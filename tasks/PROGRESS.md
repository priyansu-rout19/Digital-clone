# Digital Clone Engine — Session Progress & Implementation Status

**Last Updated:** March 5, 2026 (Session 20 — Frontend Polish & E2E Testing)
**Current Focus:** React frontend built (Session 19) and polished (Session 20). Full-stack operational: FastAPI backend + React SPA. 56 modules, zero TS errors. 33 API tests passing. Frontend features: error boundaries, WebSocket resilience, mobile responsive, loading states.

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
- Files: `core/db/schema.py` (360 lines) + `core/db/migrations/` (4 migrations)
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
- ConversationState TypedDict with 19 keys (clone_id, user_id, etc.)
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
| crag_evaluator | ✅ Real | No | Passage-count confidence adjustment (no LLM, fast) — Session 16 |
| query_reformulator | ✅ Real | Yes | Rephrases low-confidence queries (retry_count fix: only increments here) |
| tier2_tree_search | Designed Stub | No | Returns passages unchanged, MinIO TODO (PCCI blocked) |
| provenance_graph_query | ✅ Real | No | SQL recursive CTE (parameterized queries — Session 17 security fix) |
| context_assembler | ✅ Real | No | Assembles passages into context string |
| memory_retrieval | ✅ Real | No | Searches Mem0 for user memories (ParaGPT only) — Session 4 |
| memory_writer | ✅ Real | No | Saves conversation turns to Mem0 (ParaGPT only) — Session 4 |
| in_persona_generator | ✅ Real | Yes | Persona-aware generation (temp=0.0 for mirror_only — Session 17 fix) |
| citation_verifier | ✅ Real | No | Parses [N] markers, cross-refs passages, populates cited_sources — Session 5 |
| confidence_scorer | ✅ Real | Yes | LLM evaluates response quality (0.0-1.0) |
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
- ✅ `core/rag/retrieval/vector_search.py` — Tier 1 pgvector + RRF (143 lines, cleaned)
  - `search(sub_queries, clone_id, access_tiers, db_url, top_k=10)` with RRF merging
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
- ✅ Full test suite: **69 passed, 6 skipped** (33 API + 10 chunker + 26 session16 + 4 E2E real)

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
  ingest_samples.py         ← Sample document ingestion runner (Session 12)
  ask_clone.py              ← CLI query script — full real pipeline (Session 14 NEW)
  sample_docs/
    paragpt_sample.md       ← ParaGPT sample (geopolitics)
    sacred_archive_sample.md ← Sacred Archive sample (compassion)

tests/                      ← Test suite (69 passed, 6 skipped)
  test_api.py               ← FastAPI endpoint tests (33 tests, mocked) — Updated Session 17
  test_chunker.py           ← Semantic chunking tests (10 tests: 8 unit + 2 integration)
  test_session16.py          ← Stub replacement tests (26 tests) — NEW Session 16
  test_e2e.py               ← End-to-end REAL integration tests (4 tests, no mocks) — Updated Session 17
  show_pipeline.py          ← Educational pipeline visualizer (--real flag) — Updated Session 17
  conftest.py               ← Pytest configuration + real DB seeding fixtures

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

## Next Tasks: React Frontend Implementation

**✅ DONE:** Sessions 12-17 — Full backend complete + hardened.
**✅ DONE:** Session 18 — MVP UI/UX designs created in Variant.

**Design Phase: ✅ COMPLETE**
- [x] ParaGPT Chat Page landing mockup in Variant
- [x] Sacred Archive Seeker Chat landing mockup in Variant
- [ ] Sacred Archive Review Dashboard mockup (deferred — will design when needed)
- [x] Design reference saved: `docs/UI-UX/DESIGN-REFERENCE.md`
- [x] Variant prompts saved: `.claude/plans/magical-meandering-nygaard.md`

**Next: React Frontend (MVP)**
- Chat Page (ParaGPT):
  - Landing: profile card, topic tags, starter questions, input bar
  - Conversation: collapsed header, message bubbles, citations, audio player
  - Real-time streaming via WebSocket
  - Voice playback (edge-tts MP3)
  - Cross-session memory ("Welcome back")

- Seeker Chat (Sacred Archive):
  - Landing: title, tier selector (Devotee/Friend/Follower), suggested questions
  - Conversation: direct quotes with provenance, original recording links
  - Sacred silence state
  - No cross-session memory

- Review Dashboard (Sacred Archive — after chat pages):
  - 3-column layout (queue | detail | actions)
  - Keyboard shortcuts (A/R/E)
  - Stats bar

**Then: Docker Compose + PCCI Deployment**

**Status:**
- ✅ Backend (core engine + API + tests): 100% COMPLETE + HARDENED (Session 17)
- ✅ Database (setup + seeding + sample data): COMPLETE
- ✅ All stubs resolved except 3 hardware-blocked (PCCI)
- ✅ 69 tests passing, 6 skipped
- ✅ UI/UX Designs: MVP mockups done (ParaGPT + Sacred Archive)
- ⏳ Frontend: React implementation next

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

22 lessons documented. Key ones:
1. **Lesson 10:** Factory pattern for profile-aware nodes (closures)
2. **Lesson 11:** Real LLM integration with graceful fallbacks
3. **Lesson 8:** Conditional routing drives unified codebase
4. **Lesson 6:** Pydantic enum serialization (str, Enum)

See `tasks/lessons.md` for all 22.

---

## For Next Session (Session 19+)

**What's Ready:**
- ✅ FULL BACKEND COMPLETE + HARDENED (Sessions 1-17)
- ✅ MVP UI/UX DESIGNS COMPLETE (Session 18) — saved in `docs/UI-UX/`
- ✅ 69 tests passing, 6 skipped
- Only 3 hardware-blocked stubs remain (LLM swap, embeddings swap, tree search — all PCCI)

**What's Next:**

**Phase 1: Design ✅ COMPLETE**
- [x] ParaGPT Chat Page mockup (landing state)
- [x] Sacred Archive Seeker Chat mockup (landing + tier selector)
- [x] Design reference: `docs/UI-UX/DESIGN-REFERENCE.md`

**Phase 2: React Frontend (NEXT)**
- [ ] Project setup: Vite + React + TypeScript + Tailwind CSS
- [ ] ParaGPT Chat Page (landing → conversation states)
- [ ] Sacred Archive Seeker Chat (landing → conversation states)
- [ ] WebSocket streaming integration
- [ ] Voice playback (audio player for edge-tts MP3)
- [ ] Sacred Archive Review Dashboard
- [ ] Docker Compose full-stack setup
- [ ] Smoke test: Chat page → API → LangGraph → response

**Phase 3: Production Deployment**
- [ ] Replace dev proxies: Groq → SGLang, Google Gemini → TEI (when PCCI ready)
- [ ] Docker Compose or Kubernetes on PCCI
- [ ] CORS lockdown, auth hardening

**To Continue Next Session (Session 19):**
1. Read `PROGRESS.md` (this file) — recap status
2. Check `docs/UI-UX/DESIGN-REFERENCE.md` — design specs for React
3. Run full test suite: `pytest tests/ -v` (expect 69 passed, 6 skipped)
4. Start FastAPI server: `python3 -m uvicorn api.main:app --port 8000`
5. Begin React project setup (Vite + TypeScript + Tailwind)
6. Implement ParaGPT landing page first, then conversation view

**Key Files Modified (Recent Sessions):**

**Session 17 (Backend Audit & Hardening — 12 fixes):**
- `core/langgraph/nodes/routing_nodes.py` — Fix 1 (silence mechanism), Fix 10 (DRY), Fix 11 (regex split)
- `core/langgraph/nodes/generation_nodes.py` — Fix 3 (profile-aware temperature)
- `core/rag/retrieval/provenance.py` — Fix 4 (SQL parameterization)
- `api/routes/ingest.py` — Fix 2 (DB URL), Fix 5 (path traversal), Fix 9 (BackgroundTasks)
- `api/routes/chat.py` — Fix 7 (WebSocket session leak), Fix 8 (user_memory privacy)
- `api/routes/review.py` — Fix 6 (clone-scoped PATCH route)
- `core/langgraph/nodes/retrieval_nodes.py` — Fix 10 (import shared psycopg_url)
- `core/db/__init__.py` — Fix 10 (shared psycopg_url utility)
- `requirements.txt` — Fix 12 (removed tf-keras, pinned versions)
- `core/langgraph/conversation_flow.py` — P3 comment fix
- `core/rag/ingestion/indexer.py` — P3 comment fix
- `tests/show_pipeline.py` — P3 added audio_base64/audio_format keys
- `tests/test_e2e.py` — P3 added GOOGLE_API_KEY to skipif
- `tests/test_api.py` — Updated 4 test assertions for route/response changes

**Session 16 (6 Stub Replacements):**
- `core/langgraph/nodes/routing_nodes.py` — review_queue_writer, voice_pipeline, stream_to_user (real)
- `core/langgraph/nodes/query_analysis_node.py` — token_budget (LLM-decided)
- `core/langgraph/nodes/retrieval_nodes.py` — crag_evaluator (confidence adjustment)
- `core/rag/ingestion/parser.py` — audio/video parsing (Groq Whisper)
- `api/routes/chat.py` — audio_base64/audio_format in initial state
- `core/langgraph/conversation_flow.py` — audio_base64/audio_format in ConversationState
- `requirements.txt` — Added edge-tts==7.2.7
- `tests/test_session16.py` (NEW) — 26 tests for stub replacements

**Session 15 (Voyage AI Cleanup):**
- `requirements.txt` — Removed voyageai, langchain-voyageai, tf-keras
- `docs/STUBS-AND-MOCKS.md` — Updated inventory
- Deleted `tests/test_voyage_integration.py`

**Sessions 8-14:** See previous PROGRESS.md versions for detailed file lists.

**If Context Gets Full Again:**
- Update PROGRESS.md with new progress
- Keep `tasks/lessons.md` updated
- Update `/home/priyansurout/.claude/projects/-home-priyansurout-Digital-Clone-Engine/memory/MEMORY.md`

---

**Session 18 (UI/UX Design Phase):**
- `docs/UI-UX/DESIGN-REFERENCE.md` (NEW) — Design system, color palettes, component specs
- `.claude/plans/magical-meandering-nygaard.md` — All Variant prompts (1, 1B, 1C, 2, 3)
- MVP mockups: ParaGPT landing + Sacred Archive landing created in Variant

**Status (Session 18):** FULL SYSTEM OPERATIONAL + HARDENED + DESIGNED. Backend 100% complete. MVP UI/UX designs done (ParaGPT + Sacred Archive landing pages). Design reference saved in `docs/UI-UX/`. 69 tests passing, 6 skipped. Ready for React frontend implementation.

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
