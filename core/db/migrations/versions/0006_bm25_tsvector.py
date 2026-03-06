"""Add tsvector column to document_chunks for BM25 hybrid search.

PostgreSQL full-text search (tsvector + GIN index) enables keyword-based
retrieval alongside vector search. Combined via RRF, this breaks the CRAG
retry loop where paraphrased queries always retrieve the same passages.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-06
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tsvector column (raw SQL — SQLAlchemy has no native tsvector type)
    op.execute(
        "ALTER TABLE document_chunks "
        "ADD COLUMN IF NOT EXISTS search_vector tsvector"
    )

    # Populate tsvector from existing passage text
    op.execute(
        "UPDATE document_chunks "
        "SET search_vector = to_tsvector('english', passage)"
    )

    # Create GIN index for fast full-text search
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_search_vector "
        "ON document_chunks USING gin (search_vector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_search_vector")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS search_vector")
