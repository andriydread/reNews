"""timezone-aware datetimes

All DateTime columns become timestamptz. Existing naive values were written
by processes running in UTC, so they are reinterpreted AT TIME ZONE 'UTC'.

Revision ID: b7c41d9e2f10
Revises: 5a45668c58d3
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c41d9e2f10"
down_revision: Union[str, None] = "5a45668c58d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = [
    ("feeds", "last_fetched_at"),
    ("articles", "created_at"),
    ("articles", "published_at"),
    ("article_analyses", "ai_processed_at"),
    ("refresh_tokens", "expires_at"),
    ("refresh_tokens", "created_at"),
]


def upgrade() -> None:
    for table, column in COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for table, column in COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=False),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
