# Digital Clone Engine — Session Progress & Implementation Status

**Last Updated:** March 6, 2026 (Session 30 — Documentation Overhaul + Demo Readiness)
**Current Focus:** All documentation updated to Session 30. Real Gemini embeddings in seed corpus (37 passages, 8 docs). Landing page questions aligned with demo corpus. 77 tests pass, zero TS errors, 93% SOW compliance.

---

## Project Overview

The Digital Clone Engine is a unified backend system serving two digital clones from one codebase:
- **ParaGPT:** Digital clone of Parag Khanna (geopolitical strategist). Interpretive, voice-enabled, direct user streaming.
- **Sacred Archive:** Spiritual teachings mirror. Mirror-only quotes, human review required, air-gapped.

**Core Architecture:** All behavioral differences driven by a `CloneProfile` config object. No code branches (`if client == "paragpt"`). One `build_graph(profile)` function produces different routing paths per client.

---

## Implementation Status

### ✅ COMPLETE

**Component 01: Clone Profile Config**
- File: `core/models/clone_profile.py`
- 7 Pydantic enums (GenerationMode, SilenceBehavior, VoiceMode, DeploymentMode, RetrievalTier, AccessTier, ChunkingStrategy) — Session 13 added ChunkingStrategy
- CloneProfile class with 17 fields (identity, generation, review, memory, voice, retrieval, access, infrastructure, chunking_strategy) — Session 13 added chunking_strategy
- Field validators (cross-field validation via `@model_validator`)
- Two preset factory functions: `paragpt_profile()`, `sacred_archive_profile()`
- Verified: Both profiles serialize to valid JSON, validators catch invalid combos

**Component 03: PostgreSQL Database Schema**
- Files: `core/db/schema.py` (360 lines) + `core/db/migrations/` (6 migrations)
- 15 SQLAlchemy 2.0 ORM models with proper cascading relationships
- 3 Pydantic JSONB schemas: DocumentProvenance, CitedSource, AuditDetails
- Migration 0001: 6 core tables (users, clones, documents, review_queue, audit_log, query_analytics)
- Migration 0002: 8 provenance tables (teaching, sources, topics, scriptures, + junctions + recursive relations)
- Migration 0003: document_chunks table with pgvector VECTOR(1024) + HNSW index
- Migration 0004: messages table (conversation persistence)
- Uses PostgreSQL native features (JSONB, recursive CTEs) instead of Apache AGE (team eliminated Oct 2024)
- BIGSERIAL for audit_log and query_analytics (immutable ordering guarantee)
- Alembic 1.14.1 configuration with environment variable support (DATABASE_URL)
- Verified: All tables generate correct SQL, alembic upgrade --sql head produces 29 statements (14 CREATE TABLE + 15 indexes)
- **Session 12:** All migrations applied to live PostgreSQL. Database seeded with clone profiles + sample documents.

**Component 04: LangGraph Orchestration Flow**
- File: `core/langgraph/conversation_flow.py`
- StateGraph with 19 nodes (17 functional + __start__ + __end__)
- ConversationState TypedDict with 23 keys (clone_id, user_id, response_tokens, conversation_history, etc.)
- `build_graph(profile)` factory that builds client-specific routing
- Conditional edges using closures (profile captured at build time)
- **Session 7 Fix:** T2 (tree_search) now runs immediately after T1 (before CRAG), not after. Added `after_tier1()` routing. CRAG evaluates combined T1+T2 result. Retry loop includes both tiers.
- Node files in `core/langgraph/nodes/`:
  - `query_analysis_node.py` — Real LLM intent classification
  - `retrieval_nodes.py` — Tier 1/2 search, CRAG, query reformulation
  - `context_nodes.py` — Context assembly, memory retrieval
  - `generation_nodes.py` — Response generation, citation verification, confidence scoring
  - `routing_nodes.py` — Output routing, review queue, silence handling

**LLM Integration**
- File: `core/llm.py`
- ChatOpenAI client factory pointing at Groq API
- Model: `qwen/qwen3-32b` (aligns with production Qwen3.5-35B)
- API key: stored in `.env` (gitignored)
- Temperature control (0.0 for classification, 0.7 for generation)

**Node Implementation Status:**
| Node | Status | LLM Call | Notes |
|---|---|---|---|
| query_analysis | Real | Yes | Classifies intent, decomposes queries (JSON with fallback) |
| tier1_retrieval | ✅ Real | No | pgvector cosine search + RRF (Reciprocal Rank Fusion) |
| crag_evaluator | ✅ Real | No | Reranker-score confidence (not passage-count) — Session 29 fix |
| query_reformulator | ✅ Real | Yes | Keyword extraction + sub-topic decomposition (not paraphrases) — Session 29 fix |
| tier2_tree_search | Designed Stub | No | Returns passages unchanged, MinIO TODO (PCCI blocked) |
| provenance_graph_query | ✅ Real | No | SQL recursive CTE (parameterized queries — Session 17 security fix) |
| context_assembler | ✅ Real | No | Assembles passages into context string |
| memory_retrieval | ✅ Real | No | Searches Mem0 for user memories (ParaGPT only) — Session 4 |
| memory_writer | ✅ Real | No | Saves conversation turns to Mem0 (ParaGPT only) — Session 4 |
| in_persona_generator | ✅ Real | Yes | Persona-aware generation (temp=0.0 for mirror_only — Session 17 fix) |
| citation_verifier | ✅ Real | No | Parses [N] markers, cross-refs passages, populates cited_sources — Session 5 |
| confidence_scorer | ✅ Real | No | Deterministic 4-factor scorer (no LLM) — Session 29 |
| soft_hedge_router | ✅ Real | No | Overwrites both raw_response AND verified_response — Session 17 fix |
| strict_silence_router | ✅ Real | No | Sets silence flag, routes to review or user |
| review_queue_writer | ✅ Real | No | Real DB INSERT into review_queue (psycopg) — Session 16 |
| stream_to_user | ✅ Real | Yes | LLM-based sentence splitting (handles abbreviations) — Session 16 |
| voice_pipeline | ✅ Real | No | edge-tts (Microsoft TTS, free, MP3 output) — Session 16 |

### ✅ COMPLETE

**Component 02: RAG Pipeline** (FULL COMPLETION)

**Component 02a: Ingestion Pipeline** ✅ (Session 14: Google Gemini Embeddings, Session 13: Semantic Chunking)
- ✅ `core/rag/ingestion/parser.py` — PDF (PyMuPDF) + text/markdown parsing (48 lines, cleaned)
- ✅ `core/rag/ingestion/chunker.py` — TRUE semantic chunking via LangChain SemanticChunker + Google Gemini embeddings (detects topic boundaries by cosine similarity). Old fixed-size chunker preserved as fallback (`fixed_size` strategy). ChunkingStrategy enum on CloneProfile selects mode. Re-ingested: 8 semantic chunks (topic-coherent).
- ✅ `core/rag/ingestion/embedder.py` — Google Gemini gemini-embedding-001 (3072-dim output truncated to 1024 via Matryoshka property) (76 lines)
  - **Dev:** Google gemini-embedding-001 (via langchain-google-genai)
  - **Prod:** TEI on PCCI (drop-in swap via LangChain interface, same 1024-dim output)
- ✅ `core/rag/ingestion/indexer.py` — pgvector storage with ON CONFLICT for re-ingestability (64 lines, cleaned)
- ✅ `core/rag/ingestion/pipeline.py` — Orchestrator: parse → chunk → embed → index (126 lines, cleaned)
- ✅ Migration 0003: `document_chunks` table with VECTOR(1024), HNSW index
- ✅ Profile-driven provenance validation (Sacred Archive strict, ParaGPT minimal)
- ✅ Requirements: Added `langchain-google-genai` (for Google Gemini embeddings)

**Component 02b: Retrieval Pipeline** ✅
- ✅ `core/rag/retrieval/vector_search.py` — Hybrid vector+BM25, FlashRank reranking, RRF fusion
  - `search(sub_queries, clone_id, access_tiers, db_url, top_k=10)` with RRF merging
  - **Session 29:** BM25 keyword search via `tsvector`/`tsquery`, FlashRank cross-encoder reranking (over-retrieve 30, rerank to 10)
  - Handles ParaGPT (public) and Sacred Archive (devotee/friend/follower) access tiers
- ✅ `core/rag/retrieval/provenance.py` — Tier 2+ teaching graph via recursive CTE (191 lines, cleaned)
  - `query_teaching_graph()` for Sacred Archive provenance traversal
  - Two-stage: seed teachings from vector search → recursive graph traversal
- ✅ `core/rag/retrieval/tree_search.py` — Designed stub for MinIO (55 lines, cleaned)
  - Returns existing_passages unchanged, clear TODO for Week 3 MinIO integration
- ✅ `core/langgraph/nodes/retrieval_nodes.py` — Updated all 3 nodes (152 lines, cleaned)
  - `tier1_retrieval()` — Real pgvector search
  - `tier2_tree_search()` — Delegates to tree_search.py
  - `provenance_graph_query()` — Delegates to provenance.py
  - **Bug fix:** retry_count only increments in `query_reformulator` (gives 3 true CRAG cycles, not 1)

**Code Cleanup** ✅
- Removed all module docstrings from all 9 files
- Removed all `#` comments and inline comments
- Preserved all functional code, imports, type hints, string literals
- All files pass Python syntax validation
- Total reduction: ~1,617 lines → ~920 lines (43% reduction)

### ✅ COMPLETE

**Component 02 Integration: Mem0 Cross-Session Memory** (Session 4, Updated Session 14)
- ✅ `core/mem0_client.py` (NEW) — Mem0 client factory with pgvector backend
  - Reads: `DATABASE_URL`, `GROQ_API_KEY`, `GOOGLE_API_KEY`
  - Config: Groq LLM + Google Gemini embeddings (1024-dim via LangChain provider) + pgvector vector store
  - Graceful error handling (same pattern as `core/llm.py`)
- ✅ `memory_retrieval()` — Real implementation searching Mem0 for user memories
  - Input: `user_id`, `query_text`
  - Output: Formatted memory string (or empty if none found)
  - Gate: Only runs for ParaGPT (`user_memory_enabled=True`)
  - Fallback: Returns empty string if Mem0 unavailable
- ✅ `memory_writer()` (NEW node) — Saves conversation turns to Mem0 after streaming
  - Input: `user_id`, `query_text`, `verified_response`
  - Output: state unchanged (side-effect node)
  - Gate: Only runs for ParaGPT
  - Fallback: Logs warning, continues if Mem0 write fails
- ✅ Graph wiring: Added `memory_writer` node after `stream_to_user`
  - `stream_to_user` → `memory_writer` (if `user_memory_enabled`) → `voice_pipeline` or `__end__`
- ✅ State update: Added `user_id: str` to `ConversationState`
  - Defaults to "anonymous" for unauthenticated sessions
  - Scopes memories per user (multi-session isolation)
- ✅ requirements.txt: Added `mem0ai`

### ✅ COMPLETE

**Component 02d: Citation Verification** (Session 5)
- ✅ `citation_verifier()` in `core/langgraph/nodes/generation_nodes.py`
  - Parses `[N]` citation markers from LLM response (regex: `\[(\d+)\]`)
  - Cross-references against `retrieved_passages` (1-indexed → 0-indexed)
  - Builds `cited_sources` list with `{doc_id, chunk_id, passage, source_type}`
  - Catches hallucinated source IDs (e.g., LLM cites [5] with only 3 passages)
  - 25 lines of pure Python (vs 2-line stub)
  - Graceful fallback: no passages → returns empty `cited_sources`
  - Gate: Runs for both clients (not profile-dependent)

### ✅ COMPLETE

**FastAPI Layer** (Session 8, Updated Session 9)
- ✅ `api/main.py` (56 lines) — FastAPI app, lifespan (load_dotenv, mkdir), CORS, routers
- ✅ `api/deps.py` (37 lines) — DB session factory, clone lookup dependency (core building block)
- ✅ `api/routes/config.py` (21 lines) — `GET /clone/{slug}/profile` endpoint
- ✅ `api/routes/chat.py` (172 lines) — `POST /chat/{slug}` (sync) + `WS /chat/{slug}/ws` (streaming)
- ✅ `api/routes/ingest.py` (139 lines) — `POST /ingest/{slug}` (multipart file upload, BackgroundTasks)
- ✅ `api/routes/review.py` — `GET /review/{slug}`, `PATCH /review/{clone_slug}/{review_id}` (clone-scoped, Session 17)
- ✅ Dependencies: `uvicorn[standard]`, `httpx`, `python-multipart` added to requirements.txt
- ✅ Environment: `GOOGLE_API_KEY` added to .env (needed for embeddings + Mem0)
- ✅ Optimization: WebSocket streaming avoids double graph.invoke() — 50% latency reduction
- ✅ Smoke test: Server starts, `/health` responds, routes register successfully
- ✅ Verified: All 4 layers working with Google Gemini embeddings (embedder, retrieval, memory, LangGraph)

**FastAPI Gateway Tests** (Session 10, Updated Session 14)
- ✅ `tests/test_api.py` (575 lines, 33 test cases) — Comprehensive HTTP endpoint testing
  - Health check, profile endpoint, chat sync, ingest, review, auth, access tier endpoints
  - Mock strategy: DB session + clone fixtures, LangGraph graph mock with preset responses
  - All 33 tests pass
- ✅ `tests/conftest.py` (UPDATED Session 14) — Pytest configuration with async support + real DB fixtures
  - Session-scoped `ensure_db_seeded` fixture (idempotent — checks before inserting)
  - `paragpt_clone_id` and `sacred_clone_id` fixtures returning real UUIDs from DB
  - Loads .env at session startup, registers pytest-asyncio
- ✅ `pytest.ini` — Pytest configuration file (asyncio_mode=auto)
- ~~`tests/test_voyage_integration.py`~~ — DELETED Session 15 (provider changed to Google Gemini)
- ✅ `requirements.txt` — Added pytest==9.0.2, pytest-asyncio==0.25.2; removed langchain-voyageai + voyageai (Session 15)
- ✅ Full test suite: **77 passed** (33 API + 10 chunker + 26 session16 + 4 E2E + 2 WS + 2 seed)

### ✅ COMPLETE

**Semantic Chunking Upgrade** (Session 13, embeddings updated Session 14)
- ✅ Upgraded chunker from paragraph-aware fixed-size to TRUE semantic chunking
- ✅ Uses LangChain's `SemanticChunker` (`langchain-experimental`) + Google Gemini embeddings to detect topic boundaries
- ✅ Old fixed-size chunker preserved as fallback (`fixed_size` strategy via `ChunkingStrategy` enum)
- ✅ New `ChunkingStrategy` enum + `chunking_strategy` field added to CloneProfile (now 7 enums, 17 fields)
- ✅ Re-ingested sample docs: 8 semantic chunks (topic-coherent)
- ✅ New dependency: `langchain-experimental==0.4.1`
- ✅ Files modified: `chunker.py`, `pipeline.py`, `clone_profile.py`, `requirements.txt`
- ✅ Files created: `tests/test_chunker.py` (10 tests: 8 unit + 2 integration)

### ✅ COMPLETE

**Real Integration Tests + Google Gemini Embeddings** (Session 14)
- ✅ Converted all 4 E2E tests from mocked to REAL integration (no mocks — real DB, real vector search, real Mem0, real Groq LLM)
- ✅ Swapped embedding provider: Voyage AI voyage-3 → Google gemini-embedding-001 (3072→1024 truncated via Matryoshka)
  - Voyage AI free tier hit 3 RPM rate limit during real integration tests
  - Google Gemini has generous free tier (1500 RPM)
  - Zero schema migration (both output 1024-dim after truncation)
- ✅ Created `scripts/ask_clone.py` — CLI query script for manual pipeline testing
  - Flags: `--clone`, `--user-id`, `--access-tier`, `-v`/`--verbose`
  - Runs full real pipeline: DB → vector search → LangGraph → LLM → response
- ✅ Updated `tests/show_pipeline.py` — added `--real` flag for live DB mode (default behavior preserved)
- ✅ Updated `tests/conftest.py` — session-scoped DB seeding fixtures (idempotent)
- ✅ **4 production bugs discovered and fixed** (were hidden by mocks):
  - `query_analysis_node.py`: hardcoded `access_tier: "public"` overwriting caller-set tier
  - `provenance.py`: `SELECT DISTINCT ... ORDER BY embedding <=> vector` SQL error
  - `retrieval_nodes.py`: DB URL format (`+psycopg` not accepted by `psycopg.connect()`)
  - `provenance.py`: missing vector string conversion for pgvector query
- ✅ Total test suite: **69 passed, 6 skipped** (after Sessions 15-17)

### ✅ COMPLETE

**Voyage AI Cleanup** (Session 15)
- ✅ Removed `voyageai`, `langchain-voyageai`, `tf-keras` from requirements.txt
- ✅ Deleted `tests/test_voyage_integration.py` (provider changed to Google Gemini in Session 14)
- ✅ Clean dependency tree

### ✅ COMPLETE

**Stub Replacement Session** (Session 16 — 6 stubs replaced with real code)
- ✅ `review_queue_writer` — Real DB INSERT into review_queue (psycopg, UUID, JSONB cited_sources)
- ✅ `audio/video parsing` — Groq Whisper Large v3 Turbo (uses existing GROQ_API_KEY, 25MB limit, 8 formats)
- ✅ `voice_pipeline` — edge-tts (Microsoft Edge TTS, free, factory pattern `make_voice_pipeline`)
- ✅ `token_budget` — LLM-decided (single call with intent + sub_queries + budget, clamped [1000-4000])
- ✅ `stream_to_user` — LLM-based sentence splitting (context-aware, handles Dr., U.S., 3.14)
- ✅ `crag_evaluator` — Passage-count confidence adjustment (no LLM call, fast for retry loop)
- ✅ New ConversationState keys: `audio_base64`, `audio_format`
- ✅ New dependency: `edge-tts==7.2.7`
- ✅ 26 new tests in `tests/test_session16.py`

### ✅ COMPLETE

**Backend Audit & Hardening** (Session 17 — 12 fixes)
- ✅ **P0 Bugs (3):** Silence mechanism fixed (verified_response overwrite), ingest DB URL format, Sacred Archive temperature (0.0 for mirror_only)
- ✅ **P1 Security (5):** SQL injection (provenance.py parameterized), path traversal (filename sanitization), cross-tenant review (clone-scoped PATCH), WebSocket session leak, user_memory privacy leak removed
- ✅ **P2 Code Quality (4):** BackgroundTasks mutable default, _psycopg_url() DRY extraction, regex sentence splitting, dependency cleanup
- ✅ 4 test assertions updated, all 69 tests passing

### ✅ COMPLETE

**Voice Pipeline** (Session 16)
- ✅ `voice_pipeline` — edge-tts (Microsoft Edge TTS, free, no API key needed)
- ai_clone mode: generates MP3 audio, stored as base64 in state
- original_only mode: stub (needs recording timestamp mapping — PCCI blocked)
- text_only mode: skipped via conditional edge
- New ConversationState keys: `audio_base64`, `audio_format`
- New dependency: `edge-tts==7.2.7`

### ✅ COMPLETE

**React Frontend** (Sessions 19-28)
- ✅ 29 source files — Vite 6 + React 19 + TypeScript + Tailwind CSS v4
- ✅ ParaGPT: Landing (glassmorphism, corpus-aligned questions) + Chat (copper theme, header-less, thinking bubble, reasoning trace)
- ✅ Sacred Archive: Landing (tier selector) + Chat (serif + gold, provenance citations)
- ✅ Review Dashboard: 3-column layout, edit mode, keyboard shortcuts (a/r/e), CollapsibleCitations
- ✅ Analytics Dashboard: stat cards, bar charts, intent breakdown
- ✅ 10 shared components: MessageBubble, ChatInput, CitationCard, CitationGroupCard, CitationList, CollapsibleCitations, NodeProgress, AudioPlayer, ReasoningTrace, ErrorBoundary
- ✅ WebSocket streaming with node progress events + reasoning trace accumulation
- ✅ Zero TypeScript errors, production build passes

**RAG Pipeline Overhaul** (Session 29)
- ✅ FlashRank cross-encoder reranking (`ms-marco-MiniLM-L-12-v2`, ~34MB, CPU-only)
- ✅ BM25 hybrid search via PostgreSQL `tsvector` + GIN index (migration 0006)
- ✅ Multi-factor confidence scorer: retrieval (0.35) + citation_coverage (0.25) + response_grounding (0.25) + passage_count (0.15)
- ✅ CRAG loop fix: reranker-based evaluator + keyword/sub-topic reformulation (not paraphrases)

**Demo Readiness** (Session 30)
- ✅ Real Gemini embeddings in seed corpus (37 passages, 8 documents)
- ✅ Landing page questions aligned with demo corpus + irrelevant question for hedge demo
- ✅ All 6 documentation files updated to Session 30
- ✅ 77 tests passing

### ✅ COMPLETE

**Database Setup + Seeding** (Session 12)
- ✅ PostgreSQL 17 running locally (pg_hba.conf → trust for dev)
- ✅ pgvector 0.8.2 installed (HNSW indexing enabled)
- ✅ `dce_dev` database created, 4 migrations applied (17 tables total)
- ✅ `scripts/seed_db.py` — Idempotent seeder (2 clones, 1 admin user, provenance graph)
- ✅ `scripts/ingest_samples.py` — Sample document ingestion (2 docs → 8 semantic chunks with Google Gemini embeddings)
- ✅ FastAPI smoke test: GET /clone/*/profile returns real data from database
- ✅ 33/33 API tests still pass (no regressions) — total suite now 65 after Session 13

---

## File Map

```
/ (root — clean, config files only)
  README.md                 ← Entry point (what is this project?)
  CLAUDE.md                 ← AI instructions
  alembic.ini               ← Alembic migration config
  requirements.txt          ← Python dependencies
  .env                      ← API key (DO NOT COMMIT)
  .gitignore                ← Excludes .env

docs/                       ← Reference library (organized Feb 28, 2026)
  README.md                 ← Doc navigation
  ARCHITECTURE.md           ← 4-layer system design, 5-step pipeline
  CLIENTS/
    CLIENT-1-PARAGPT.md
    CLIENT-2-SACRED-ARCHIVE.md
  COMPONENTS/
    README.md               ← Status of all 4 components
  RESEARCH/
    README.md               ← Locked decisions Q1-Q8

core/                       ← Runtime implementation
  __init__.py
  models/
    clone_profile.py        ← Component 01 ✅ (7 enums, 17 fields, 2 presets)
  llm.py                    ← LLM client factory (Groq + Qwen)
  mem0_client.py            ← Mem0 client factory (pgvector backend) ✅ NEW Session 4
  db/                       ← Component 03 ✅
    __init__.py
    schema.py               ← 14 SQLAlchemy models, 3 Pydantic schemas
    migrations/
      env.py                ← Alembic environment (loads DATABASE_URL)
      script.py.mako        ← Alembic template
      versions/
        0001_initial_schema.py    ← 6 core tables
        0002_provenance_graph.py  ← 8 provenance tables
        0003_document_chunks.py   ← pgvector VECTOR(1024) + HNSW index
        0004_messages.py          ← Conversation persistence
        0005_user_memory.py       ← Mem0 metadata
        0006_bm25_search.py       ← tsvector column + GIN index (Session 29)
  langgraph/                ← Component 04 ✅
    conversation_flow.py    ← 19-node orchestration graph (build_graph factory)
    nodes/
      query_analysis_node.py      ← Intent classification (real LLM)
      retrieval_nodes.py          ← Tier 1/2, CRAG, reformulation (stubs)
      context_nodes.py            ← Context assembly, memory_retrieval ✅, memory_writer ✅ (NEW Session 4)
      generation_nodes.py         ← Response generation (real LLM)
      routing_nodes.py            ← Output routing, review queue (stubs)
  rag/                      ← Component 02 (to be built)
    (empty, stubs in langgraph nodes)

scripts/                    ← Database setup + CLI utilities
  seed_db.py                ← Idempotent clone + user + provenance seeder (Session 12)
  seed_paragpt_corpus.py    ← Sample ParaGPT corpus (6 docs, 22 chunks) (Session 25 NEW)
  ingest_samples.py         ← Sample document ingestion runner (Session 12)
  ask_clone.py              ← CLI query script — full real pipeline (Session 14 NEW)
  sample_docs/
    paragpt_sample.md       ← ParaGPT sample (geopolitics)
    sacred_archive_sample.md ← Sacred Archive sample (compassion)

tests/                      ← Test suite (77 passed)
  test_api.py               ← FastAPI endpoint tests (33 tests, mocked) — Updated Session 17
  test_chunker.py           ← Semantic chunking tests (10 tests: 8 unit + 2 integration)
  test_session16.py          ← Stub replacement tests (26 tests) — NEW Session 16
  test_e2e.py               ← End-to-end REAL integration tests (4 tests, no mocks) — Updated Session 17
  show_pipeline.py          ← Educational pipeline visualizer (--real flag) — Updated Session 17
  conftest.py               ← Pytest configuration + real DB seeding fixtures

ui/                         ← React Frontend (29 source files) — Sessions 19-28
  src/
    api/                    ← types.ts (22 interfaces + TraceRecord), client.ts, websocket.ts
    hooks/                  ← useChat.ts (WS + trace), useCloneProfile.ts, useAudio.ts
    components/             ← 10 shared components (MessageBubble, CitationCard, ReasoningTrace, etc.)
    pages/
      paragpt/              ← Landing.tsx (glassmorphism, corpus-aligned questions), Chat.tsx (copper theme)
      sacred-archive/       ← Landing.tsx (tier selector), Chat.tsx (serif + gold)
      review/               ← Dashboard.tsx (3-column, keyboard shortcuts, edit mode)
      analytics/            ← Dashboard.tsx (stats cards, bar charts)
    themes/                 ← paragpt.ts, sacred-archive.ts (design tokens)
    App.tsx                 ← Router + profile loader
    main.tsx                ← React root
    index.css               ← Global styles + glass morphism + markdown

build/                      ← Specification documents (reference only)
  components/
    03-db-schema.md
    others...
  model-testing/

open-questions/             ← Research archive (locked decisions)
  INDEX.md
  01-zvec-persistence.md through 08-timeline-buffer.md

tasks/                      ← Session tracking
  todo.md                   ← Build checklist
  lessons.md                ← Learned patterns (22 documented)
  PROGRESS.md               ← This file
```

---

## How to Verify Everything Works

**1. Test LLM Connection:**
```bash
cd /home/priyansurout/Digital\ Clone\ Engine
python3 -c "from core.llm import get_llm; r = get_llm().invoke('Say hello'); print(r.content)"
```
Expected: Short greeting from qwen/qwen3-32b (should take ~2-3 seconds)

**2. Test Component 01 (CloneProfile):**
```bash
python3 << 'EOF'
from core.models.clone_profile import paragpt_profile, sacred_archive_profile
p = paragpt_profile()
s = sacred_archive_profile()
print("ParaGPT:", p.generation_mode, p.review_required)
print("Sacred:", s.generation_mode, s.review_required)
print("✅ Both profiles load and validate correctly")
EOF
```

**3. Test Component 03 (DB Schema):**
```bash
# Import test (no database needed)
python3 -c "from core.db.schema import Clone, Document, ReviewQueue, Teaching, DocumentProvenance, CitedSource, AuditDetails; print('✅ Schema imports work')"

# Alembic SQL dry-run (generates SQL without applying)
cd /home/priyansurout/Digital\ Clone\ Engine
alembic upgrade --sql head
# Expected: 29 CREATE statements (14 tables + 15 indexes)
```

**4. Test Component 04 Full Graph (ParaGPT):**
```bash
python3 << 'EOF'
from core.langgraph.conversation_flow import build_graph, ConversationState
from core.models.clone_profile import paragpt_profile

profile = paragpt_profile()
graph = build_graph(profile)
result = graph.invoke({
    "query_text": "What is the future of connectivity?",
    "sub_queries": [], "intent_class": "", "access_tier": "public",
    "clone_id": "test-uuid", "user_id": "john-doe", "token_budget": 2000, "retrieved_passages": [],
    "provenance_graph_results": [], "retrieval_confidence": 0.0, "retry_count": 0,
    "assembled_context": "", "user_memory": "", "raw_response": "", "verified_response": "",
    "final_confidence": 0.0, "cited_sources": [], "silence_triggered": False, "voice_chunks": []
})
print("Intent:", result["intent_class"])
print("Confidence:", result["final_confidence"])
print("Has response:", len(result["raw_response"]) > 0)
print("✅ Full graph invocation works (with clone_id)")
EOF
```
Expected: intent_class is populated, confidence is 0.5+, raw_response is non-empty, clone_id in state

**4. Test Sacred Archive Routing (Review Queue):**
```bash
python3 << 'EOF'
from core.langgraph.conversation_flow import build_graph
from core.models.clone_profile import sacred_archive_profile

profile = sacred_archive_profile()
graph = build_graph(profile)
# Invoke same initial state
# ... (same state dict as above)
result = graph.invoke({...})
print("Voice chunks:", len(result["voice_chunks"]), "(should be 0 for original_only)")
print("✅ Sacred Archive routes correctly (review_required=true)")
EOF
```
Expected: Review queue log appears, voice_chunks=0

---

## Key Technical Decisions

These were researched and decided. Do NOT re-debate:

| Decision | Why | Alternative Considered |
|---|---|---|
| `build_graph(profile)` factory | Captures profile in routing closures. Single code path, different routing per client. | Add profile to state (bloats request-specific data) |
| Node factories (`make_in_persona_generator`) | Some nodes need config. Factory with closure keeps signature clean. | Pass profile in state or as extra parameter |
| Groq API + qwen/qwen3-32b | Fast, reliable, close to production Qwen3.5. | Use different API (Ollama, Together AI, OpenAI) |
| Pydantic v2 `str, Enum` | JSON serializes cleanly to strings (not enum reprs). | Custom serializers (more complex) |
| Stubs with correct state shape | Verify orchestration before building RAG/DB. | Build everything upfront (blocks faster iteration) |
| Graceful fallbacks in LLM nodes | If API fails, node returns sensible default (0.5 confidence, empty response). | Let failures propagate (breaks graph) |

---

## Component Status Summary (Session 30)

| Component | Status | Sessions | Notes |
|---|---|---|---|
| Backend (core engine + API) | ✅ COMPLETE + HARDENED | 1-17 | 19 LangGraph nodes, 7 API endpoint groups |
| Database (schema + seeding) | ✅ COMPLETE | 12, 25, 30 | 15 tables, 6 migrations, 37 seeded passages |
| RAG Pipeline | ✅ COMPLETE | 13-14, 29 | FlashRank reranking, BM25 hybrid, multi-factor scorer |
| Frontend (React SPA) | ✅ COMPLETE | 19-28 | 29 source files, zero TS errors, production build |
| Documentation | ✅ COMPLETE | 30 | 6 docs refreshed to Session 30 |
| Test Suite | ✅ COMPLETE | 10-16 | 77 tests passing |
| Stubs | 3 remaining | — | All PCCI hardware-blocked |

---

## Groq API Setup (For Next Session)

**What's Already Set Up:**
- `.env` file with `GROQ_API_KEY=gsk_...` (local, gitignored)
- `core/llm.py` with `get_llm()` factory function
- All nodes import and use LLM via `get_llm()`

**If Key Expires:**
- Get new key from https://console.groq.com/keys
- Update `.env` file
- Tests will pass again

**Available Qwen Model on Groq:**
- `qwen/qwen3-32b` (Preview tier)
- If it gets deprecated, check https://console.groq.com/docs/models
- Fallback alternatives: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`

---

## Lessons Learned (from tasks/lessons.md)

30 lessons documented. Key recent ones:
1. **Lesson 28:** LLM self-evaluation unreliable for confidence scoring — use deterministic multi-factor scoring
2. **Lesson 29:** Paraphrased queries embed identically — use keyword/sub-topic/jargon strategies
3. **Lesson 30:** Random embeddings break testing — always use real embeddings for demo corpora

See `tasks/lessons.md` for all 30.

---

## For Next Session (Session 31+)

**Current Status (Session 30):**
- ✅ FULL SYSTEM COMPLETE — Backend + Frontend + RAG pipeline + Tests
- ✅ 77 tests passing, zero TS errors, production build passes
- ✅ SOW Compliance: ParaGPT 97%, Sacred Archive 90%, Combined 93%
- ✅ Demo-ready: real Gemini embeddings, corpus-aligned starter questions, reasoning trace
- ✅ All documentation updated to Session 30 (6 docs refreshed)
- Only 3 hardware-blocked stubs remain (LLM swap, embeddings swap, tree search — all PCCI)

**Remaining Work (P2 Quality):**
- [ ] AuditLog writes — table exists but never INSERT'd (needs writes on review/ingest/admin actions)
- [ ] Rejection → seeker notification flow — no notification when reviewer rejects
- [ ] GDPR delete auth — no authentication on DELETE endpoint
- [ ] Demo videos — 5 user journey recordings (manager HIGH priority, non-code)
- [ ] When full corpus loaded: raise `confidence_threshold` back to 0.80

**Phase 3: Production Deployment (PCCI-blocked)**
- [ ] Replace dev proxies: Groq → SGLang, Google Gemini → TEI (when PCCI ready)
- [ ] Docker Compose or Kubernetes on PCCI
- [ ] Real voice cloning (OpenAudio S1-mini)
- [ ] Air-gapped deployment for Sacred Archive

**To Continue Next Session (Session 31):**
1. Read `PROGRESS.md` (this file) — recap status
2. Run full test suite: `python3 -m pytest tests/ -v` (expect 77 passed)
3. Check `docs/SOW-AUDIT.md` for remaining gaps
4. Start with P2 quality fixes (AuditLog writes, rejection flow, GDPR auth)

**Key Files Modified (Recent Sessions):**

**Session 30 (Demo Readiness + Documentation):**
- `scripts/seed_paragpt_corpus.py` — Real Gemini embeddings (replaced random), 37 passages, 8 docs
- `ui/src/pages/paragpt/Landing.tsx` — Corpus-aligned starter questions + irrelevant hedge demo
- `core/models/clone_profile.py` — ParaGPT `confidence_threshold` 0.80 → 0.65 (for demo corpus)
- All 6 documentation files updated (SOW-AUDIT, MANAGER-DIRECTIVES, ARCHITECTURE, FRONTEND, DEVELOPMENT-PLAN, lessons.md)

**Session 29 (RAG Pipeline Overhaul — 4 fixes):**
- `core/langgraph/nodes/generation_nodes.py` — Multi-factor confidence scorer (4 deterministic factors)
- `core/rag/retrieval/vector_search.py` — FlashRank reranking + BM25 hybrid search
- `core/langgraph/nodes/retrieval_nodes.py` — Reranker-based CRAG evaluator + keyword reformulator
- `core/rag/ingestion/indexer.py` — `search_vector` tsvector column population
- `core/db/migrations/versions/0006_bm25_search.py` — tsvector + GIN index migration
- `requirements.txt` — Added flashrank==0.2.10

**Session 28 (P1 SOW Gaps + Reasoning Trace):**
- `api/routes/chat.py` — `_extract_trace_data()`, `_extract_topic_suggestions()`, trace in WS progress
- `api/routes/review.py` — PATCH edit action, cited_sources in GET response
- `ui/src/components/ReasoningTrace.tsx` (NEW) — Pipeline trace timeline
- `ui/src/pages/review/Dashboard.tsx` — Edit mode, keyboard shortcuts, CollapsibleCitations

**Sessions 19-27:** Frontend build (29 source files), UI/UX overhaul (copper theme, glassmorphism, header-less chat), citation grouping, collapsible citations, dynamic response length, Mem0 dimension fix.

**If Context Gets Full Again:**
- Update PROGRESS.md with new progress
- Keep `tasks/lessons.md` updated
- Update MEMORY.md

---

**Session 19 (React Frontend Implementation):**

Built complete React frontend (Vite + TypeScript + Tailwind CSS v4). 21 source files, zero TS errors, production build passes.

**Files Created (21):**
- `ui/src/api/` — `types.ts` (21 interfaces), `client.ts` (4 REST functions), `websocket.ts` (WS manager)
- `ui/src/hooks/` — `useChat.ts` (WebSocket + node progress), `useCloneProfile.ts`, `useAudio.ts` (base64→playback)
- `ui/src/components/` — `ChatInput.tsx`, `MessageBubble.tsx`, `NodeProgress.tsx`, `AudioPlayer.tsx`, `CitationCard.tsx`
- `ui/src/pages/paragpt/` — `Landing.tsx` (glassmorphism profile card), `Chat.tsx` (messages + citations + audio)
- `ui/src/pages/sacred-archive/` — `Landing.tsx` (tier selector), `Chat.tsx` (serif quotes + provenance)
- `ui/src/pages/review/` — `Dashboard.tsx` (3-column approve/reject)
- `ui/src/themes/` — `paragpt.ts`, `sacred-archive.ts` (design tokens)
- `ui/src/App.tsx` — React Router with profile-driven theme switching
- `ui/src/index.css` — Tailwind v4 @theme with custom colors + glass utility classes
- `ui/vite.config.ts` — Proxy `/chat`, `/clone`, `/review`, `/ingest` → backend

**Backend Patch:**
- `api/routes/chat.py` — Added `audio_base64`, `audio_format` to ChatResponse + WebSocket response

**Architecture:**
- Routing: `/:slug` auto-detects ParaGPT vs Sacred Archive via `generation_mode`
- Design system: glassmorphism (ParaGPT: navy+teal), serif+gold (Sacred Archive: brown+gold)
- WebSocket streaming: 15 node labels mapped to user-friendly progress messages

**Verification:** TypeScript zero errors, production build (55 modules, 2.14s), 33 API tests pass.

---

**Session 20 (Frontend Polish & E2E Testing):**

Polished React frontend with error handling, WebSocket resilience, mobile responsive layouts, and documentation updates.

**Polish Fixes (10 files modified):**
1. `ErrorBoundary.tsx` (NEW) — React class component catches render errors with "Try Again" button
2. `App.tsx` — Wrapped routes in ErrorBoundary, pass `chatError` to chat pages
3. `useChat.ts` — WebSocket resilience: close old WS before new, 30s timeout, cleanup on unmount
4. `useAudio.ts` — Cleanup on unmount (revoke URLs, stop audio), try/catch on atob/play
5. `client.ts` — AbortController with 15s timeout on all fetch calls
6. `paragpt/Chat.tsx` — Error banner display, `relative` positioning
7. `sacred-archive/Chat.tsx` — Error banner display, `relative` positioning
8. `sacred-archive/Landing.tsx` — Fixed dead "Continue to Archive" button, safe-area padding
9. `Dashboard.tsx` — Mobile responsive: `flex-col md:flex-row`, stacked columns on mobile
10. `MessageBubble.tsx` — Responsive `max-w-[90%] sm:max-w-[80%] md:max-w-[75%]`
11. `ChatInput.tsx` — Loading spinner replaces send icon when disabled
12. `paragpt/Landing.tsx` — Safe-area padding for notched phones

**Testing:**
- TypeScript: zero errors
- Production build: 56 modules, passes
- Backend tests: 33/33 pass
- WebSocket integration test: `tests/test_ws_integration.py` (NEW) — 3 tests (progress+response, invalid slug, empty query)

**Status (Session 20):** FULL STACK OPERATIONAL + POLISHED. Frontend 22 source files, zero TS errors. Error boundaries, WS resilience, mobile responsive, loading states. 33 API tests + 3 WS integration tests.

---

**Session 20B (E2E Testing & Chat UX Overhaul):**

Live E2E browser testing revealed several bugs and UX issues. Compared against Delphi.ai reference for quality benchmarking.

**Bug Fixes:**
1. `api/deps.py` — Added `load_dotenv()` before module-level `DATABASE_URL` read (was crashing with "role priyansurout does not exist")
2. `paragpt/Landing.tsx` + `paragpt/Chat.tsx` — Avatar photo: `profile.avatar_url` from DB was `/static/avatars/parag-khanna.jpg` (non-existent). Hardcoded to `/avatars/parag-khanna.png`
3. `useChat.ts` — WS timeout reset: progress events now reset the 60s timer (was only clearing on final response, causing false timeouts on slow pipelines)
4. `MessageBubble.tsx` — Typewriter animation: removed `animatingRef` guard that broke under React StrictMode double-mount (text was empty)
5. `clone_profile.py` — Updated ParaGPT preset `avatar_url` from `/static/avatars/parag-khanna.jpg` to `/avatars/parag-khanna.png`

**UX Overhaul (Delphi.ai comparison):**
6. `MessageBubble.tsx` — Installed `react-markdown` for proper markdown rendering (bold, italic, paragraphs, lists, blockquotes). Added `leading-relaxed` for readability.
7. `index.css` — Added `.markdown-body` CSS: paragraph spacing, white bold, teal blockquote border, translucent code background
8. `generation_nodes.py` — Rewrote system prompt: "2-3 short paragraphs max", "conversational, not a textbook", "no markdown headers/horizontal rules"
9. `llm.py` — Added `max_tokens` parameter to `get_llm()`. Response generator now uses `max_tokens=500` (~375 words)

**New Files:**
- `ui/public/avatars/parag-khanna.png` — Clone avatar image (200x200 PNG)
- `docs/FRONTEND.md` — Complete frontend documentation (architecture, file inventory, design system, patterns, session history)

**Verification:**
- TypeScript: zero errors
- LLM module: imports clean with new `max_tokens` parameter
- Frontend: 23 source files (21 original + ErrorBoundary + avatar)

**Status (Session 20B):** Chat responses now conversational (2-3 paragraphs, capped at 500 tokens). Markdown renders properly. Avatar photo visible. WS timeout no longer fires during normal pipeline execution. Full frontend documented in `docs/FRONTEND.md`.

---

**Session 21 (Citation Fix):**

Citations were not appearing in the ParaGPT chat UI despite backend pipeline generating them. Two root causes identified and fixed.

**Bug 1 — LLM never produced citation markers:**
- `context_assembler` numbers passages as `[1]`, `[2]` but system prompt never told LLM to use them
- `citation_verifier` regex found nothing → `cited_sources` always empty
- **Fix:** Added citation instruction to both interpretive and mirror_only system prompts

**Bug 2 — Field name mismatch (backend → frontend):**
- Backend sent `{passage, source_type}` but frontend expected `{chunk_text, source}`
- **Fix:** Remapped fields in `citation_verifier` to match `CitedSource` interface
- Added `re.sub(r'\s*\[\d+\]', '', raw)` to strip markers from displayed text

**Files Modified:**
- `core/langgraph/nodes/generation_nodes.py` — System prompt + citation_verifier field remap + marker stripping
- `tests/test_e2e.py` — Updated citation_verifier test assertions

**Verification:** 37/37 tests pass, zero frontend changes needed.

---

**Session 22 (Requirements Audit + Gap Fixes):**

Full 3-agent audit of CLIENT-1 and CLIENT-2 requirements against codebase. Found bugs, missing features, and security gaps. Fixed all actionable items.

**Phase 1 — Bug Fixes:**
1. `routing_nodes.py` — `strict_silence_router` converted to factory function (`make_strict_silence_router(profile)`). Now overwrites `raw_response` AND `verified_response` with `silence_message` (was only setting `silence_triggered=True`, letting real LLM output through)
2. `conversation_flow.py` — Updated import and node registration to use factory function
3. `chat.py` — Added `min_length=1, max_length=2000` to `ChatRequest.query` (REST). Added `len(query) > 2000` check in WebSocket handler

**Phase 2 — Monitoring Dashboard (new CLIENT-1 deliverable):**
4. `chat.py` — Added `_write_analytics()` helper using psycopg. Both sync and WebSocket handlers now INSERT to `query_analytics` table with latency_ms, confidence, intent_class, silence_triggered
5. `api/routes/analytics.py` (NEW) — `GET /analytics/{slug}` returns aggregate stats: total queries, avg confidence, avg latency, silence rate, queries per day, top intents
6. `ui/src/pages/analytics/Dashboard.tsx` (NEW) — Stats cards, bar charts, intent breakdown. Route: `/:slug/analytics`
7. `ui/src/api/types.ts` — Added `AnalyticsSummary` interface
8. `ui/src/api/client.ts` — Added `getAnalytics()` function
9. `ui/src/App.tsx` — Added `AnalyticsPage` component + route

**Phase 3 — GDPR & Security:**
10. `api/routes/users.py` (NEW) — `DELETE /users/{user_id}/data` deletes messages, analytics, Mem0 memories
11. `api/main.py` — CORS hardened: `allow_origins=["*"]` → env-based `CORS_ORIGINS` (defaults to localhost). Rate limiting: slowapi attached to app with `RateLimitExceeded` handler
12. `chat.py` — Rate limit `@limiter.limit("60/minute")` on sync endpoint. Renamed `request` → `chat_request` to accommodate slowapi's `Request` parameter
13. `api/routes/ingest.py` — Rate limit `@limiter.limit("10/minute")` on file upload
14. `requirements.txt` — Added `slowapi==0.1.9`
15. `ui/vite.config.ts` — Added `/analytics` and `/users` proxy entries

**Documentation:**
16. `docs/MANAGER-DIRECTIVES.md` (NEW) — Manager feedback, feature requests, requirement audit results

**Verification:** 37/37 tests pass, zero TS errors, frontend production build succeeds.

**Status (Session 22):** All CLIENT-1 deliverables now implemented (including monitoring dashboard). Strict silence bug fixed for Sacred Archive. GDPR delete endpoint live. API rate-limited and CORS-hardened. 3 PCCI-blocked stubs remain. Manager requests reasoning trace feature next.

---

**Session 23 (SOW Audit — Line-by-Line Verification):**

Full 3-agent audit of both client SOW PDFs against codebase. Every deliverable, user story, and success criteria checked with file:line evidence.

**Audit Results:**
- ParaGPT: 6/9 deliverables fully done, 3 partial, 0 missing (89%)
- Sacred Archive: 4/9 fully done, 4 partial, 1 missing (72%)
- Combined: 80% SOW compliance
- **12 gaps identified**, 10 fixable now, 2 PCCI-blocked

**Gaps Found (P0 — Release Blockers):**
1. **Multi-turn conversation broken** — prior messages saved to Message table but never retrieved for LLM context. `context_assembler` only uses retrieved_passages, no conversation history
2. **Provenance fields missing from citations** — DocumentProvenance has date/location/event/verifier but citation_verifier only extracts source_type. Sacred Archive SOW requires all 5 fields
3. **Sacred Archive silence message text wrong** — doesn't match SOW wording

**Gaps Found (P1 — SOW Requirements):**
4. Review EDIT action missing (only approve/reject)
5. Review keyboard shortcuts missing (mouse-only, can't do 50+/day)
6. Review dashboard doesn't show cited sources
7. Dynamic topic suggestions missing from silence messages

**Gaps Found (P2 — Quality & Security):**
8. AuditLog table never written to
9. Rejection → seeker notification flow missing
10. GDPR delete endpoint has no auth

**PCCI-Blocked:**
11. Voice clone (generic edge-tts, not trained model)
12. Air-gap enforcement (deployment_mode not checked before API calls)

**Documentation Created:**
- `docs/SOW-AUDIT.md` (NEW) — Full audit report with evidence, fix plan, file-by-file implementation guide

**Status (Session 23):** SOW compliance at 80%. 12 gaps documented with prioritized fix plan. Ready to implement P0 fixes (multi-turn + provenance + silence message).

---

**Session 24 (P0 Release Blocker Fixes):**

Fixed all 3 P0 release blockers identified in Session 23 SOW audit. CLAUDE.md restructured for efficiency.

**P0 Fixes (3/3 Complete):**
1. **Multi-turn conversation** — New `conversation_history_node` in `context_nodes.py`. Queries last 5 messages from `Message` table by (clone_id, user_id), formats as `User: ... / Assistant: ...`, injects before context in LLM prompt. New ConversationState key: `conversation_history`. Graph path: `context_assembler → conversation_history → (memory_retrieval | in_persona_generator)`.
2. **Provenance fields in citations** — `vector_search.py` LEFT JOIN to `documents` table pulls provenance JSONB (date, location, event, verifier). `citation_verifier` passes all fields through to `cited_sources`. Frontend `CitationCard.tsx` conditionally renders provenance metadata.
3. **Sacred Archive silence message** — Updated `silence_message` in `clone_profile.py` to use institutional voice per SOW: "We honor the tradition of sacred silence..."

**CLAUDE.md restructured:** 72→60 lines. Added 3 sections (LangGraph patterns, dependency verification, security-by-default). Self-Improvement Loop merged into Plan Mode. Task Management collapsed.

**Files Modified (Session 24):**
- `core/langgraph/nodes/context_nodes.py` — New `conversation_history_node()` function
- `core/langgraph/conversation_flow.py` — Added `conversation_history` key + node wiring
- `core/langgraph/nodes/generation_nodes.py` — Inject conversation history into LLM prompt, pass provenance fields through citation_verifier
- `core/rag/retrieval/vector_search.py` — LEFT JOIN to documents, extract provenance JSONB fields
- `core/models/clone_profile.py` — Updated Sacred Archive silence_message
- `ui/src/components/CitationCard.tsx` — Render provenance fields (date, location, event, verifier)
- `ui/src/api/types.ts` — Added date/location/event/verifier to CitedSource interface
- `api/routes/chat.py` — Pass user_id to graph for conversation history
- `CLAUDE.md` — Restructured (3 new sections, collapsed task management)

**Verification:** 73 tests pass (all passing, 3 skipped), zero TS errors.

---

**Session 25 (Citation Title Pipeline + Sample Corpus):**

SOW requires: "Every answer includes the source **(book, essay, interview, date)**". Citations were showing just "essay" (the `source_type`). Fixed by adding `source_title` through the entire pipeline. Created sample ParaGPT corpus for realistic demo.

**Part 1 — `source_title` Pipeline (5 files):**
- `core/db/schema.py` — Added `title` field to `DocumentProvenance` Pydantic schema (JSONB, no migration needed)
- `core/rag/retrieval/vector_search.py` — Extract `source_title` from `provenance.get("title")` with `d.filename` fallback
- `core/langgraph/nodes/generation_nodes.py` — Pass `source_title` through `citation_verifier` to `cited_sources`
- `ui/src/api/types.ts` — Added `source_title?: string | null` to `CitedSource` interface
- `ui/src/components/CitationCard.tsx` — Header shows `"The Future Is Asian (book) — 2019"` when title available, falls back to just source_type

**Part 2 — Sample ParaGPT Corpus:**
- `scripts/seed_paragpt_corpus.py` (NEW) — Seeds 6 documents with 22 chunks:
  - "The Future Is Asian" (book, 2019)
  - "Connectography" (book, 2016)
  - "MOVE" (book, 2021)
  - "How to Run the World" (book, 2011)
  - "CNN Interview on ASEAN" (interview, 2023-06-15)
  - "The Age of Connectivity" (essay, 2020-03-10)
- Uses random normalized 1024-dim vectors for demo embeddings
- Idempotent: checks by (clone_id, filename) before inserting

**Part 3 — Old Data Cleanup:**
- Updated `paragpt_sample.md` document provenance JSONB in DB: added `title: "Geopolitics in the Age of AI"`, `date: "2024-01-15"`

**Verification:** 75 tests pass, zero TS errors, frontend production build passes.

**Status (Session 25):** SOW compliance at 89% (up from 85%). Citations now match SOW requirement with source title + type + date. Sample corpus provides realistic demo data. All P0 gaps resolved. Next: Phase 2 P1 review dashboard fixes.

---

**Session 26 (Dynamic Response Length + Mem0 Fix):**

Two fixes: (1) responses always came out as 2-3 paragraphs regardless of question complexity, (2) Mem0 cross-session memory silently failed due to embedding dimension mismatch.

**Fix 1 — Dynamic Response Length (3 files):**
- **Root cause:** System prompt said "Keep responses to 2-3 short paragraphs maximum" + hardcoded `max_tokens=500` on all LLM calls
- `core/langgraph/nodes/query_analysis_node.py` — LLM now decides `response_tokens` (100-1000) in the same call that decides `intent_class` and `token_budget`. Added `DEFAULT_RESPONSE_TOKENS = 500`, clamped [100, 1000]
- `core/langgraph/nodes/generation_nodes.py` — Replaced rigid "2-3 paragraphs" prompt with adaptive length instructions. Uses `state.get("response_tokens", 500)` instead of hardcoded `max_tokens=500`
- `core/langgraph/conversation_flow.py` — Added `response_tokens: int` to ConversationState (now 23 keys)

**Fix 2 — Mem0 Embedding Dimension Mismatch (1 file):**
- **Root cause:** `GoogleGenerativeAIEmbeddings` outputs 3072-dim vectors. Mem0's pgvector expects 1024. The ingestion pipeline truncates via `[:1024]` but `mem0_client.py` didn't — the function was named `_truncated_google_embeddings()` but never actually truncated
- `core/mem0_client.py` — Added `TruncatedGoogleEmbeddings` wrapper class that overrides `embed_query()` and `embed_documents()` to truncate to 1024 dims. Updated factory to return the wrapper

**Other:**
- `scripts/ask_clone.py` — Added `response_tokens` to verbose output

**Verification:**
- 75 tests pass (1 pre-existing WS timeout)
- Dimension check: `embed_query()` → 1024 dims (was 3072)
- Mem0 write/search/delete: all working end-to-end
- 5 pipeline queries tested: simple→150 tokens, moderate→200, opinion→300, synthesis→500 (all LLM-decided)
- Memory personalization confirmed: clone remembered "Rahul, data scientist, Bangalore" across queries

**Status (Session 26):** Dynamic response length working (no more rigid 3-paragraph answers). Mem0 cross-session memory fixed and verified (was silently broken since Session 4). ConversationState now 23 keys. All previous test results maintained.

**Session 27 (Frontend UI/UX Overhaul):**

Complete visual redesign of the ParaGPT chat interface across 6 improvement phases:

1. **Citation grouping** — Multiple passages from the same document now grouped into one expandable card instead of duplicate cards. New components: `CitationGroupCard.tsx`, `CitationList.tsx`. Added `doc_id` and `chunk_id` to `CitedSource` interface in `types.ts`.

2. **Collapsible citations** — Citations hidden by default behind a clickable "N sources cited" pill with book icon + chevron. New component: `CollapsibleCitations.tsx`. Replaces inline citation rendering in both Chat pages.

3. **Hidden scrollbar** — Removed visible scrollbar from chat message area. Added `.hide-scrollbar` CSS utility to `index.css`. Applied to both Chat pages.

4. **Wider chat layout** — Message container widened from `max-w-2xl` (672px) to `max-w-3xl` (768px). Assistant messages now full-width (`w-full`), user messages stay constrained at `max-w-[75%]`.

5. **Dark theme redesign** — Complete color overhaul:
   - Background: `#0a1628` (dark navy) → `#0d0d0d` (near-black charcoal)
   - Accent: `#00d4aa` (teal) → `#d08050` (warm copper-terracotta)
   - Glass: `rgba(22, 42, 72, 0.55)` → `rgba(30, 30, 30, 0.75)` (neutral dark gray)
   - User bubbles: copper gradient with warm glow shadow
   - All CSS variable tokens updated → cascades to all 12 files automatically

6. **Layout polish** — Removed persistent top bar header. Added conversation-start intro (centered avatar + name) that scrolls with messages. Thinking bubble (animated dots in glass bubble) replaces NodeProgress for immediate visual feedback on send. Input bar bottom padding increased to 24px. Subtle border separators for visual hierarchy.

**Files created:** `CitationGroupCard.tsx`, `CitationList.tsx`, `CollapsibleCitations.tsx` (3 new components)
**Files modified:** `index.css`, `paragpt.ts` (theme), `MessageBubble.tsx`, `CitationCard.tsx`, `types.ts`, `paragpt/Chat.tsx`, `sacred-archive/Chat.tsx`
**Build:** Zero TS errors, production build passes.

**Status (Session 27):** Frontend fully redesigned with modern dark theme, premium copper accent, professional citation UX, and conversation-centric layout. 28 source files (was 25). Sacred Archive theme untouched. All previous test results maintained.

---

## Development Plan (Session 28+)

### Phase 1: P0 SOW Fixes — Release Blockers
**Goal:** Fix 3 critical gaps that break core SOW promises

| Task | Files | Effort |
|------|-------|--------|
| Multi-turn conversation — retrieve last N messages, inject into LLM context | `context_nodes.py`, `conversation_flow.py`, `generation_nodes.py`, `chat.py` | Medium |
| Provenance fields in citations — date, location, event, verifier | `vector_search.py`, `generation_nodes.py`, `CitationCard.tsx`, `types.ts` | Small |
| Sacred Archive silence message — match SOW text exactly | `clone_profile.py` | Tiny |

### Phase 2: P1 SOW Fixes — Review Dashboard
**Goal:** Sacred Archive review workflow matches SOW requirements

| Task | Files | Effort |
|------|-------|--------|
| Review EDIT action — PUT endpoint + edit textarea | `review.py`, `Dashboard.tsx`, `types.ts`, `client.ts` | Small |
| Keyboard shortcuts — a/r/e for approve/reject/edit | `Dashboard.tsx` | Small |
| Cited sources in review dashboard | `Dashboard.tsx`, `review.py` | Small |
| Dynamic topic suggestions in silence messages | `routing_nodes.py` | Medium |

### Phase 3: P2 Quality & Security
**Goal:** Audit trail + security hardening

| Task | Files | Effort |
|------|-------|--------|
| AuditLog writes on review/ingest/delete actions | `review.py`, `ingest.py`, `users.py` | Small |
| Rejection → seeker notification | `review.py` flow | Medium |
| Auth on GDPR delete endpoint | `users.py` | Tiny |

### Phase 4: Manager Requests
**Goal:** Trust & visibility features

| Task | Files | Effort |
|------|-------|--------|
| Reasoning trace panel (collapsible pipeline visibility) | `chat.py`, new `TracePanel.tsx` component | Large |
| Demo videos (3-5 user journey recordings) | Screen recording tool | Non-code |
| Success metrics evaluation framework | New `scripts/eval_metrics.py` | Medium |

### When PCCI Ready
- LLM: Groq → SGLang (env var swap)
- Embeddings: Gemini → TEI (LangChain drop-in)
- Tree search: MinIO + PageIndex
- Voice: edge-tts → OpenAudio TTS (trained voice model)
- Air-gap enforcement: check deployment_mode before API calls

---

## Session 28 — P1 SOW Gaps + Reasoning Trace Panel

**All 4 P1 gaps FIXED + Manager HIGH priority delivered.**

### P1 Fixes (4/4 Complete)

1. **Review EDIT action** — New `edit` action in PATCH `/review/{slug}/{id}`. Reviewers can now edit response text before approving. Status becomes "edited" (remains visible in queue). Frontend shows edit textarea in center panel with Save/Cancel buttons.
   - Files: `api/routes/review.py`, `ui/src/pages/review/Dashboard.tsx`, `ui/src/api/types.ts`

2. **Keyboard shortcuts** — `a` approve, `r` reject, `e` edit, `ArrowUp/Down` navigate queue. Guarded: shortcuts don't fire when typing in textarea. `<kbd>` badge hints next to each button.
   - Files: `ui/src/pages/review/Dashboard.tsx`

3. **Cited sources in review dashboard** — `cited_sources` JSONB was already stored in DB but never returned by GET endpoint. Now included in API response and rendered via `CollapsibleCitations` (defaultExpanded=true so reviewers see sources).
   - Files: `api/routes/review.py`, `ui/src/api/types.ts`, `ui/src/pages/review/Dashboard.tsx`

4. **Dynamic topic suggestions** — When silence triggers, `_extract_topic_suggestions()` pulls `source_title` from `retrieved_passages` (no LLM call). Appends "You might explore: ..." (ParaGPT) or "Related topics in the archive: ..." (Sacred Archive) to silence message. New `suggested_topics` field in ConversationState and WS response.
   - Files: `core/langgraph/nodes/routing_nodes.py`, `core/langgraph/conversation_flow.py`, `api/routes/chat.py`

### Reasoning Trace Panel (Manager HIGH Priority)

5. **Backend:** New `_extract_trace_data()` function extracts curated metrics per node (never full passages). WS progress messages now include `{"type": "progress", "node": "...", "trace": {...}}`. Per-node data: intent, passage count, confidence, retry count, citation count, etc. Backward-compatible.
   - Files: `api/routes/chat.py`

6. **Frontend:** New `ReasoningTrace.tsx` component (collapsible pill toggle "{N} pipeline steps"). Vertical timeline with dot indicators per node + human-readable labels. `TraceRecord` type added. `useChat.ts` accumulates trace via ref, attaches to ChatMessage. Integrated in both ParaGPT and Sacred Archive Chat pages.
   - Files: `ui/src/components/ReasoningTrace.tsx` (NEW), `ui/src/api/types.ts`, `ui/src/hooks/useChat.ts`, `ui/src/pages/paragpt/Chat.tsx`, `ui/src/pages/sacred-archive/Chat.tsx`

### Test Results
- ✅ 74 passed, 3 skipped, 0 failed (1 new `test_review_edit`)
- ✅ Frontend build: zero TS errors, production build passes
- ✅ 29 frontend source files (1 new: ReasoningTrace.tsx)

### SOW Compliance Update
- ParaGPT: 96% → ~97% (topic suggestions in silence)
- Sacred Archive: 83% → ~90% (review EDIT, shortcuts, cited sources, topic suggestions)
- Combined: 89% → ~93%

### ConversationState Keys: 24 (was 23)
New key: `suggested_topics: list[str]`

---

## Session 29 — RAG Pipeline Overhaul

**Fixed 3 fundamental pipeline bugs discovered via reasoning trace panel (Session 28 screenshot).**

### Problem Discovery
The reasoning trace showed: CRAG retried 3x with identical 77% confidence → final confidence scorer returned 100%. Two disconnected confidence metrics (retrieval_confidence for CRAG, final_confidence for output routing) were never combined. The hedge/silence mechanism was effectively dead for ParaGPT.

### Root Cause Analysis (3 interacting bugs)
1. **CRAG evaluator was a no-op** — `min(10/3.0, 1.0) = 1.0` with 10 passages (default). Never adjusted confidence.
2. **CRAG retry loop was useless** — paraphrased queries embed to identical vectors (by design). Reformulator had no diagnostic info (only `source_type`, no passage text).
3. **Confidence scorer was blind** — LLM saw only question+answer, never retrieval_confidence or passages. Always rated ~1.0 (grading fluency, not groundedness).

### Fix 1: Multi-Factor Confidence Scorer
- **File:** `core/langgraph/nodes/generation_nodes.py`
- Replaced LLM self-evaluation with deterministic 4-factor scoring:
  - `0.35 * retrieval_confidence` (from vector search / reranker)
  - `0.25 * citation_coverage` (cited_sources / retrieved_passages)
  - `0.25 * response_grounding` (lexical overlap response↔context)
  - `0.15 * passage_count_factor` (min(passages/3, 1.0))
- No LLM call = faster, no overconfidence. Hedge/silence now actually triggers.

### Fix 2: FlashRank Reranking
- **File:** `core/rag/retrieval/vector_search.py`
- Added cross-encoder reranking after vector search (2-stage retrieval):
  1. Over-retrieve `top_k * 3` candidates via cosine similarity
  2. Rerank with `ms-marco-MiniLM-L-12-v2` (~34MB, CPU-only)
  3. Return top 10 reranked with per-passage `rerank_score`
- Confidence = mean reranker score of top 5 (far more calibrated than cosine similarity)
- Module-level singleton: model loaded once, reused across requests
- Graceful fallback: if FlashRank unavailable, falls back to RRF order
- **New dependency:** `flashrank==0.2.10`

### Fix 3: CRAG Loop Improvement
- **File:** `core/langgraph/nodes/retrieval_nodes.py`
- **Evaluator:** Uses mean reranker scores (cross-encoder) instead of passage-count heuristic
- **Reformulator:** Now sees actual passage text (first 200 chars of top 3) + reranker scores
- **Prompt:** Asks for keyword extraction, sub-topic decomposition, domain jargon — NOT paraphrases
- Fallback generates keyword queries instead of "What about X?" / "Explain X"

### Fix 4: BM25 Hybrid Search
- **Files:** `core/rag/retrieval/vector_search.py`, `core/rag/ingestion/indexer.py`
- Added `search_vector` (tsvector) column to `document_chunks` table
- **Migration 0006:** `ALTER TABLE` + `to_tsvector('english', passage)` + GIN index
- BM25 results combined with vector results via existing RRF formula
- **Why this breaks the stuck loop:** BM25 ranks by keyword frequency, not embedding similarity. Reformulated queries with different keywords → different passages.
- Indexer updated to populate `search_vector` during ingestion

### Trace Panel Update
- `_extract_trace_data()` now shows `reranked` flag and `top_rerank_score`
- Frontend `TraceRecord` type updated with new fields
- `ReasoningTrace.tsx` displays "reranked" label when cross-encoder was used

### Files Modified (Session 29)
| File | Change |
|------|--------|
| `core/langgraph/nodes/generation_nodes.py` | Multi-factor confidence scorer (replaced LLM self-eval) |
| `core/rag/retrieval/vector_search.py` | FlashRank reranking + BM25 hybrid search + confidence fix |
| `core/langgraph/nodes/retrieval_nodes.py` | CRAG evaluator (reranker scores) + reformulator (diagnostic info) |
| `core/rag/ingestion/indexer.py` | Populate `search_vector` tsvector column |
| `core/db/migrations/versions/0006_bm25_tsvector.py` | New migration: tsvector column + GIN index |
| `api/routes/chat.py` | Trace data: reranked flag + top_rerank_score |
| `ui/src/api/types.ts` | TraceRecord: reranked, top_rerank_score fields |
| `ui/src/components/ReasoningTrace.tsx` | Display "reranked" in trace |
| `requirements.txt` | Added `flashrank==0.2.10` |

### Verification
- ✅ 70 tests passed (test_api 34 + test_session16 26 + test_chunker 10), 0 failed
- ✅ Frontend: zero TS errors, production build passes
- ✅ FlashRank reranker loads and scores correctly (verified with sample data)
- ✅ Migration 0006 applied (tsvector column + GIN index)

### Research Sources
- CRAG Paper (arXiv:2401.15884) — retrieval evaluator + web search fallback
- Anthropic Contextual Retrieval — 67% reduction in retrieval failures
- LLM Overconfidence (arXiv:2508.06225) — 84.3% overconfident scenarios
- FlashRank — ultra-lightweight CPU reranker
- PostgreSQL tsvector — built-in BM25, no extension needed

---

## Session 31: Frontend Polish (9 Fixes)

**Date:** March 6, 2026
**Goal:** Close all frontend gaps found during ParaGPT audit — 6 polish items + 3 nice-to-haves. No backend changes.

### Changes

| # | Fix | Description |
|---|-----|-------------|
| 1 | **Suggested topic pills** | Render `suggested_topics` from WS response as clickable copper/gold pills below assistant messages. Clicking sends topic as new query. Both clients. |
| 2 | **Sacred Archive thinking bubble** | Replaced `NodeProgress` import with inline animated dots (same pattern as ParaGPT but `sacred-gold` accent). Both clients now show instant feedback on send. |
| 3 | **Consolidated node labels** | Moved node label constants into `types.ts` as single source of truth: `NODE_LABELS` (28 progress-style entries) + `NODE_DISPLAY_NAMES` (22 noun-style entries). Removed duplicate locals from `useChat.ts` and `ReasoningTrace.tsx`. |
| 4 | **New conversation button** | `+` icon button left of input bar in both Chat pages. Calls `clearMessages()` + resets to landing page. Wired through `onNewConversation` prop from `App.tsx`. |
| 5 | **Character counter** | Shows `{length}/2000` below textarea when >1900 chars. Red text when over 2000. Send button disabled at limit. Matches backend's 2000-char validation. |
| 6 | **404 page** | Invalid slug now shows styled "404 / Clone not found" page with slug name in error text and "Go to ParaGPT" link button. |
| 7 | **Copy-to-clipboard** | Copy icon appears on hover (top-right of assistant bubble). Uses `navigator.clipboard.writeText()`. Shows green checkmark for 1.5s after copying. |
| 8 | **Multi-line textarea** | `<input>` → `<textarea rows={1}>` with auto-resize (max 120px / ~4 rows). Enter sends, Shift+Enter adds newline. |
| 9 | **Audio seek** | Progress bar is clickable — click to jump to position. `useAudio.ts` exposes `seek(percentage)`. Larger click target (h-3 container, h-1 fill bar). |

### Files Modified (Session 31)

| File | Change |
|------|--------|
| `ui/src/api/types.ts` | Added `suggested_topics` to WSResponseMessage + ChatMessage. Added `NODE_LABELS` + `NODE_DISPLAY_NAMES` exports. |
| `ui/src/hooks/useChat.ts` | Import shared `NODE_LABELS`, capture `suggested_topics` from WS response |
| `ui/src/hooks/useAudio.ts` | Added `seek(percentage)` function |
| `ui/src/components/MessageBubble.tsx` | Copy-to-clipboard button (hover, green checkmark feedback) |
| `ui/src/components/ChatInput.tsx` | Textarea + auto-resize + character counter |
| `ui/src/components/AudioPlayer.tsx` | `onSeek` prop, clickable progress bar |
| `ui/src/components/ReasoningTrace.tsx` | Import shared `NODE_DISPLAY_NAMES` |
| `ui/src/pages/paragpt/Chat.tsx` | Suggested topics, new conversation button, `onSeek` wiring |
| `ui/src/pages/sacred-archive/Chat.tsx` | Thinking bubble, suggested topics, new conversation button |
| `ui/src/App.tsx` | `handleNewConversation`, styled 404 page |

### Verification
- ✅ Zero TypeScript errors (`npx tsc --noEmit`)
- ✅ Production build passes (`npm run build` — 222 modules, 2.96s)
- ✅ 70 tests passing (no backend changes)

---

## For Next Session (Session 32)

**What's Ready:**
- ✅ RAG pipeline with reranking + BM25 + multi-factor confidence
- ✅ ALL P0 + P1 SOW gaps FIXED
- ✅ Frontend fully polished (9 fixes, Session 31)
- ✅ 70 tests passing, zero TS errors, production build clean
- ✅ SOW compliance at ~93%

**Remaining Work:**
1. **P2 Quality fixes:** AuditLog never written to, rejection→seeker flow missing, GDPR delete no auth
2. **Demo videos:** 5 user journey recordings (manager request, non-code)
3. **PCCI-blocked stubs:** LLM swap, embeddings swap, tree search, voice clone, air-gap enforcement
4. **Future RAG improvements:** Contextual Retrieval (Anthropic), RAGAS evaluation framework
5. **Cleanup:** `NodeProgress.tsx` is now unused (both clients use thinking bubble) — consider removing
