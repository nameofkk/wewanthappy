"""seed rss channels — 긍정 뉴스 피드

Revision ID: 0010
Revises: 0009
Create Date: 2026-02-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RSS_CHANNELS = [
    # ── Tier A: 긍정 뉴스 전문 매체 ──────────────────────────────────────────
    {
        "display_name": "Good News Network",
        "source_type": "rss", "tier": "A", "base_confidence": 0.95, "language": "en",
        "feed_url": "https://www.goodnewsnetwork.org/feed/",
        "topics": ["kindness", "rescue", "community", "recovery", "children", "health", "animals", "elderly", "peace"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "Good News Network - Animals",
        "source_type": "rss", "tier": "A", "base_confidence": 0.95, "language": "en",
        "feed_url": "https://www.goodnewsnetwork.org/category/news/animals/feed/",
        "topics": ["animals", "rescue"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "Good News Network - Health",
        "source_type": "rss", "tier": "A", "base_confidence": 0.95, "language": "en",
        "feed_url": "https://www.goodnewsnetwork.org/category/news/health/feed/",
        "topics": ["health", "recovery"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "Good News Network - Heroes",
        "source_type": "rss", "tier": "A", "base_confidence": 0.95, "language": "en",
        "feed_url": "https://www.goodnewsnetwork.org/category/news/heroes/feed/",
        "topics": ["rescue", "kindness", "community"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "Good News Network - Kids",
        "source_type": "rss", "tier": "A", "base_confidence": 0.95, "language": "en",
        "feed_url": "https://www.goodnewsnetwork.org/category/news/kids/feed/",
        "topics": ["children", "kindness", "community"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "Positive News",
        "source_type": "rss", "tier": "A", "base_confidence": 0.92, "language": "en",
        "feed_url": "https://www.positive.news/feed/",
        "topics": ["community", "peace", "recovery", "health", "children"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "Reasons to be Cheerful",
        "source_type": "rss", "tier": "A", "base_confidence": 0.90, "language": "en",
        "feed_url": "https://reasonstobecheerful.world/feed/",
        "topics": ["community", "peace", "recovery", "health", "children"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "Good Good Good",
        "source_type": "rss", "tier": "A", "base_confidence": 0.88, "language": "en",
        "feed_url": "https://www.goodgoodgood.co/articles/rss",
        "topics": ["kindness", "community", "peace", "recovery"],
        "geo_focus": ["global"],
    },
    # ── Tier B: 준전문 긍정 뉴스 / 주요 매체 긍정 섹션 ─────────────────────
    {
        "display_name": "Upworthy",
        "source_type": "rss", "tier": "B", "base_confidence": 0.82, "language": "en",
        "feed_url": "https://www.upworthy.com/feeds/feed.rss",
        "topics": ["kindness", "community", "children", "reunion", "rescue"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "The Optimist Daily",
        "source_type": "rss", "tier": "B", "base_confidence": 0.85, "language": "en",
        "feed_url": "https://www.optimistdaily.com/feed/",
        "topics": ["health", "community", "recovery", "peace", "children"],
        "geo_focus": ["global"],
    },
]


def upgrade() -> None:
    conn = op.get_bind()

    result = conn.execute(sa.text("SELECT COUNT(*) FROM source_channels WHERE source_type = 'rss'"))
    count = result.scalar()
    if count and count > 0:
        return

    for ch in RSS_CHANNELS:
        conn.execute(
            sa.text("""
                INSERT INTO source_channels
                  (display_name, source_type, tier, base_confidence, language,
                   feed_url, topics, geo_focus, is_active)
                VALUES
                  (:display_name, :source_type, :tier, :base_confidence, :language,
                   :feed_url, :topics, :geo_focus, true)
                ON CONFLICT DO NOTHING
            """).bindparams(
                sa.bindparam("topics", type_=sa.ARRAY(sa.Text())),
                sa.bindparam("geo_focus", type_=sa.ARRAY(sa.Text())),
            ),
            {
                "display_name": ch["display_name"],
                "source_type": ch["source_type"],
                "tier": ch["tier"],
                "base_confidence": ch["base_confidence"],
                "language": ch["language"],
                "feed_url": ch["feed_url"],
                "topics": ch["topics"],
                "geo_focus": ch["geo_focus"],
            },
        )


def downgrade() -> None:
    op.execute("DELETE FROM source_channels WHERE source_type = 'rss'")
