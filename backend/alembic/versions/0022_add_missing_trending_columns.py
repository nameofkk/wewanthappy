"""trending_keywords 누락 컬럼 추가

Revision ID: 0022
Revises: 0021
Create Date: 2026-02-27

trending_keywords 테이블에 모델에서 사용하는데 마이그레이션에서 누락된 컬럼 추가:
- keyword_ko, event_count, warmth, is_touching
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # keyword_ko
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='trending_keywords' AND column_name='keyword_ko'"
    ))
    if not result.fetchone():
        op.add_column("trending_keywords", sa.Column("keyword_ko", sa.String(256), nullable=True))

    # event_count
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='trending_keywords' AND column_name='event_count'"
    ))
    if not result.fetchone():
        op.add_column("trending_keywords", sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"))

    # warmth
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='trending_keywords' AND column_name='warmth'"
    ))
    if not result.fetchone():
        op.add_column("trending_keywords", sa.Column("warmth", sa.Integer(), nullable=False, server_default="0"))

    # is_touching
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='trending_keywords' AND column_name='is_touching'"
    ))
    if not result.fetchone():
        op.add_column("trending_keywords", sa.Column("is_touching", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("trending_keywords", "is_touching")
    op.drop_column("trending_keywords", "warmth")
    op.drop_column("trending_keywords", "event_count")
    op.drop_column("trending_keywords", "keyword_ko")
