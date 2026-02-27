"""
source_channels 초기 씨드 데이터.
긍정/감동 뉴스 RSS 소스 14개 (Tier A/B/C).
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.source_channel import SourceChannel
from sqlalchemy import select

# ── Tier A: 감동 실화 전문 ──────────────────────────────────────
TIER_A_SOURCES = [
    {
        "channel_id": None,
        "username": None,
        "display_name": "Good News Network",
        "tier": "A",
        "base_confidence": 0.85,
        "language": "en",
        "topics": ["heartwarming", "kindness", "inspiration"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://goodnewsnetwork.org/feed/",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "Upworthy",
        "tier": "A",
        "base_confidence": 0.80,
        "language": "en",
        "topics": ["heartwarming", "humanity", "social-good"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://upworthy.com/rss",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "Positive News",
        "tier": "A",
        "base_confidence": 0.85,
        "language": "en",
        "topics": ["heartwarming", "environment", "social-good"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://positive.news/feed/",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "Sunny Skyz",
        "tier": "A",
        "base_confidence": 0.78,
        "language": "en",
        "topics": ["heartwarming", "kindness", "animals"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://sunnyskyz.com/rss",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "InspireMore",
        "tier": "A",
        "base_confidence": 0.80,
        "language": "en",
        "topics": ["heartwarming", "inspiration", "humanity"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://inspiremore.com/feed/",
        "is_active": True,
    },
]

# ── Tier B: 구조/인도주의/건강 ──────────────────────────────────
TIER_B_SOURCES = [
    {
        "channel_id": None,
        "username": None,
        "display_name": "Reasons to be Cheerful",
        "tier": "B",
        "base_confidence": 0.78,
        "language": "en",
        "topics": ["solutions", "community", "environment"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://reasonstobecheerful.world/feed/",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "UNHCR Stories",
        "tier": "B",
        "base_confidence": 0.82,
        "language": "en",
        "topics": ["humanitarian", "refugees", "rescue"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://unhcr.org/news.rss",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "WHO News",
        "tier": "B",
        "base_confidence": 0.85,
        "language": "en",
        "topics": ["health", "medical", "humanitarian"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://who.int/rss-feeds/news-english.xml",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "GoFundMe Stories",
        "tier": "B",
        "base_confidence": 0.72,
        "language": "en",
        "topics": ["fundraising", "kindness", "community"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://medium.com/feed/@gofundme",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "DailyGood",
        "tier": "B",
        "base_confidence": 0.75,
        "language": "en",
        "topics": ["kindness", "inspiration", "wisdom"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://dailygood.org/rss",
        "is_active": True,
    },
]

# ── Tier C: 일반 긍정 + 솔루션 ─────────────────────────────────
TIER_C_SOURCES = [
    {
        "channel_id": None,
        "username": None,
        "display_name": "YES! Magazine",
        "tier": "C",
        "base_confidence": 0.75,
        "language": "en",
        "topics": ["solutions", "justice", "environment"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://yesmagazine.org/feeds/latest",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "The Optimist Daily",
        "tier": "C",
        "base_confidence": 0.72,
        "language": "en",
        "topics": ["solutions", "innovation", "health"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://optimistdaily.com/feed/",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "Future Crunch",
        "tier": "C",
        "base_confidence": 0.72,
        "language": "en",
        "topics": ["science", "innovation", "progress"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://futurecrunch.com/feed/",
        "is_active": True,
    },
    {
        "channel_id": None,
        "username": None,
        "display_name": "UN News - Peace & Security",
        "tier": "C",
        "base_confidence": 0.80,
        "language": "en",
        "topics": ["peace", "diplomacy", "humanitarian"],
        "geo_focus": [],
        "source_type": "rss",
        "feed_url": "https://news.un.org/feed/subscribe/en/news/topic/peace-and-security/feed/rss.xml",
        "is_active": True,
    },
]

ALL_SOURCES = TIER_A_SOURCES + TIER_B_SOURCES + TIER_C_SOURCES


async def seed():
    print("source_channels 씨드 시작...")
    async with AsyncSessionLocal() as db:
        seeded = 0
        for data in ALL_SOURCES:
            # 이미 존재하는지 확인 (display_name 기준)
            existing = await db.execute(
                select(SourceChannel).where(
                    SourceChannel.display_name == data["display_name"]
                )
            )
            if existing.scalar_one_or_none():
                print(f"  이미 존재: {data['display_name']}")
                continue

            channel = SourceChannel(**data)
            db.add(channel)
            seeded += 1
            print(f"  추가됨 [{data['tier']}]: {data['display_name']}")

        await db.commit()
        print(f"\n씨드 완료: {seeded}개 추가됨")


if __name__ == "__main__":
    asyncio.run(seed())
