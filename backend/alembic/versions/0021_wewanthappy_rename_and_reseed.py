"""WeWantHappy 컬럼 리네이밍 + RSS 소스 교체

Revision ID: 0021
Revises: 0020
Create Date: 2026-02-27

기존 배포된 DB에서:
1. story_clusters.spike_at → touching_at
2. user_preferences.min_severity → min_warmth
3. user_preferences.min_kscore → min_hscore
4. user_preferences.topics 기본값 → 긍정 토픽
5. 기존 RSS 소스 삭제 → 긍정 뉴스 피드 삽입
6. OSINT 텔레그램 채널 비활성화
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POSITIVE_RSS_FEEDS = [
    # Tier A
    {"display_name": "Good News Network", "tier": "A", "base_confidence": 0.95, "language": "en",
     "feed_url": "https://www.goodnewsnetwork.org/feed/",
     "topics": ["kindness", "rescue", "community", "recovery", "children", "health", "animals", "elderly", "peace"]},
    {"display_name": "Good News Network - Animals", "tier": "A", "base_confidence": 0.95, "language": "en",
     "feed_url": "https://www.goodnewsnetwork.org/category/news/animals/feed/",
     "topics": ["animals", "rescue"]},
    {"display_name": "Good News Network - Health", "tier": "A", "base_confidence": 0.95, "language": "en",
     "feed_url": "https://www.goodnewsnetwork.org/category/news/health/feed/",
     "topics": ["health", "recovery"]},
    {"display_name": "Good News Network - Heroes", "tier": "A", "base_confidence": 0.95, "language": "en",
     "feed_url": "https://www.goodnewsnetwork.org/category/news/heroes/feed/",
     "topics": ["rescue", "kindness", "community"]},
    {"display_name": "Good News Network - Kids", "tier": "A", "base_confidence": 0.95, "language": "en",
     "feed_url": "https://www.goodnewsnetwork.org/category/news/kids/feed/",
     "topics": ["children", "kindness", "community"]},
    {"display_name": "Positive News", "tier": "A", "base_confidence": 0.92, "language": "en",
     "feed_url": "https://www.positive.news/feed/",
     "topics": ["community", "peace", "recovery", "health", "children"]},
    {"display_name": "Reasons to be Cheerful", "tier": "A", "base_confidence": 0.90, "language": "en",
     "feed_url": "https://reasonstobecheerful.world/feed/",
     "topics": ["community", "peace", "recovery", "health", "children"]},
    {"display_name": "Good Good Good", "tier": "A", "base_confidence": 0.88, "language": "en",
     "feed_url": "https://www.goodgoodgood.co/articles/rss",
     "topics": ["kindness", "community", "peace", "recovery"]},
    # Tier B
    {"display_name": "Upworthy", "tier": "B", "base_confidence": 0.82, "language": "en",
     "feed_url": "https://www.upworthy.com/feeds/feed.rss",
     "topics": ["kindness", "community", "children", "reunion", "rescue"]},
    {"display_name": "The Optimist Daily", "tier": "B", "base_confidence": 0.85, "language": "en",
     "feed_url": "https://www.optimistdaily.com/feed/",
     "topics": ["health", "community", "recovery", "peace", "children"]},
    {"display_name": "InspireMore", "tier": "B", "base_confidence": 0.80, "language": "en",
     "feed_url": "https://www.inspiremore.com/feed/",
     "topics": ["kindness", "animals", "children", "reunion", "elderly"]},
    {"display_name": "Sunny Skyz", "tier": "B", "base_confidence": 0.80, "language": "en",
     "feed_url": "https://feeds.feedburner.com/SunnySkyz",
     "topics": ["kindness", "animals", "children", "rescue", "reunion"]},
    {"display_name": "DailyGood", "tier": "B", "base_confidence": 0.78, "language": "en",
     "feed_url": "https://www.dailygood.org/rss/stories.xml",
     "topics": ["kindness", "community", "peace", "elderly"]},
    {"display_name": "Tank's Good News", "tier": "B", "base_confidence": 0.78, "language": "en",
     "feed_url": "https://tanksgoodnews.com/feed/",
     "topics": ["kindness", "rescue", "reunion", "animals", "community"]},
    {"display_name": "Washington Post - The Optimist", "tier": "B", "base_confidence": 0.82, "language": "en",
     "feed_url": "https://feeds.washingtonpost.com/rss/lifestyle/inspired-life",
     "topics": ["kindness", "reunion", "rescue", "community", "children", "elderly"]},
    {"display_name": "The Dodo", "tier": "B", "base_confidence": 0.85, "language": "en",
     "feed_url": "https://www.thedodo.com/rss",
     "topics": ["animals", "rescue", "kindness"]},
    {"display_name": "YES! Magazine", "tier": "B", "base_confidence": 0.75, "language": "en",
     "feed_url": "https://www.yesmagazine.org/feed",
     "topics": ["community", "peace", "recovery", "children"]},
    # Tier C
    {"display_name": "Reddit - r/UpliftingNews", "tier": "C", "base_confidence": 0.55, "language": "en",
     "feed_url": "https://www.reddit.com/r/UpliftingNews/.rss",
     "topics": ["kindness", "rescue", "reunion", "community", "recovery", "animals"]},
    {"display_name": "ScienceDaily - Health", "tier": "C", "base_confidence": 0.60, "language": "en",
     "feed_url": "https://rss.sciencedaily.com/health_medicine.xml",
     "topics": ["health", "recovery"]},
]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. story_clusters.spike_at → touching_at (존재하면)
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='story_clusters' AND column_name='spike_at'"
    ))
    if result.fetchone():
        op.alter_column("story_clusters", "spike_at", new_column_name="touching_at")

    # spike 인덱스 → touching 인덱스
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_cluster_spike"))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_cluster_touching "
        "ON story_clusters (is_touching, touching_at)"
    ))

    # 2. user_preferences.min_severity → min_warmth (존재하면)
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='user_preferences' AND column_name='min_severity'"
    ))
    if result.fetchone():
        op.alter_column("user_preferences", "min_severity", new_column_name="min_warmth")

    # 3. user_preferences.min_kscore → min_hscore (존재하면)
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='user_preferences' AND column_name='min_kscore'"
    ))
    if result.fetchone():
        op.alter_column("user_preferences", "min_kscore", new_column_name="min_hscore")

    # 4. topics 기본값 변경
    conn.execute(sa.text(
        "ALTER TABLE user_preferences "
        "ALTER COLUMN topics SET DEFAULT "
        "'{kindness,reunion,rescue,community,recovery,children,health,animals,elderly,peace}'"
    ))

    # 5. 기존 RSS 소스 삭제 → 긍정 뉴스 피드 삽입
    conn.execute(sa.text("DELETE FROM source_channels WHERE source_type = 'rss'"))
    for ch in POSITIVE_RSS_FEEDS:
        conn.execute(
            sa.text("""
                INSERT INTO source_channels
                  (display_name, source_type, tier, base_confidence, language,
                   feed_url, topics, geo_focus, is_active)
                VALUES
                  (:display_name, 'rss', :tier, :base_confidence, :language,
                   :feed_url, :topics, '{global}', true)
                ON CONFLICT DO NOTHING
            """).bindparams(
                sa.bindparam("topics", type_=sa.ARRAY(sa.Text())),
            ),
            {
                "display_name": ch["display_name"],
                "tier": ch["tier"],
                "base_confidence": ch["base_confidence"],
                "language": ch["language"],
                "feed_url": ch["feed_url"],
                "topics": ch["topics"],
            },
        )

    # 6. OSINT 텔레그램 채널 비활성화
    conn.execute(sa.text(
        "UPDATE source_channels SET is_active = false WHERE source_type = 'telegram'"
    ))


def downgrade() -> None:
    conn = op.get_bind()

    # touching_at → spike_at
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='story_clusters' AND column_name='touching_at'"
    ))
    if result.fetchone():
        op.alter_column("story_clusters", "touching_at", new_column_name="spike_at")

    # min_warmth → min_severity
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='user_preferences' AND column_name='min_warmth'"
    ))
    if result.fetchone():
        op.alter_column("user_preferences", "min_warmth", new_column_name="min_severity")

    # min_hscore → min_kscore
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='user_preferences' AND column_name='min_hscore'"
    ))
    if result.fetchone():
        op.alter_column("user_preferences", "min_hscore", new_column_name="min_kscore")
