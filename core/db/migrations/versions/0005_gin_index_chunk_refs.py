"""Add GIN index on teachings.chunk_refs for JSONB containment queries.

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-04
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX idx_teachings_chunk_refs "
        "ON teachings USING gin (chunk_refs jsonb_path_ops)"
    )


def downgrade() -> None:
    op.drop_index("idx_teachings_chunk_refs", table_name="teachings")
