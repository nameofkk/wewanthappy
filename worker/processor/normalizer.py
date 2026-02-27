"""
EventNormalizer: RawEvent 텍스트 → NormalizedEvent 변환 (WeWantHappy).

처리 순서:
1. 언어 감지 (langdetect)
2. Topic 분류 (휴먼터치 10개 토픽 키워드 매칭)
3. Warmth 계산 (0~100) — 온기 지수
4. Confidence 계산 (source tier 기반)
5. dedup_key 생성 (정규화 텍스트 MD5)
6. Geo 정보 추출 (국가 키워드 → 좌표 → geohash5)
"""
import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── Topic 분류 키워드 (휴먼터치 10개 토픽) ──────────────────────────────────

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "kindness": [
        "random act of kindness", "stranger helped", "good samaritan", "donated",
        "selfless", "generous", "generosity", "charity", "gift", "giving",
        "compassion", "kindness", "kind act", "helping hand", "paying it forward",
        "free meal", "surprise", "anonymous donor", "philanthropy", "benevolence",
        "warm heart", "touched by", "heartwarming", "uplifting",
    ],
    "reunion": [
        "reunited", "found after", "long-lost", "homecoming", "forgiveness",
        "reconciliation", "reunion", "reconnect", "came back", "returned home",
        "family reunion", "long-awaited", "embrace", "tears of joy",
        "finally met", "after years", "reconnected", "back together",
    ],
    "rescue": [
        "rescued", "saved life", "survived", "miracle", "hero", "bravery",
        "brave", "courage", "courageous", "first responder", "pulled from",
        "saved from", "search and rescue", "life-saving", "emergency rescue",
        "firefighter", "lifeguard", "paramedic", "evacuation", "survivor",
    ],
    "community": [
        "volunteer", "solidarity", "neighborhood", "together", "mutual aid",
        "grassroots", "community", "coming together", "united", "collective",
        "neighbors", "neighbourhood", "teamwork", "cooperation", "support group",
        "fundraiser", "crowdfunding", "raised money", "food bank", "shelter",
    ],
    "recovery": [
        "rebuilt", "recovered", "overcame", "resilience", "back on feet",
        "second chance", "recovery", "overcome", "perseverance", "determination",
        "fresh start", "new beginning", "bounced back", "rebuild", "restoration",
        "turned life around", "redemption", "transformation", "triumph",
    ],
    "children": [
        "student", "child", "school", "dream came true", "scholarship",
        "future", "young", "youth", "kid", "children", "classroom",
        "graduation", "first day", "education", "learning", "teacher",
        "mentor", "inspire", "inspired", "aspiring",
    ],
    "health": [
        "cured", "cancer-free", "walked again", "medical miracle", "breakthrough",
        "remission", "recovered from", "beat cancer", "prosthetic", "transplant",
        "clinical trial", "new treatment", "innovative therapy", "healed",
        "disability", "accessible", "inclusive", "mental health", "wellness",
    ],
    "animals": [
        "adopted", "rescued animal", "therapy dog", "wildlife saved", "shelter",
        "animal rescue", "foster", "stray", "pet adoption", "wildlife",
        "endangered species", "conservation", "rehabilitation", "sanctuary",
        "puppy", "kitten", "beloved pet", "loyal", "companion",
    ],
    "elderly": [
        "grandparent", "100 years old", "lifelong", "wisdom", "generations",
        "elderly", "senior", "aging", "grandmother", "grandfather",
        "centenarian", "golden years", "retirement", "legacy", "memory",
        "intergenerational", "nursing home", "care home", "elder",
    ],
    "peace": [
        "ceasefire", "peace", "coexistence", "bridge-building",
        "cross-border friendship", "harmony", "unity", "tolerance",
        "understanding", "dialogue", "peacemaker", "peacekeeping",
        "diplomacy", "treaty", "accord", "reconciliation", "human rights",
    ],
}

# ── Warmth 기본값 (온기 점수) ──────────────────────────────────────────────

TOPIC_BASE_WARMTH: dict[str, int] = {
    "kindness":   85,
    "reunion":    90,
    "rescue":     85,
    "community":  80,
    "recovery":   80,
    "children":   85,
    "health":     80,
    "animals":    75,
    "elderly":    85,
    "peace":      85,
    "unknown":    50,
}

# ── Warmth 보정 키워드 (감동 보정) ─────────────────────────────────────────

WARMTH_UP: list[tuple[str, int]] = [
    ("tears", 10), ("miracle", 10), ("reunited", 8), ("hero", 8),
    ("selfless", 8), ("survived", 7), ("dream", 6), ("love", 5),
    ("hug", 5), ("smile", 5), ("faith in humanity", 10),
    ("restored", 6), ("overcame", 6), ("inspiring", 5),
    ("heartwarming", 8), ("touching", 7), ("emotional", 5),
    ("grateful", 5), ("thankful", 5), ("beautiful", 4),
    ("incredible", 5), ("amazing", 4), ("wonderful", 4),
    ("extraordinary", 6), ("remarkable", 5), ("uplifting", 6),
]

WARMTH_DOWN: list[tuple[str, int]] = [
    ("failed", -10), ("arrested", -8), ("accused", -7),
    ("controversial", -5), ("scandal", -5), ("rejected", -5),
    ("tragedy", -8), ("disaster", -6), ("crisis", -5),
    ("death", -6), ("killed", -8), ("violence", -10),
    ("war", -10), ("attack", -8), ("conflict", -7),
]

# ── 부정 콘텐츠 필터 (수집 제외용) ──────────────────────────────────────────

_COLD_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"\b(killed|dead|deaths?|massacre|genocide|murder|shooting|stabbing)\b",
    r"\b(war|warfare|invasion|bombing|airstrike|missile|shelling|artillery)\b",
    r"\b(terror|terrorist|extremist|jihadist|suicide bomb)\b",
    r"\b(rape|sexual assault|abuse|trafficking)\b",
    r"\b(coup|junta|martial law)\b",
    r"\b(catastroph|devastat|horr?ific)\b",
]]


def _is_cold_content(text: str) -> bool:
    """부정적/폭력적 콘텐츠인지 감지 → 수집 제외."""
    cold_count = sum(1 for p in _COLD_PATTERNS if p.search(text))
    return cold_count >= 2  # 2개 이상 부정 패턴이면 cold


# ── 사람 이름/인용문 보너스 ─────────────────────────────────────────────────

def _human_touch_bonus(text: str) -> int:
    """사람에 대한 이야기일수록 보너스. 최대 +25."""
    import math
    bonus = 0

    # 사람 이름 등장 (대문자 시작 이름 패턴)
    name_pattern = re.compile(r'\b[A-Z][a-z]{2,}\s[A-Z][a-z]{2,}\b')
    names = name_pattern.findall(text)
    if names:
        bonus += min(15, len(names) * 5)

    # 직접 인용문 (따옴표 안의 발언)
    quotes = re.findall(r'"[^"]{10,}"', text)
    if quotes:
        bonus += min(5, len(quotes) * 3)

    # 수혜자 수 규모
    beneficiary_patterns = [
        re.compile(r'(\d[\d,]*)\s*(?:people|children|students|families|animals)', re.I),
        re.compile(r'(?:helped|saved|rescued|fed|housed)\s+(\d[\d,]*)', re.I),
    ]
    for pat in beneficiary_patterns:
        for m in pat.finditer(text):
            try:
                n = int(m.group(1).replace(",", ""))
                bonus += min(10, int(math.log10(max(1, n)) * 3))
            except ValueError:
                continue

    return min(25, bonus)


# ── 국가 키워드 → 코드 + 중심 좌표 ─────────────────────────────────────────

COUNTRY_MAP: dict[str, tuple[str, float, float]] = {
    "ukraine": ("UA", 49.0, 31.0),
    "ukrainian": ("UA", 49.0, 31.0),
    "kyiv": ("UA", 50.45, 30.52),
    "russia": ("RU", 61.0, 105.0),
    "russian": ("RU", 61.0, 105.0),
    "moscow": ("RU", 55.75, 37.62),
    "israel": ("IL", 31.5, 34.8),
    "israeli": ("IL", 31.5, 34.8),
    "gaza": ("PS", 31.5, 34.47),
    "palestine": ("PS", 31.9, 35.3),
    "iran": ("IR", 32.0, 53.0),
    "china": ("CN", 35.0, 105.0),
    "chinese": ("CN", 35.0, 105.0),
    "beijing": ("CN", 39.91, 116.39),
    "taiwan": ("TW", 23.7, 121.0),
    "north korea": ("KP", 40.3, 127.5),
    "south korea": ("KR", 36.5, 127.8),
    "korea": ("KR", 36.5, 127.8),
    "korean": ("KR", 36.5, 127.8),
    "seoul": ("KR", 37.57, 126.98),
    "syria": ("SY", 35.0, 38.0),
    "myanmar": ("MM", 17.0, 96.0),
    "sudan": ("SD", 15.0, 32.0),
    "ethiopia": ("ET", 9.0, 38.5),
    "somalia": ("SO", 5.5, 45.5),
    "lebanon": ("LB", 33.9, 35.5),
    "iraq": ("IQ", 33.0, 44.0),
    "afghanistan": ("AF", 33.0, 65.0),
    "pakistan": ("PK", 30.0, 70.0),
    "india": ("IN", 20.0, 77.0),
    "united states": ("US", 38.0, -97.0),
    "america": ("US", 38.0, -97.0),
    "american": ("US", 38.0, -97.0),
    "washington": ("US", 38.9, -77.0),
    "new york": ("US", 40.71, -74.01),
    "los angeles": ("US", 34.05, -118.24),
    "uk": ("GB", 54.0, -2.0),
    "britain": ("GB", 54.0, -2.0),
    "british": ("GB", 54.0, -2.0),
    "london": ("GB", 51.51, -0.13),
    "france": ("FR", 46.0, 2.0),
    "french": ("FR", 46.0, 2.0),
    "paris": ("FR", 48.85, 2.35),
    "germany": ("DE", 51.0, 9.0),
    "german": ("DE", 51.0, 9.0),
    "berlin": ("DE", 52.52, 13.4),
    "mexico": ("MX", 23.0, -102.0),
    "australia": ("AU", -27.0, 133.0),
    "australian": ("AU", -27.0, 133.0),
    "japan": ("JP", 35.0, 138.0),
    "japanese": ("JP", 35.0, 138.0),
    "tokyo": ("JP", 35.68, 139.69),
    "brazil": ("BR", -14.0, -51.0),
    "brazilian": ("BR", -14.0, -51.0),
    "saudi arabia": ("SA", 24.0, 45.0),
    "turkey": ("TR", 39.0, 35.0),
    "turkish": ("TR", 39.0, 35.0),
    "egypt": ("EG", 26.0, 30.0),
    "nigeria": ("NG", 9.0, 8.0),
    "italy": ("IT", 42.83, 12.83),
    "italian": ("IT", 42.83, 12.83),
    "rome": ("IT", 41.90, 12.49),
    "spain": ("ES", 40.0, -4.0),
    "spanish": ("ES", 40.0, -4.0),
    "madrid": ("ES", 40.42, -3.70),
    "netherlands": ("NL", 52.37, 5.23),
    "canada": ("CA", 56.13, -106.35),
    "canadian": ("CA", 56.13, -106.35),
    "south africa": ("ZA", -30.56, 22.94),
    "kenya": ("KE", -0.02, 37.91),
    "thailand": ("TH", 15.87, 100.99),
    "vietnam": ("VN", 14.06, 108.28),
    "philippines": ("PH", 12.88, 121.77),
    "indonesia": ("ID", -0.79, 113.92),
    "singapore": ("SG", 1.35, 103.82),
    "malaysia": ("MY", 4.21, 101.97),
    "colombia": ("CO", 4.57, -74.3),
    "argentina": ("AR", -38.42, -63.62),
    "chile": ("CL", -35.68, -71.54),
    "peru": ("PE", -9.19, -75.02),
    "new zealand": ("NZ", -40.9, 174.89),
    "sweden": ("SE", 60.13, 18.64),
    "norway": ("NO", 64.5, 17.9),
    "denmark": ("DK", 56.26, 9.5),
    "switzerland": ("CH", 46.82, 8.23),
    "austria": ("AT", 47.52, 14.55),
    "poland": ("PL", 51.92, 19.15),
    "greece": ("GR", 39.07, 21.82),
    "portugal": ("PT", 39.55, -7.86),
    "belgium": ("BE", 50.85, 4.35),
    "nato": ("BE", 50.88, 4.47),
    "ghana": ("GH", 7.95, -1.02),
    "morocco": ("MA", 31.79, -7.09),
    "bangladesh": ("BD", 23.68, 90.36),
    "sri lanka": ("LK", 7.87, 80.77),
    "nepal": ("NP", 28.39, 84.12),
    "uganda": ("UG", 1.37, 32.29),
    "haiti": ("HT", 19.0, -72.0),
    "venezuela": ("VE", 8.0, -66.0),
    "cuba": ("CU", 21.52, -77.78),
    "finland": ("FI", 64.0, 26.0),
    "romania": ("RO", 45.94, 24.97),
    "hungary": ("HU", 47.16, 19.5),
    "serbia": ("RS", 44.02, 21.09),
    "croatia": ("HR", 45.1, 15.2),
}


# ── 데이터 클래스 ────────────────────────────────────────────────────────────

@dataclass
class NormalizeResult:
    title: str
    title_ko: Optional[str]
    body: str
    topic: str
    entity_anchor: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    geohash5: Optional[str]
    country_code: Optional[str]
    severity: int  # warmth score (0~100)
    source_tier: str
    confidence: float
    dedup_key: str
    lang: str
    translation_status: str  # ok | failed | skipped
    geo_method: str  # keyword | none
    event_time: datetime


# ── 내부 함수들 ──────────────────────────────────────────────────────────────

def _detect_language(text: str) -> str:
    try:
        from langdetect import detect
        return detect(text[:500])
    except Exception:
        return "unknown"


def _translate_to_english(text: str, lang: str) -> str:
    if lang in ("en", "unknown"):
        return text
    try:
        from deep_translator import GoogleTranslator
        chunk = text[:480]
        translated = GoogleTranslator(source="auto", target="en").translate(chunk)
        return translated or text
    except Exception as e:
        logger.warning("번역 실패 (%s→en, %d자): %s", lang, len(text), e)
        return text


def _translate_to_korean(text: str) -> Optional[str]:
    try:
        from deep_translator import GoogleTranslator
        chunk = text[:480]
        result = GoogleTranslator(source="en", target="ko").translate(chunk)
        return result or None
    except Exception as e:
        logger.warning("한국어 번역 실패 (%d자): %s", len(text), e)
        return None


# 강력한 신호 키워드 (1개만 있어도 topic 분류 확정)
_STRONG_KEYWORDS: dict[str, set[str]] = {
    "kindness":  {"random act of kindness", "good samaritan", "paying it forward",
                  "heartwarming", "faith in humanity"},
    "reunion":   {"reunited", "long-lost", "homecoming", "tears of joy"},
    "rescue":    {"rescued", "saved life", "hero", "miracle", "first responder"},
    "community": {"volunteer", "solidarity", "mutual aid", "crowdfunding"},
    "recovery":  {"overcame", "resilience", "second chance", "triumph"},
    "children":  {"dream came true", "scholarship", "graduation"},
    "health":    {"cancer-free", "medical miracle", "walked again", "breakthrough"},
    "animals":   {"animal rescue", "therapy dog", "wildlife saved"},
    "elderly":   {"centenarian", "100 years old", "intergenerational"},
    "peace":     {"ceasefire", "peace", "coexistence", "peacemaker"},
}


def _classify_topic(text: str) -> str:
    """키워드 매칭으로 topic 분류 (휴먼터치 10개 토픽)."""
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        strong = _STRONG_KEYWORDS.get(topic, set())
        strong_hits = sum(1 for kw in strong if kw in text_lower)
        if strong_hits:
            scores[topic] = scores.get(topic, 0) + strong_hits * 3

        weak_hits = sum(1 for kw in keywords if kw not in strong and kw in text_lower)
        if weak_hits >= 1:
            scores[topic] = scores.get(topic, 0) + weak_hits

    return max(scores, key=lambda t: scores[t]) if scores else "unknown"


def _calculate_warmth(text: str, topic: str) -> int:
    """
    온기 지수 산정 (0~100).
    = base(토픽) + keyword_modifier(WARMTH_UP/DOWN) + human_touch_bonus
    """
    base = TOPIC_BASE_WARMTH.get(topic, 50)
    text_lower = text.lower()

    keyword_delta = sum(delta for kw, delta in WARMTH_UP if kw in text_lower)
    keyword_delta += sum(delta for kw, delta in WARMTH_DOWN if kw in text_lower)
    keyword_delta = max(-30, min(30, keyword_delta))

    modifier = keyword_delta + _human_touch_bonus(text_lower)

    return max(0, min(100, base + modifier))


def _extract_geo(
    text: str,
    title: Optional[str] = None,
) -> tuple[Optional[str], Optional[float], Optional[float]]:
    """국가 코드, 위도, 경도 반환. 빈도 기반 + 제목 3배 가중치."""
    from collections import defaultdict
    country_hits: dict[str, list[tuple[int, float, float]]] = defaultdict(list)

    sorted_kws = sorted(COUNTRY_MAP.keys(), key=len, reverse=True)

    if title:
        title_lower = title.lower()
        for kw in sorted_kws:
            if kw in title_lower:
                code, lat, lon = COUNTRY_MAP[kw]
                count = title_lower.count(kw)
                weight = count * len(kw) * 3
                country_hits[code].append((weight, lat, lon))

    text_lower = text.lower()
    for kw in sorted_kws:
        if kw in text_lower:
            code, lat, lon = COUNTRY_MAP[kw]
            count = text_lower.count(kw)
            weight = count * len(kw)
            country_hits[code].append((weight, lat, lon))

    if not country_hits:
        return None, None, None

    best_code = max(country_hits, key=lambda c: sum(w for w, _, _ in country_hits[c]))
    best_entry = max(country_hits[best_code], key=lambda x: x[0])
    return best_code, best_entry[1], best_entry[2]


def _make_geohash(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    if lat is None or lon is None:
        return None
    try:
        import geohash2
        return geohash2.encode(lat, lon, precision=5)
    except Exception:
        return None


def _make_dedup_key(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    words = cleaned.split()[:60]
    return hashlib.md5(" ".join(words).encode("utf-8")).hexdigest()


def _make_title(text: str, max_len: int = 120) -> str:
    sentences = re.split(r"[.!?\n]", text.strip())
    title = (sentences[0].strip() if sentences else text.strip())
    return title[:max_len - 3] + "..." if len(title) > max_len else title


def _calculate_confidence(tier: str, warmth: int) -> float:
    base = {"A": 0.85, "B": 0.70, "C": 0.55, "D": 0.35}.get(tier, 0.50)
    return round(min(0.95, base), 2)


# ── 공개 API ─────────────────────────────────────────────────────────────────

def is_relevant(result: "NormalizeResult") -> bool:
    """
    정규화 결과가 서비스에 표시할 가치가 있는지 판단.
    - topic이 unknown이 아님 → 항상 통과
    - topic이 unknown이면 warmth > 40이어야 통과
    """
    if result.topic != "unknown":
        return True
    return result.severity > 40


def normalize(
    raw_text: str,
    source_tier: str,
    collected_at: datetime,
    source_title: Optional[str] = None,
    published_at: Optional[datetime] = None,
) -> NormalizeResult:
    """RawEvent 텍스트 → NormalizeResult (동기)."""
    lang = _detect_language(raw_text)

    if lang in ("en", "unknown"):
        translation_status = "skipped"
    else:
        translation_status = "ok"
    text_for_analysis = _translate_to_english(raw_text, lang)
    if lang not in ("en", "unknown") and text_for_analysis == raw_text:
        translation_status = "failed"

    # 부정 콘텐츠 필터
    if _is_cold_content(text_for_analysis):
        # cold content → 낮은 warmth로 설정 (나중에 is_relevant에서 걸러짐)
        return NormalizeResult(
            title=_make_title(text_for_analysis),
            title_ko=None,
            body=text_for_analysis[:2000],
            topic="unknown",
            entity_anchor=None,
            lat=None, lon=None, geohash5=None, country_code=None,
            severity=0,
            source_tier=source_tier,
            confidence=0.0,
            dedup_key=_make_dedup_key(raw_text),
            lang=lang,
            translation_status=translation_status,
            geo_method="none",
            event_time=published_at if published_at is not None else collected_at,
        )

    topic = _classify_topic(text_for_analysis)
    warmth = _calculate_warmth(text_for_analysis, topic)

    _raw_title_for_geo = source_title.strip()[:200] if source_title and len(source_title.strip()) > 5 else None
    country_code, lat, lon = _extract_geo(text_for_analysis, title=_raw_title_for_geo)
    geohash5 = _make_geohash(lat, lon)
    confidence = _calculate_confidence(source_tier, warmth)
    dedup_key = _make_dedup_key(raw_text)

    if source_title and len(source_title.strip()) > 5:
        raw_title = source_title.strip()[:200]
        title_lang = _detect_language(raw_title)
        title_en = _translate_to_english(raw_title, title_lang) if title_lang not in ("en", "unknown") else raw_title
        title = title_en[:120]
    else:
        title = _make_title(text_for_analysis)

    title_ko = _translate_to_korean(title)

    entity_anchor: Optional[str] = country_code
    if not entity_anchor:
        m = re.search(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b", text_for_analysis)
        if m:
            entity_anchor = m.group(1)[:64]

    geo_method = "keyword" if country_code else "none"

    return NormalizeResult(
        title=title,
        title_ko=title_ko,
        body=text_for_analysis[:2000],
        topic=topic,
        entity_anchor=entity_anchor,
        lat=lat,
        lon=lon,
        geohash5=geohash5,
        country_code=country_code,
        severity=warmth,
        source_tier=source_tier,
        confidence=confidence,
        dedup_key=dedup_key,
        lang=lang,
        translation_status=translation_status,
        geo_method=geo_method,
        event_time=published_at if published_at is not None else collected_at,
    )
