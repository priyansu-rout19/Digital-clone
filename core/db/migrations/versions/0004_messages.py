"""Add messages table for conversation persistence.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "clone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Text(), nullable=False, server_default="anonymous"),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("silence_triggered", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("cited_sources", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Create indexes for efficient queries
    op.create_index("idx_messages_clone_id", "messages", ["clone_id"])
    op.create_index("idx_messages_user_id", "messages", ["user_id"])
    op.create_index("idx_messages_clone_user", "messages", ["clone_id", "user_id"])
    # DESC index for efficient "latest messages first" queries
    op.execute("CREATE INDEX idx_messages_created_at ON messages (created_at DESC)")


def downgrade() -> None:
    op.drop_table("messages")
