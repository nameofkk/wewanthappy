"""seed more rss channels — 긍정 뉴스 추가 피드

Revision ID: 0011
Revises: 0010
Create Date: 2026-02-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MORE_RSS_CHANNELS = [
    # ── Tier B 추가 ──────────────────────────────────────────────────────────
    {
        "display_name": "InspireMore",
        "source_type": "rss", "tier": "B", "base_confidence": 0.80, "language": "en",
        "feed_url": "https://www.inspiremore.com/feed/",
        "topics": ["kindness", "animals", "children", "reunion", "elderly"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "Sunny Skyz",
        "source_type": "rss", "tier": "B", "base_confidence": 0.80, "language": "en",
        "feed_url": "https://feeds.feedburner.com/SunnySkyz",
        "topics": ["kindness", "animals", "children", "rescue", "reunion"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "DailyGood",
        "source_type": "rss", "tier": "B", "base_confidence": 0.78, "language": "en",
        "feed_url": "https://www.dailygood.org/rss/stories.xml",
        "topics": ["kindness", "community", "peace", "elderly"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "Tank's Good News",
        "source_type": "rss", "tier": "B", "base_confidence": 0.78, "language": "en",
        "feed_url": "https://tanksgoodnews.com/feed/",
        "topics": ["kindness", "rescue", "reunion", "animals", "community"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "Washington Post - The Optimist",
        "source_type": "rss", "tier": "B", "base_confidence": 0.82, "language": "en",
        "feed_url": "https://feeds.washingtonpost.com/rss/lifestyle/inspired-life",
        "topics": ["kindness", "reunion", "rescue", "community", "children", "elderly"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "The Dodo",
        "source_type": "rss", "tier": "B", "base_confidence": 0.85, "language": "en",
        "feed_url": "https://www.thedodo.com/rss",
        "topics": ["animals", "rescue", "kindness"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "YES! Magazine",
        "source_type": "rss", "tier": "B", "base_confidence": 0.75, "language": "en",
        "feed_url": "https://www.yesmagazine.org/feed",
        "topics": ["community", "peace", "recovery", "children"],
        "geo_focus": ["global"],
    },
    # ── Tier C: 보조 소스 ─────────────────────────────────────────────────────
    {
        "display_name": "Reddit - r/UpliftingNews",
        "source_type": "rss", "tier": "C", "base_confidence": 0.55, "language": "en",
        "feed_url": "https://www.reddit.com/r/UpliftingNews/.rss",
        "topics": ["kindness", "rescue", "reunion", "community", "recovery", "animals"],
        "geo_focus": ["global"],
    },
    {
        "display_name": "ScienceDaily - Health",
        "source_type": "rss", "tier": "C", "base_confidence": 0.60, "language": "en",
        "feed_url": "https://rss.sciencedaily.com/health_medicine.xml",
        "topics": ["health", "recovery"],
        "geo_focus": ["global"],
    },
]

_INSERT_SQL = sa.text("""
    INSERT INTO source_channels
      (display_name, source_type, tier, base_confidence, language,
       feed_url, topics, geo_focus, is_active)
    SELECT
      :display_name, :source_type, :tier, :base_confidence, :language,
      :feed_url, :topics, :geo_focus, true
    WHERE NOT EXISTS (
      SELECT 1 FROM source_channels WHERE feed_url = :feed_url
    )
""").bindparams(
    sa.bindparam("topics", type_=sa.ARRAY(sa.Text())),
    sa.bindparam("geo_focus", type_=sa.ARRAY(sa.Text())),
)


def upgrade() -> None:
    conn = op.get_bind()
    for ch in MORE_RSS_CHANNELS:
        conn.execute(_INSERT_SQL, {
            "display_name": ch["display_name"],
            "source_type": ch["source_type"],
            "tier": ch["tier"],
            "base_confidence": ch["base_confidence"],
            "language": ch["language"],
            "feed_url": ch["feed_url"],
            "topics": ch["topics"],
            "geo_focus": ch["geo_focus"],
        })


def downgrade() -> None:
    feeds = [ch["feed_url"] for ch in MORE_RSS_CHANNELS]
    conn = op.get_bind()
    for feed_url in feeds:
        conn.execute(
            sa.text("DELETE FROM source_channels WHERE feed_url = :feed_url"),
            {"feed_url": feed_url},
        )
