"""
TrendingEngine: HScore 기반 트렌딩 키워드 계산.

HScore (v4, 0-10 스케일):
  raw = 0.25*velocity_norm + 0.15*quality + 0.40*warmth_norm + 0.20*spread
  HScore = raw × KSCORE_SCALE(10)

  모든 컴포넌트 0~1 정규화 → 가중치가 실제 영향도를 정확히 반영.
  UI 임계값: 정상(<3) / 주의(3-5) / 경계(5-7) / 위기(7+)

포함 조건: HScore >= calibration.KSCORE_MIN
결과를 trending_keywords 테이블에 UPSERT.
모든 튜닝 가능한 상수는 calibration.py에서 관리.
"""
import logging
import math
import uuid as uuid_lib
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.story_cluster import StoryCluster
from backend.app.models.trending_keyword import TrendingKeyword
from worker.processor.calibration import (
    VELOCITY_CAP,
    VELOCITY_EXPONENT,
    SPIKE_FACTOR,
    SPREAD_SATURATION,
    KSCORE_MIN,
    KSCORE_SCALE,
    TRENDING_LIMIT,
    KSCORE_VALID_MINUTES,
)

logger = logging.getLogger(__name__)

# 모듈 수준 alias (하위 호환 및 가독성)
VALID_MINUTES = KSCORE_VALID_MINUTES


def _calc_hscore(
    event_count: int,
    is_touching: bool,
    confidence: float,
    warmth: int,
    independent_sources: int,
    source_tiers: list[str],
) -> float:
    """
    HScore 계산 (v4) — 0~10 스케일.

    모든 컴포넌트를 0~1 정규화 후 가중합산, × KSCORE_SCALE(10).
    HScore = (0.25*velocity_norm + 0.15*quality + 0.40*warmth_norm + 0.20*spread) × 10

    velocity_norm (0~1):
    - min(1.0, k10^VELOCITY_EXPONENT × spike_factor / VELOCITY_CAP)
    - k10=5: 0.52, k10=10: 0.84, k10=15: 1.0(cap)

    UI 임계값: 정상(<3) / 주의(3~5) / 경계(5~7) / 위기(7+)

    상수 변경 시: calibration.py 수정 후 이 함수는 자동 반영됨.
    """
    k10 = max(1, event_count)

    sf = SPIKE_FACTOR if is_touching else 1.0
    # v4: velocity를 0~1 정규화 (기존: 1.0~6.0 비정규화 → 63% 지배 버그)
    velocity_raw = min(VELOCITY_CAP, (k10 ** VELOCITY_EXPONENT) * sf)
    velocity_norm = velocity_raw / VELOCITY_CAP

    # quality: confidence + tier 보너스
    tier_bonus = sum(
        0.05 if t == "A" else 0.03 if t == "B" else 0.01
        for t in source_tiers
    )
    quality = min(1.0, confidence + tier_bonus)

    warmth_norm = warmth / 100.0

    # spread: 독립출처 수 기반 (최대 1.0, calibration.SPREAD_SATURATION 기준)
    spread = min(1.0, independent_sources / float(SPREAD_SATURATION))

    raw = (
        0.25 * velocity_norm
        + 0.15 * quality
        + 0.40 * warmth_norm
        + 0.20 * spread
    )
    return round(raw * KSCORE_SCALE, 2)


async def calculate_global_trending(db: AsyncSession) -> list[dict]:
    """
    최근 60분 StoryCluster에서 HScore 상위 20개 계산.
    trending_keywords 테이블에 저장 후 결과 반환.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=48)  # 48시간 윈도우 (HScore 계산 범위)

    # 최근 48시간 활성 클러스터 조회
    result = await db.execute(
        select(StoryCluster)
        .where(StoryCluster.last_event_at >= cutoff)
        .order_by(StoryCluster.event_count.desc())
        .limit(200)
    )
    clusters = result.scalars().all()

    if not clusters:
        return []

    # HScore 계산
    scored = []
    for c in clusters:
        kscore = _calc_hscore(
            event_count=c.event_count,
            is_touching=c.is_touching,
            confidence=c.confidence,
            warmth=c.warmth,
            independent_sources=c.independent_sources,
            source_tiers=c.source_tiers or [],
        )
        # 포함 조건 완화: event_count >= 1 이상이면 포함
        if kscore < KSCORE_MIN:
            continue

        scored.append({
            "cluster_id": str(c.id),
            "keyword": c.title,
            "keyword_ko": c.title_ko,
            "hscore": kscore,
            "topic": c.topic,
            "country_codes": [c.country_code] if c.country_code else [],
            "is_touching": c.is_touching,
            "warmth": c.warmth,
            "event_count": c.event_count,
            "k10": c.event_count,
            "reason": _make_reason(c, kscore),
        })

    scored.sort(key=lambda x: x["hscore"], reverse=True)
    top = scored[:TRENDING_LIMIT]

    # trending_keywords 테이블: 상위 TRENDING_LIMIT(30)개만 저장하여 DB bloat 방지
    # story_clusters.hscore는 전체 scored에서 갱신 (아래 별도 처리)
    valid_until = now + timedelta(minutes=VALID_MINUTES)

    for item in top:
        kw = TrendingKeyword(
            keyword=item["keyword"],
            keyword_ko=item.get("keyword_ko"),
            normalized_kw=item["keyword"].lower(),
            hscore=item["hscore"],
            topic=item["topic"],
            country_codes=item["country_codes"],
            cluster_ids=[uuid_lib.UUID(item["cluster_id"])],
            event_count=item.get("event_count", 0),
            warmth=item.get("warmth", 0),
            is_touching=item.get("is_touching", False),
            scope="global",
            calculated_at=now,
            valid_until=valid_until,
        )
        db.add(kw)

    # 히스토리 보관: 90일 이전 레코드만 삭제
    # valid_until은 현재 트렌딩 표시용 (24h), calculated_at 기준으로 90일 보관.
    # Pro+ 사용자가 90일 HScore 히스토리를 조회할 수 있어야 함.
    history_cutoff = now - timedelta(days=91)
    await db.flush()
    await db.execute(
        delete(TrendingKeyword).where(
            TrendingKeyword.calculated_at < history_cutoff,
        )
    )

    # story_clusters.hscore 업데이트:
    # 1) scored 클러스터: 계산된 kscore 반영
    # 2) 평가했지만 KSCORE_MIN 미달 클러스터: hscore=0 리셋
    #    (이전에 높았다가 떨어진 클러스터가 stale 값을 유지하는 버그 방지)
    from sqlalchemy import update as sql_update
    scored_ids = {uuid_lib.UUID(item["cluster_id"]) for item in scored}
    for item in scored:
        await db.execute(
            sql_update(StoryCluster)
            .where(StoryCluster.id == uuid_lib.UUID(item["cluster_id"]))
            .values(hscore=item["hscore"])
        )
    for c in clusters:
        if c.id not in scored_ids:
            await db.execute(
                sql_update(StoryCluster)
                .where(StoryCluster.id == c.id)
                .values(hscore=0.0)
            )

    logger.info("트렌딩 계산 완료: 클러스터 %d개 → scored %d개 (top %d개)", len(clusters), len(scored), len(top))
    return top


def _make_reason(cluster: StoryCluster, kscore: float) -> str:
    """'왜 뜸?' 설명 문자열 생성."""
    if cluster.is_touching:
        return f"1분간 이벤트 급증 (HScore {kscore:.1f})"
    if cluster.independent_sources >= 3:
        return f"{cluster.independent_sources}개 독립출처 동시 보도 (HScore {kscore:.1f})"
    return f"60분간 {cluster.event_count}개 이벤트 (HScore {kscore:.1f})"
