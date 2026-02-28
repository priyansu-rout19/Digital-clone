"""Initial schema: 6 core tables for all clients.

Revision ID: 0001
Revises:
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None          # This is the first migration — no parent
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users (no dependencies) ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.Text(), unique=True),
        sa.Column("name", sa.Text()),
        sa.Column("role", sa.String(20)),
        sa.Column("oauth_provider", sa.String(20)),
        sa.Column("oauth_id", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # --- clones (no dependencies) ---
    op.create_table(
        "clones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(64), unique=True, nullable=False),
        sa.Column("display_name", sa.Text()),
        sa.Column("bio", sa.Text()),
        sa.Column("avatar_url", sa.Text()),
        sa.Column("profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(20), server_default="provisioning", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_clones_slug", "clones", ["slug"], unique=True)

    # --- documents (depends on clones) ---
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("clone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(20)),
        sa.Column("mime_type", sa.String(64)),
        sa.Column("file_path", sa.Text()),
        sa.Column("zvec_collection", sa.Text()),
        sa.Column("pageindex_tree_path", sa.Text()),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_documents_clone_id", "documents", ["clone_id"])
    op.create_index("idx_documents_status", "documents", ["status"])

    # --- review_queue (depends on clones) ---
    op.create_table(
        "review_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("clone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("session_id", postgresql.UUID(as_uuid=True)),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("cited_sources", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True)),
        sa.Column("reviewer_notes", sa.Text()),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_review_queue_clone_id", "review_queue", ["clone_id"])
    op.create_index("idx_review_queue_status", "review_queue", ["status"])

    # --- audit_log (no FK dependencies, BIGSERIAL PK) ---
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("clone_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(50)),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_role", sa.String(20)),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_audit_log_clone_id", "audit_log", ["clone_id"])
    op.create_index("idx_audit_log_action", "audit_log", ["action"])
    # Use op.execute for DESC index (Alembic op.create_index doesn't support it)
    op.execute("CREATE INDEX idx_audit_log_created_at ON audit_log (created_at DESC)")

    # --- query_analytics (depends on clones) ---
    op.create_table(
        "query_analytics",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("clone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clones.id")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("query_text", sa.Text()),
        sa.Column("intent_class", sa.String(20)),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("tier_used", sa.String(20)),
        sa.Column("silence_triggered", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_query_analytics_clone_id", "query_analytics", ["clone_id"])
    # Use op.execute for DESC index
    op.execute("CREATE INDEX idx_query_analytics_created_at ON query_analytics (created_at DESC)")


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("query_analytics")
    op.drop_table("audit_log")
    op.drop_table("review_queue")
    op.drop_table("documents")
    op.drop_table("clones")
    op.drop_table("users")
