# Components

Engineering specifications for each component of the Digital Clone Engine.

| # | Component | Status | Files |
|---|---|---|---|
| **01** | Clone Profile Config Model | ✅ COMPLETE | `core/models/clone_profile.py` |
| **02** | RAG Pipeline (Ingestion + Retrieval + Semantic Chunking) | ✅ COMPLETE (v1.1 — Session 13) | `core/rag/` |
| **03** | PostgreSQL Database Schema | ✅ COMPLETE (v1.5 — applied + seeded) | `core/db/schema.py`, `core/db/migrations/` |
| **04** | LangGraph Orchestration (19-node graph) | ✅ COMPLETE (v2.1) | `core/langgraph/conversation_flow.py` |
| **05** | FastAPI Gateway + 3 Improvements | ✅ COMPLETE (v1.1) | `api/main.py`, `api/middleware.py`, `api/routes/` |
| **06** | Database Seeding Scripts | ✅ COMPLETE (Session 12) | `scripts/seed_db.py`, `scripts/ingest_samples.py` |

## Component 01: Clone Profile Config

**Location:** `core/models/clone_profile.py` (197 lines)

The configuration object that drives all behavioral differences between ParaGPT and Sacred Archive. 7 enums, 17 fields, Pydantic model with cross-field validators. Session 13 added `ChunkingStrategy` enum and `chunking_strategy` field.

See [ARCHITECTURE.md](../ARCHITECTURE.md#3-clone-profile--the-configuration-object) for details.

## Component 02: RAG Pipeline

**Location:** `core/rag/`

Ingestion pipeline (parse → chunk → embed → index) and retrieval (Tier 1 vector search + Tier 2 tree search with self-correction).

**Session 13 — Semantic Chunking Upgrade:**
- Upgraded chunker from paragraph-aware fixed-size to TRUE semantic chunking
- Uses LangChain's `SemanticChunker` + Voyage AI embeddings to detect topic boundaries
- Old chunker preserved as fallback (`fixed_size` strategy via `ChunkingStrategy` enum)
- Re-ingested sample docs: 4 fixed-size chunks → 8 semantic chunks (better topic separation)
- New dependency: `langchain-experimental==0.4.1`
- Files modified: `chunker.py`, `pipeline.py`, `clone_profile.py`, `requirements.txt`
- Files created: `tests/test_chunker.py` (10 new tests)

## Component 03: Database Schema

**Location:** `core/db/schema.py` (360 lines) + `core/db/migrations/` (15 tables, 4 migrations)

SQLAlchemy 2.0 ORM models. 6 core tables (all clients) + 8 provenance tables (Sacred Archive) + document_chunks (pgvector). Session 12: All migrations applied, database seeded.

See [core/db/README.md](../../core/db/README.md) for schema details.

## Component 04: LangGraph Orchestration

**Location:** `core/langgraph/conversation_flow.py` (320+ lines) + `core/langgraph/nodes/` (5 files)

The orchestration graph. 19 nodes (query analysis, retrieval, context assembly, generation, verification, routing, memory). Profile-driven conditional edges via closures.

Real nodes: query_analyzer, tier1_retrieval, context_assembler, in_persona_generator, confidence_scorer, citation_verifier, memory_retrieval, memory_writer, review_queue_writer.

## Component 05: FastAPI Gateway + API Improvements (Session 11)

**Location:** `api/` (6 files, 700+ lines) + `core/db/migrations/0004_messages.py`

The HTTP gateway layer. 5 endpoint groups (health, config, chat, ingest, review) + WebSocket streaming. Session 11 additions:

**Feature 1: Conversation Persistence**
- New ORM model: `Message` (1 row per chat exchange)
- Migration 0004: messages table (9 columns, 4 indexes: clone_id, user_id, composite)
- Modified POST /chat + WS handler: saves message after completion
- Use case: Audit trail, conversation history retrieval, analytics

**Feature 2: Ingest Status Polling**
- New endpoint: `GET /ingest/{slug}/status/{doc_id}`
- Returns: doc_id, filename, status, chunk_count, timestamps, human-readable message
- Cross-clone isolation: validates both doc_id AND clone_id
- Use case: Async document processing progress tracking

**Feature 3: API Key Validation + Access Tier Checks**
- New middleware: `APIKeyMiddleware` (X-API-Key header validation)
- Check against `DCE_API_KEY` env var (empty = allow all for backward compatibility)
- Exempt paths: /health, /docs, /openapi.json, /redoc
- Access tier: Added to ChatRequest, validates against AccessTier enum
- Use case: Authenticate API requests, enforce content access tiers

**Tests:** 33 HTTP endpoint tests (18 original + 15 new), all passing. Total suite: 65 tests (+ 10 chunker tests Session 13).

## Component 06: Database Seeding Scripts (Session 12)

**Location:** `scripts/` (4 files)

Database setup utilities for populating the system with initial data.

- `seed_db.py` (~120 lines) — Idempotent seeder using factory functions from `clone_profile.py`
  - 2 clone profiles (ParaGPT + Sacred Archive)
  - 1 admin user (Sacred Archive reviewer)
  - Provenance graph data (2 teachings, 2 topics, 1 scripture, 1 source)
- `ingest_samples.py` (~80 lines) — Runs sample docs through real IngestionPipeline
  - 2 markdown documents → 8 semantic chunks with Voyage AI 1024-dim embeddings
- `sample_docs/paragpt_sample.md` — ParaGPT sample (geopolitics/connectivity)
- `sample_docs/sacred_archive_sample.md` — Sacred Archive sample (compassion teachings)
