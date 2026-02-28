"""
Database Schema (Component 03)

SQLAlchemy 2.0 ORM models for all persistent tables.
Pydantic schemas for JSONB column validation.

Two migration targets:
  - Migration 0001: clones, documents, review_queue, audit_log, users, query_analytics
  - Migration 0002: teachings, teaching_sources, topics, scriptures + junction tables
                    (Sacred Archive provenance graph — replaces Apache AGE)
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


# ============================================================================
# PYDANTIC SCHEMAS FOR JSONB COLUMNS
# ============================================================================
# These define the structure of data stored in JSONB columns.
# Use these when reading/writing to prevent KeyError surprises at runtime.
# ============================================================================


class DocumentProvenance(BaseModel):
    """
    Structure for documents.provenance JSONB column.

    Mandatory for Sacred Archive, optional for ParaGPT.
    Captures origin metadata for every ingested document.
    """

    date: Optional[str] = Field(None, description="Teaching/publication date (ISO 8601)")
    location: Optional[str] = Field(None, description="Physical location where teaching occurred")
    event: Optional[str] = Field(None, description="Event name (retreat, satsang, class)")
    verifier: Optional[str] = Field(None, description="Name of human who verified this document")
    access_tier: str = Field("public", description="public | devotee | friend | follower")
    source_url: Optional[str] = Field(None, description="Original URL or recording reference")
    notes: Optional[str] = Field(None, description="Archivist notes")


class CitedSource(BaseModel):
    """
    One element in the review_queue.cited_sources JSONB array.

    Mirrors the structure in ConversationState.cited_sources from conversation_flow.py.
    """

    doc_id: str = Field(description="UUID of the document in the documents table")
    chunk_id: str = Field(description="Chunk identifier within the document")
    passage: str = Field(description="The actual text passage that was cited")
    provenance: Optional[dict] = Field(None, description="DocumentProvenance data for this source")


class AuditDetails(BaseModel):
    """
    Structure for audit_log.details JSONB column.

    Fields vary by action type — use Optional for action-specific fields.
    """

    query_id: Optional[str] = Field(None, description="review_queue row ID if action=query")
    response_id: Optional[str] = Field(None, description="review_queue row ID if action=response")
    decision: Optional[str] = Field(None, description="approved | rejected | edited")
    reason: Optional[str] = Field(None, description="Human-readable reason for decision")
    confidence_score: Optional[float] = Field(None, description="Score at time of action")
    session_id: Optional[str] = Field(None, description="Conversation session identifier")
    previous_status: Optional[str] = Field(None, description="Status before this action")
    new_status: Optional[str] = Field(None, description="Status after this action")


# ============================================================================
# SQLALCHEMY BASE
# ============================================================================


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    Alembic's env.py imports Base.metadata to auto-discover all tables
    and generate migrations. Every model below inherits from this.
    """

    pass


# ============================================================================
# MIGRATION 0001: CORE TABLES (ALL CLIENTS)
# ============================================================================


class User(Base):
    """
    Authentication and role management.
    Roles differ per client: ParaGPT has creator/admin, Sacred Archive has reviewer/curator.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    role: Mapped[Optional[str]] = mapped_column(String(20))
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(20))
    oauth_id: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("idx_users_email", "email"),)


class Clone(Base):
    """
    One row per digital clone.
    Stores identity and the full CloneProfile config as JSONB.
    profile JSONB is what LangGraph reads at request time via build_graph(profile).
    """

    __tablename__ = "clones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(Text)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    profile: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), server_default="provisioning", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships (for ORM convenience)
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="clone", cascade="all, delete-orphan"
    )
    review_queue_items: Mapped[list["ReviewQueue"]] = relationship(
        "ReviewQueue", back_populates="clone"
    )

    __table_args__ = (Index("idx_clones_slug", "slug"),)


class Document(Base):
    """
    One row per ingested document per clone.
    Tracks file metadata, ingestion status, and provenance.
    provenance JSONB is DocumentProvenance (mandatory for Sacred Archive, optional for ParaGPT).
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[Optional[str]] = mapped_column(String(20))
    mime_type: Mapped[Optional[str]] = mapped_column(String(64))
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    zvec_collection: Mapped[Optional[str]] = mapped_column(Text)
    pageindex_tree_path: Mapped[Optional[str]] = mapped_column(Text)
    provenance: Mapped[Optional[dict]] = mapped_column(JSONB)
    chunk_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default="queued", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    clone: Mapped["Clone"] = relationship("Clone", back_populates="documents")

    __table_args__ = (
        Index("idx_documents_clone_id", "clone_id"),
        Index("idx_documents_status", "status"),
    )


class ReviewQueue(Base):
    """
    Responses awaiting human review.
    Sacred Archive routes ALL responses here (review_required=True).
    ParaGPT only routes here when confidence < threshold AND silence_behavior=strict_silence.
    This table is what review_queue_writer node (routing_nodes.py) will write to.
    """

    __tablename__ = "review_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    cited_sources: Mapped[Optional[list]] = mapped_column(JSONB)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), server_default="pending", nullable=False)
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    clone: Mapped["Clone"] = relationship("Clone", back_populates="review_queue_items")

    __table_args__ = (
        Index("idx_review_queue_clone_id", "clone_id"),
        Index("idx_review_queue_status", "status"),
    )


class AuditLog(Base):
    """
    Immutable event log. BIGSERIAL PK guarantees ordering — row 1001 always after 1000.
    No updated_at because audit rows must never change.
    Required for Sacred Archive. Recommended for ParaGPT.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    clone_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    action: Mapped[Optional[str]] = mapped_column(String(50))
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    actor_role: Mapped[Optional[str]] = mapped_column(String(20))
    details: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_audit_log_clone_id", "clone_id"),
        Index("idx_audit_log_action", "action"),
    )


class QueryAnalytics(Base):
    """
    Per-query performance metrics.
    BIGSERIAL PK for efficient time-series append. Not UUID because this table
    grows fast and we never need to reference rows by ID from outside.
    """

    __tablename__ = "query_analytics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    clone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clones.id"),
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    query_text: Mapped[Optional[str]] = mapped_column(Text)
    intent_class: Mapped[Optional[str]] = mapped_column(String(20))
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    tier_used: Mapped[Optional[str]] = mapped_column(String(20))
    silence_triggered: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_query_analytics_clone_id", "clone_id"),
    )


# ============================================================================
# MIGRATION 0002: PROVENANCE GRAPH (SACRED ARCHIVE ONLY)
# Replaces Apache AGE (eliminated Oct 2024) with pure PostgreSQL tables.
# Recursive CTEs on teaching_relations enable graph traversal queries.
# ============================================================================


class TeachingSource(Base):
    """
    Source node: The physical origin of a teaching.
    A teaching always comes FROM a source (event, recording, document).
    """

    __tablename__ = "teaching_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[Optional[str]] = mapped_column(String(20))
    event_name: Mapped[Optional[str]] = mapped_column(Text)
    recording_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    teachings: Mapped[list["Teaching"]] = relationship("Teaching", back_populates="source")


class Topic(Base):
    """
    Topic node: A thematic category (forgiveness, devotion, compassion).
    UNIQUE name prevents duplicates.
    """

    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    teachings: Mapped[list["Teaching"]] = relationship(
        "Teaching", secondary="teaching_topics", back_populates="topics"
    )

    __table_args__ = (Index("idx_topics_name", "name"),)


class Scripture(Base):
    """
    Scripture node: A canonical text reference (Bhagavad Gita 2.47, etc).
    """

    __tablename__ = "scriptures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(Text, nullable=False)
    tradition: Mapped[Optional[str]] = mapped_column(Text)

    teachings: Mapped[list["Teaching"]] = relationship(
        "Teaching", secondary="teaching_scriptures", back_populates="scriptures"
    )


class Teaching(Base):
    """
    Teaching node: Core entity in the provenance graph.
    One row per discrete teaching unit (a talk, a passage, a recorded session).

    chunk_refs JSONB: references to specific chunks in the documents table
    Format: [{"doc_id": "...", "chunk_id": "..."}]

    access_tier: enforced at query time for Sacred Archive access control.
    """

    __tablename__ = "teachings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(Text)
    date: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(Text)
    access_tier: Mapped[str] = mapped_column(String(20), server_default="public", nullable=False)
    chunk_refs: Mapped[Optional[list]] = mapped_column(JSONB)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teaching_sources.id"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    source: Mapped[Optional["TeachingSource"]] = relationship("TeachingSource", back_populates="teachings")
    topics: Mapped[list["Topic"]] = relationship(
        "Topic", secondary="teaching_topics", back_populates="teachings"
    )
    scriptures: Mapped[list["Scripture"]] = relationship(
        "Scripture", secondary="teaching_scriptures", back_populates="teachings"
    )
    reviewers: Mapped[list["User"]] = relationship(
        "User", secondary="teaching_reviewer_links"
    )

    __table_args__ = (
        Index("idx_teachings_clone_id", "clone_id"),
        Index("idx_teachings_access_tier", "access_tier"),
    )


class TeachingTopic(Base):
    """
    Teaching <-> Topic junction table.
    Models the ABOUT relationship: a teaching is about one or more topics.
    """

    __tablename__ = "teaching_topics"

    teaching_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachings.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )


class TeachingScripture(Base):
    """
    Teaching <-> Scripture junction table.
    Models the REFERENCES relationship: a teaching references one or more scriptures.
    """

    __tablename__ = "teaching_scriptures"

    teaching_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachings.id", ondelete="CASCADE"), primary_key=True
    )
    scripture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scriptures.id", ondelete="CASCADE"), primary_key=True
    )


class TeachingRelation(Base):
    """
    Self-referential Teaching <-> Teaching relation table.
    Models the RELATED_TO relationship — one teaching relates to another.

    relation_type: 'related' | 'elaborates' | 'contradicts' | 'precedes'

    This is the key table for recursive CTE graph traversal.
    Example query (find all teachings related to T within 3 hops):

        WITH RECURSIVE chain AS (
          SELECT to_teaching_id AS id, 1 AS depth
          FROM teaching_relations WHERE from_teaching_id = $1
          UNION ALL
          SELECT tr.to_teaching_id, c.depth + 1
          FROM teaching_relations tr JOIN chain c ON tr.from_teaching_id = c.id
          WHERE c.depth < 3
        )
        SELECT * FROM teachings WHERE id IN (SELECT id FROM chain);
    """

    __tablename__ = "teaching_relations"

    from_teaching_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachings.id", ondelete="CASCADE"), primary_key=True
    )
    to_teaching_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachings.id", ondelete="CASCADE"), primary_key=True
    )
    relation_type: Mapped[str] = mapped_column(String(20), nullable=False)


class TeachingReviewerLink(Base):
    """
    Teaching <-> Reviewer (User) junction table.
    Models the VERIFIED_BY relationship: a teaching is verified by a human reviewer.
    """

    __tablename__ = "teaching_reviewer_links"

    teaching_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachings.id", ondelete="CASCADE"), primary_key=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
