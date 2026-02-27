"""
GET /warmth/mine              — 관심지역 온기 + 원인 TOP5
GET /warmth/country/{code}    — 국가별 최신 온기 + 히스토리
GET /warmth/peek              — 온기 레벨 변화 인앱 알림용 폴링
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import get_current_user, get_optional_user, get_db, plan_required, require_admin
from backend.app.models.user import User
from backend.app.models.warmth_index import WarmthIndex
from backend.app.models.story_cluster import StoryCluster

router = APIRouter(prefix="/warmth", tags=["warmth"])

WARMTH_LABELS = {0: "안정", 1: "주의", 2: "경계", 3: "위기"}


# ── Pydantic 스키마 ───────────────────────────────────────────────────────────

class ClusterSummary(BaseModel):
    id: str
    title: str
    title_ko: Optional[str] = None
    warmth: int
    confidence: float
    topic: str
    hscore: float = 0.0


class WarmthOut(BaseModel):
    country_code: str
    raw_score: float
    warmth_level: int
    warmth_label: str
    percentile_30d: float
    event_score: float
    accel_score: float
    spread_score: float
    updated_at: str
    top5_clusters: list[ClusterSummary]


class WarmthHistoryPoint(BaseModel):
    time: str
    raw_score: float
    warmth_level: int
    percentile_30d: float


class WarmthPeekItem(BaseModel):
    country_code: str
    warmth_level: int
    prev_level: int
    raw_score: float
    change_type: str  # "level_up"




# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

async def _latest_warmth(country_code: str, db: AsyncSession) -> Optional[WarmthIndex]:
    result = await db.execute(
        select(WarmthIndex)
        .where(WarmthIndex.country_code == country_code)
        .order_by(WarmthIndex.time.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_top5(country_code: str, db: AsyncSession, min_warmth: int = 0) -> list[ClusterSummary]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    result = await db.execute(
        select(StoryCluster)
        .where(
            StoryCluster.country_code == country_code,
            StoryCluster.last_event_at >= cutoff,
            StoryCluster.warmth >= max(min_warmth, 1),  # 최소 1 이상 유지
        )
        .order_by(StoryCluster.hscore.desc(), StoryCluster.warmth.desc())
        .limit(5)
    )
    clusters = result.scalars().all()
    return [
        ClusterSummary(
            id=str(c.id),
            title=c.title,
            title_ko=c.title_ko,
            warmth=c.warmth,
            confidence=round(c.confidence, 3),
            topic=c.topic,
            hscore=round(c.hscore, 2),
        )
        for c in clusters
    ]


async def _get_top5_batch(
    country_codes: list[str], db: AsyncSession, min_warmth: int = 0,
) -> dict[str, list[ClusterSummary]]:
    """국가별 top5 클러스터를 1회 배치 쿼리로 조회 (window function)."""
    if not country_codes:
        return {}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    effective_min = max(min_warmth, 1)

    rn_col = sa_func.row_number().over(
        partition_by=StoryCluster.country_code,
        order_by=[StoryCluster.hscore.desc(), StoryCluster.warmth.desc()],
    ).label("rn")

    subq = (
        select(
            StoryCluster.id,
            StoryCluster.country_code,
            StoryCluster.title,
            StoryCluster.title_ko,
            StoryCluster.warmth,
            StoryCluster.confidence,
            StoryCluster.topic,
            StoryCluster.hscore,
            rn_col,
        )
        .where(
            StoryCluster.country_code.in_(country_codes),
            StoryCluster.last_event_at >= cutoff,
            StoryCluster.warmth >= effective_min,
        )
        .subquery()
    )

    stmt = (
        select(subq)
        .where(subq.c.rn <= 5)
        .order_by(subq.c.country_code, subq.c.rn)
    )
    result = await db.execute(stmt)
    rows = result.all()

    top5_map: dict[str, list[ClusterSummary]] = {}
    for row in rows:
        cs = ClusterSummary(
            id=str(row.id),
            title=row.title,
            title_ko=row.title_ko,
            warmth=row.warmth,
            confidence=round(row.confidence, 3),
            topic=row.topic,
            hscore=round(row.hscore, 2),
        )
        top5_map.setdefault(row.country_code, []).append(cs)
    return top5_map


def _warmth_to_out(t: WarmthIndex, top5: list[ClusterSummary]) -> WarmthOut:
    return WarmthOut(
        country_code=t.country_code,
        raw_score=round(t.raw_score, 1),
        warmth_level=t.warmth_level,
        warmth_label=WARMTH_LABELS.get(t.warmth_level, "알 수 없음"),
        percentile_30d=round(t.percentile_30d or 0.0, 1),
        event_score=round(t.event_score or 0.0, 1),
        accel_score=round(t.accel_score or 0.0, 1),
        spread_score=round(t.spread_score or 0.0, 1),
        updated_at=t.time.isoformat(),
        top5_clusters=top5,
    )


# ── 기본 모니터링 국가 ─────────────────────────────────────────────────────────

DEFAULT_COUNTRIES = [
    # 주요국
    "US", "GB", "FR", "DE", "JP", "AU",
    # 유럽·코카서스
    "UA", "RU", "BY", "MD", "RS", "GE", "AM", "AZ",
    # 중동
    "PS", "IL", "IR", "IQ", "SY", "LB", "YE", "SA", "TR", "EG",
    # 동아시아
    "KP", "TW", "CN", "KR",
    # 동남아
    "MM", "PH", "VN", "ID", "TH",
    # 남아시아·중앙아시아
    "PK", "AF", "IN", "BD", "KZ", "TJ", "KG",
    # 아프리카
    "SD", "SS", "ET", "SO", "LY", "ML", "BF", "NE", "NG", "CM",
    "CF", "CD", "MZ", "TD", "GN", "ER", "DZ", "TN", "MA",
    # 아메리카
    "VE", "HT", "CO", "EC", "MX", "NI", "CU", "GT", "HN",
]


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.get("/peek", response_model=list[WarmthPeekItem])
async def peek_warmth(
    since: Optional[str] = Query(None, description="ISO timestamp — 이 시각 이후 알림만 반환"),
):
    """
    온기 레벨 변화 인앱 알림용 폴링.
    Redis에서 warmth:alert:* 키를 스캔하여 since 이후 레벨 상승 건만 반환.
    최대 3건, 레벨 상승폭 큰 순 정렬.
    """
    import re as _re
    from backend.app.core.redis import get_redis

    since_dt: Optional[datetime] = None
    if since:
        try:
            s = _re.sub(r'\.\d+', '', since.replace("Z", "+00:00"))
            since_dt = datetime.fromisoformat(s)
        except ValueError:
            since_dt = datetime.now(timezone.utc) - timedelta(minutes=5)

    redis = get_redis()
    items: list[WarmthPeekItem] = []

    cursor = "0"
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match="warmth:alert:*", count=100)
        for key in keys:
            val = await redis.get(key)
            if not val:
                continue
            # 형식: "{prev_level}:{new_level}:{raw_score}:{iso_timestamp}"
            parts = val.split(":", 3)
            if len(parts) < 4:
                continue
            prev_level = int(parts[0])
            new_level = int(parts[1])
            raw_score = float(parts[2])
            alert_time_str = parts[3]

            # since 필터
            if since_dt:
                try:
                    alert_time = datetime.fromisoformat(alert_time_str)
                    if alert_time <= since_dt:
                        continue
                except ValueError:
                    continue

            country_code = key.split(":")[-1]
            items.append(WarmthPeekItem(
                country_code=country_code,
                warmth_level=new_level,
                prev_level=prev_level,
                raw_score=round(raw_score, 1),
                change_type="level_up",
            ))

        if cursor == "0" or cursor == 0:
            break

    # 레벨 상승폭 큰 순 정렬, 최대 3건
    items.sort(key=lambda x: x.warmth_level - x.prev_level, reverse=True)
    return items[:3]


@router.get("/mine", response_model=list[WarmthOut])
async def warmth_mine(
    countries: Optional[str] = Query(None, description="쉼표 구분 국가 코드 (예: UA,PS,IL)"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    관심지역 온기. countries 파라미터로 필터, 없으면 기본 8개국.
    각 국가별 최신 값 + 원인 TOP5.
    로그인 사용자의 min_warmth 설정을 TOP5 클러스터 필터에 적용.
    """
    from backend.app.models.user import UserPreference
    codes = [c.strip().upper() for c in countries.split(",") if c.strip()] if countries else DEFAULT_COUNTRIES

    # 로그인 사용자의 min_warmth 조회
    user_min_warmth = 0
    if current_user:
        pref_result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == current_user.id)
        )
        pref = pref_result.scalar_one_or_none()
        if pref:
            user_min_warmth = pref.min_warmth

    # ── DB에서 국가별 최신 1건만 조회 (DISTINCT ON) ──
    raw_result = await db.execute(
        select(WarmthIndex)
        .where(WarmthIndex.country_code.in_(codes))
        .distinct(WarmthIndex.country_code)
        .order_by(WarmthIndex.country_code, WarmthIndex.time.desc())
    )
    warmth_map: dict[str, WarmthIndex] = {
        row.country_code: row for row in raw_result.scalars().all()
    }

    # ── 데이터 없으면 요청 국가만 온더플라이 계산 (경량 fallback) ──
    missing_codes = [c for c in codes if c not in warmth_map]
    if missing_codes:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("warmth fallback: %d개국 온더플라이 계산 시작", len(missing_codes))
        from backend.app.core.database import AsyncSessionLocal
        try:
            async with AsyncSessionLocal() as calc_db:
                async with calc_db.begin():
                    from worker.processor.warmth_calculator import calculate_country_warmth
                    for mc in missing_codes:
                        result = await calculate_country_warmth(mc, calc_db)
                        if result:
                            _logger.info("warmth fallback 완료: %s", mc)
            # fallback 계산 후 다시 조회
            raw_result2 = await db.execute(
                select(WarmthIndex)
                .where(WarmthIndex.country_code.in_(missing_codes))
                .distinct(WarmthIndex.country_code)
                .order_by(WarmthIndex.country_code, WarmthIndex.time.desc())
            )
            for row in raw_result2.scalars().all():
                warmth_map[row.country_code] = row
        except Exception as e:
            _logger.warning("warmth fallback 실패: %s", e)

    # ── 국가별 top5 클러스터 일괄 조회 (1회 배치 쿼리) ──
    active_codes = [c for c in codes if c in warmth_map]
    top5_map = await _get_top5_batch(active_codes, db, min_warmth=user_min_warmth)

    results = []
    for code in codes:
        t = warmth_map.get(code)
        if t is None:
            continue
        results.append(_warmth_to_out(t, top5_map.get(code, [])))

    return results


@router.get("/country/{country_code}", response_model=WarmthOut)
async def warmth_country(
    country_code: str,
    db: AsyncSession = Depends(get_db),
):
    """국가별 최신 온기 + 원인 TOP5."""
    code = country_code.upper()
    t = await _latest_warmth(code, db)

    if t is None:
        raise HTTPException(status_code=404, detail=f"온기 데이터 없음: {code}")

    top5 = await _get_top5(code, db)
    return _warmth_to_out(t, top5)


_HISTORY_PLAN_DAYS = {"7d": ("free", 7), "30d": ("pro", 30), "90d": ("pro_plus", 90)}


@router.get("/country/{country_code}/history", response_model=list[WarmthHistoryPoint])
async def warmth_history(
    country_code: str,
    range: str = Query("7d", description="7d / 30d / 90d"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """국가별 온기 히스토리 (비로그인/Free: 7일, Pro: 30일, Pro+: 90일)."""
    code = country_code.upper()

    # 플랜 게이팅 (30d는 Pro, 90d는 Pro+ 필요)
    min_plan, days = _HISTORY_PLAN_DAYS.get(range, ("free", 7))
    from backend.app.core.auth import _PLAN_ORDER
    user_level = _PLAN_ORDER.get(current_user.plan.lower(), 0) if current_user else 0
    required_level = _PLAN_ORDER.get(min_plan, 0)
    if user_level < required_level:
        raise HTTPException(
            status_code=403,
            detail={"code": "PLAN_REQUIRED", "required": min_plan, "upgrade_url": "/upgrade"},
        )
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(WarmthIndex)
        .where(
            WarmthIndex.country_code == code,
            WarmthIndex.time >= cutoff,
        )
        .order_by(WarmthIndex.time.asc())
    )
    rows = result.scalars().all()

    return [
        WarmthHistoryPoint(
            time=r.time.isoformat(),
            raw_score=round(r.raw_score, 1),
            warmth_level=r.warmth_level,
            percentile_30d=round(r.percentile_30d or 0.0, 1),
        )
        for r in rows
    ]


@router.post("/recalculate")
async def warmth_recalculate(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """온기 즉시 재계산 (admin 전용)."""
    import logging
    _logger = logging.getLogger(__name__)

    from backend.app.core.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as calc_db:
            async with calc_db.begin():
                from worker.processor.warmth_calculator import calculate_all_warmth
                results = await calculate_all_warmth(calc_db)
                _logger.info("warmth_recalculate 완료: %d개국", len(results))
                return {"status": "ok", "countries": len(results)}
    except Exception as e:
        _logger.error("warmth_recalculate 실패: %s", e, exc_info=True)
        raise HTTPException(500, detail="온기 재계산 중 오류가 발생했습니다.")
