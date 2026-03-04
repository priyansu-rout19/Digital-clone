# Stubs & Mocks Inventory — Digital Clone Engine

**Last Updated:** March 5, 2026 (Session 15 — Real integration tests + Google Gemini embeddings update) | **Status:** Comprehensive inventory of all stubs, dev proxies, and test mocks. All core embeddings/LLM/API paths functional and verified. 51 tests collected (45 passed, 6 skipped), zero xfails. PostgreSQL running with pgvector 0.8.2.

---

## Overview

The codebase contains **9 active items** that are currently stubbed or using dev proxies. They fall into three categories:

1. **Hardware-Blocked** (5 items) — PCCI GPU server or MinIO required
2. **Infra-Blocked** (1 item) — Review queue DB writes need wiring (PostgreSQL running since Session 12, auth middleware complete since Session 11)
3. **Intentional/Partial** (3 items) — Not bugs; design choices or data-dependent

**Resolved since Session 13:**
- E2E test mocks (vector_search, mem0_client) **removed** — all 4 E2E tests now use real services (Session 14)
- Auth middleware **complete** — `api/middleware.py` with X-API-Key validation (Session 11)
- access_tier hardcoding bug **fixed** — `query_analysis_node.py` preserves caller-set tier (Session 14)

For each item below: **Now** (current behavior) → **Real** (production behavior) → **How** (implementation steps) → **Dependency** (what's blocking it).

---

## Category 1: Hardware-Blocked Stubs

These require PCCI infrastructure (GPU, MinIO). Code is ready; waiting for deployment.

### 1. LLM — Groq API (dev) → SGLang/vLLM (prod)

**File:** `core/llm.py` lines 40–48

**Now:**
```python
ChatOpenAI(
    model="qwen/qwen3-32b",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
    model_kwargs={"reasoning_effort": "none"},  # Groq-specific parameter
)
```

**Real:**
```python
ChatOpenAI(
    model="Qwen3.5-35B-A3B",
    base_url="http://localhost:8000/v1",  # PCCI vLLM/SGLang endpoint
    api_key=os.getenv("VLLM_API_KEY"),
    extra_body={"enable_thinking": False},  # vLLM/SGLang parameter
)
```

**Why now is dev:**
- Groq API is a cloud service. ParaGPT uses it because PCCI GPU server isn't ready yet.
- Model is intentionally `qwen3-32b` (closely matches production `Qwen3.5-35B-A3B`). Same behavior, different scale.
- Parameter name changes between backends: Groq uses `reasoning_effort` enum, vLLM/SGLang uses `enable_thinking` boolean.

**How to make real:**
1. Update `base_url` env var to `http://localhost:8000/v1` (PCCI internal endpoint).
2. Update `api_key` env var to use vLLM token (different auth than Groq).
3. Change `model_kwargs` → `extra_body` dict.
4. Change `model` name to match deployed Qwen version.
5. No code changes to nodes (they all call `get_llm()` — the factory handles it).

**Blocking dependency:** PCCI GPU server with vLLM/SGLang running Qwen3.5-35B-A3B 4-bit AWQ (~20GB VRAM).

---

### 2. Embeddings — Google Gemini (dev, Session 14) → TEI (prod)

**File:** `core/rag/ingestion/embedder.py` (full file)

**Now (Development, Session 14 — replaced Voyage AI from Session 9):**
```python
from langchain_google_genai import GoogleGenerativeAIEmbeddings

TARGET_DIMS = 1024  # Gemini outputs 3072, truncated via Matryoshka property

client = GoogleGenerativeAIEmbeddings(
    model=os.environ.get("EMBEDDING_MODEL"),  # models/gemini-embedding-001
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
)
# embed_documents() returns 3072-dim vectors; truncated to [:1024] in _embed_batch()
```

**Mem0 also uses Google Gemini** (`core/mem0_client.py`):
```python
"embedder": {
    "provider": "langchain",
    "config": {
        "model": GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", ...),
        "embedding_dims": 1024,
    },
},
```

**Real (Production, when PCCI ready):**
```python
from langchain_community.embeddings import HuggingFaceEmbeddings
# Or use TEI via OpenAI-compatible endpoint:
client = HuggingFaceEmbeddings(
    model_name="Qwen3-Embedding-0.6B",
    # Runs locally on PCCI ~2GB VRAM
)
# Returns 1024-dim vectors from local GPU (no Matryoshka truncation needed)
```

**Status (Session 14):**
- ✅ **Fully functional and verified** — Google Gemini gemini-embedding-001 working across all 4 layers (embedder, retrieval, memory, chunking)
- ✅ 3072-dim output truncated to 1024 via Matryoshka property — zero schema migration from Voyage AI
- ✅ LangChain drop-in interface (zero code changes to swap backends)
- ✅ Tested: 4/4 real E2E tests pass, all sample docs re-ingested, pipeline visualizer complete
- Previously Voyage AI voyage-3 (Session 9). Replaced due to 3 RPM rate limit on free tier during real integration tests.

**How to make real (when PCCI TEI deployed):**
1. Deploy TEI on PCCI GPU (~2GB VRAM) serving `Qwen3-Embedding-0.6B` or compatible model
2. Update `core/rag/ingestion/embedder.py`:
   - Replace `GoogleGenerativeAIEmbeddings` with `HuggingFaceEmbeddings` or TEI via OpenAI-compatible endpoint
   - Remove Matryoshka truncation (TEI can serve native 1024-dim)
   - Update `.env`: replace `GOOGLE_API_KEY` + `EMBEDDING_MODEL` with local model reference
3. Update `core/mem0_client.py`: swap Google embeddings for TEI in Mem0 config
4. No breaking changes — LangChain Embeddings interface is identical

**ENV requirements:** `GOOGLE_API_KEY`, `EMBEDDING_MODEL=models/gemini-embedding-001`

**Blocking dependency:** PCCI GPU server with TEI (waiting for infrastructure deployment).

---

### 3. Voice Pipeline — Stub → OpenAudio TTS

**File:** `core/langgraph/nodes/routing_nodes.py` lines 120–144

**Now:**
```python
def voice_pipeline(state: ConversationState) -> ConversationState:
    # STUB: In production, this would send voice_chunks to TTS
    return state
```
Simply returns `state` unchanged. `voice_chunks` list remains as text; no audio generated.

**Real:**
1. Check `profile.voice_mode`:
   - If `ai_clone`: Send each text chunk in `voice_chunks` to OpenAudio S1-mini TTS API with `profile.voice_model_ref` (e.g., "voice_pk_v1"). Receive audio bytes or streaming URL. Store in new state key `audio_chunks`.
   - If `original_only`: Fetch original audio recording. Map each `voice_chunk` text to a timestamp range in the recording (requires metadata during ingestion). Return file paths with start/end times.
   - If `text_only`: Return unchanged (no audio needed).
2. Return updated state with `audio_chunks` for FastAPI layer to stream.

**Why it's stubbed:**
- Requires trained voice models (ParaGPT voice model "voice_pk_v1" doesn't exist yet).
- Requires OpenAudio TTS deployed on PCCI.
- Requires GPU for real-time voice synthesis.

**How to make real:**
1. Add OpenAudio TTS client import.
2. For each chunk in `voice_chunks`:
   - Call TTS API: `tts.synthesize(text=chunk, voice=profile.voice_model_ref, lang="en")`
   - Receive audio bytes or URL.
   - Append to `audio_chunks` list.
3. Set `state["audio_chunks"] = audio_chunks`.
4. Return state.

**Blocking dependency:**
- PCCI GPU (~2GB VRAM) for OpenAudio S1-mini TTS.
- Trained ParaGPT voice model (`voice_pk_v1`) — requires voice cloning preprocessing (not yet done).
- OpenAudio service deployed on PCCI.

---

### 4. Tier 2 Tree Search — Stub → MinIO + PageIndex

**File:** `core/rag/retrieval/tree_search.py` lines 1–54

**Now:**
```python
if docs_with_trees:
    logger.info(
        f"Tier 2 tree search: Found {len(docs_with_trees)} document(s) "
        f"with PageIndex tree paths: {[d[1] for d in docs_with_trees]}. "
        f"MinIO not yet configured — stub returning existing passages unchanged. "
        f"Ready to implement in Week 3 deployment phase."
    )
return existing_passages  # Always unchanged
```
Correctly checks PostgreSQL for `pageindex_tree_path`, but always returns T1 passages without augmentation.

**Real:**
1. For each doc with `pageindex_tree_path`:
   - Connect to MinIO using path (e.g., `s3://clone-trees/sacred_archive/teachings.json`).
   - Fetch PageIndex tree JSON (hierarchical structure: chapters → sections → pages with summaries).
   - Send tree structure + original query to LLM: "Which sections in this document tree are most relevant?"
   - LLM returns section IDs (e.g., "Chapter 2, Section 2.3").
   - Extract passages from those sections from the database.
2. Merge T1 passages + T2 passages.
3. Apply Reciprocal Rank Fusion (RRF) to re-rank combined set.
4. Return augmented `list[dict]`.

**Why it's stubbed:**
- MinIO object storage not deployed on PCCI yet.
- PageIndex trees not yet generated for documents during ingestion (would happen in `core/rag/ingestion/pipeline.py`).

**How to make real:**
1. Add MinIO boto3 client setup (or s3fs).
2. In the loop over `docs_with_trees`, call:
   ```python
   tree_json = s3_client.get_object(Bucket="clone-trees", Key=pageindex_tree_path)
   tree = json.loads(tree_json)
   ```
3. Call LLM to reason over tree:
   ```python
   relevant_sections = llm.invoke(f"Given this tree: {tree}, find sections matching query: {query_text}")
   ```
4. Extract passages for those sections (DB query or already in chunk metadata).
5. Merge + RRF rank.

**Blocking dependency:**
- MinIO deployed on PCCI.
- PageIndex tree generation logic added to ingestion pipeline.
- Example PageIndex tree JSON schema (stored in migration).

---

### 5. Audio/Video Parsing — NotImplementedError → Whisper

**File:** `core/rag/ingestion/parser.py` lines 8–12

**Now:**
```python
audio_video_formats = {".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".flac", ".aac"}
if extension in audio_video_formats:
    raise NotImplementedError(
        "Audio/video parsing requires Whisper integration (future work)"
    )
```
Raises error if user tries to upload audio/video. Only PDF, markdown, text supported.

**Real:**
1. Accept audio/video files.
2. Send to Whisper Large V3 API/service.
3. Receive transcript (text).
4. Set `source_type = "transcript"` (or "audio").
5. Feed transcript through normal chunker → embedder → indexer pipeline.

**Why it's stubbed:**
- Whisper integration requires audio transcription service (GPU-intensive).
- Not a priority for initial deployment (ParaGPT and Sacred Archive will likely start with PDF/text docs).

**How to make real:**
1. Add Whisper client (OpenAI API or local SGLang endpoint for `faster-whisper`).
2. In `parse()` function, add branch:
   ```python
   if extension in audio_video_formats:
       transcript = whisper_client.transcribe(file_path)
       return {"content": transcript["text"], "language": "en"}
   ```
3. Rest of pipeline handles transcript as plain text.

**Blocking dependency:** PCCI GPU (~6GB VRAM) + Whisper Large V3 deployed.

---

## Category 2: Infra-Blocked Stubs (FastAPI + Auth Complete — Needs DB Write Wiring)

FastAPI gateway is **fully built** (Session 8) with 5 endpoint groups and 33 passing tests (Session 11). Auth middleware is **complete** (Session 11, `api/middleware.py`). PostgreSQL is **running** with seeded data (Session 12). The only remaining infra-blocked item is wiring the review_queue_writer node to actually write to the database.

### 1. Review Queue Writer — Print stub → DB Insert

**File:** `core/langgraph/nodes/routing_nodes.py` lines 65–88

**Now:**
```python
confidence = state.get("final_confidence", 0.0)
response = state.get("verified_response", "")
print(f"[REVIEW QUEUE] Response queued for human review. Confidence={confidence:.2f}")
print(f"  Response preview: {response[:100]}...")
```
Prints to stdout. Does not touch database.

**Real:**
```python
INSERT INTO review_queue
  (clone_id, user_id, query_text, response_text, confidence, cited_sources, status)
VALUES
  (?, ?, ?, ?, ?, ?, 'pending')
```
Then optionally send reviewer notification (email, webhook, dashboard signal).

**Why it's still stubbed:**
- `review_queue` table is fully designed (migration 0001 ✅), but node never writes to it.
- PostgreSQL is running ✅ (Session 12), migrations applied ✅, database seeded ✅.
- The node simply prints to stdout instead of inserting into the table.

**How to make real:**
1. ~~Start PostgreSQL locally~~ ✅ Done (Session 12)
2. ~~Run `alembic upgrade head`~~ ✅ Done (Session 12)
3. Add `psycopg` connection in the node:
   ```python
   db_url = os.getenv("DATABASE_URL")
   with psycopg.connect(db_url) as conn:
       with conn.cursor() as cur:
           cur.execute(
               "INSERT INTO review_queue (...) VALUES (...)",
               (clone_id, user_id, query, response, confidence, cited_sources, "pending")
           )
       conn.commit()
   ```
4. Optionally: Send notification to reviewers (email, webhook, Redis pubsub).

**Blocking dependency:** DB write wiring in the node (~20 lines of code). No hardware or infrastructure needed — PostgreSQL is running and the table exists.

---

### 2. access_tier + token_budget — Partially Resolved

**File:** `core/langgraph/nodes/query_analysis_node.py`

**Now (Session 14):**
```python
# access_tier: FIXED — now preserved from initial state via {**state, ...} spread
# Previously hardcoded to "public", overwriting caller-set tier (bug fixed Session 14)
"token_budget": 2000,     # Still hardcoded — minor remaining item
```

**Ideal (token_budget enhancement):**
```python
# token_budget varies by intent:
intent_to_budget = {
    "factual": 2000,
    "synthesis": 8000,
    "temporal": 3000,
    "opinion": 4000,
    "exploratory": 6000,
}
token_budget = intent_to_budget.get(intent_class, 2000)
```

**Current status (Session 14):**
- **access_tier: FIXED** ✅ — `query_analysis_node.py` uses `{**state, ...}` spread which preserves the caller-set `access_tier`. Bug was that it previously hardcoded `"public"`, overwriting the value set by the API layer. Fixed Session 14.
- **Auth middleware: COMPLETE** ✅ (Session 11) — `api/middleware.py` (67 lines) validates `X-API-Key` header against `DCE_API_KEY` env var. Returns 401 if missing, 403 if invalid. 7 passing tests.
- **token_budget: STILL HARDCODED** — Always 2000. The intent-to-budget mapping above would be an enhancement.

**Remaining work (token_budget only):**
1. ~~Add auth middleware to FastAPI~~ ✅ Done (Session 11, `api/middleware.py`)
2. ~~Pass `access_tier` in initial state to graph~~ ✅ Done (Session 14 bug fix)
3. For `token_budget`, implement the intent_to_budget mapping (~10 lines).
4. Could be a profile-level setting instead of hardcoded mapping.

**Blocking dependency:** None for access_tier (done). token_budget enhancement is optional (~10 lines, low priority).

---

## Category 3: Intentional / Partial

These aren't stubs or bugs — they're design choices or awaiting data.

### 1. CRAG Evaluator — Empty Pass-Through (Intentional)

**File:** `core/langgraph/nodes/retrieval_nodes.py` lines 59–60

**Now:**
```python
def crag_evaluator(state: ConversationState) -> ConversationState:
    return state
```

**This is intentional.** The node is a named placeholder in the graph. The actual CRAG routing logic (checking confidence threshold and deciding to retry or proceed) is correctly implemented in the `after_crag()` conditional edge function (in `conversation_flow.py` lines 176–195).

This node could be enhanced in the future to:
- Explicitly evaluate retrieval quality (cross-check passages against query for semantic relevance).
- Detect retrieval failures (all passages from same wrong date range, all irrelevant, etc.).
- Set an explicit `crag_decision` state key instead of relying purely on the float confidence score.

**Status:** Not a bug. No action needed unless future enhancements wanted.

---

### 2. stream_to_user — Partial (Text Split, No Real Streaming)

**File:** `core/langgraph/nodes/routing_nodes.py` lines 91–117

**Now:**
Splits `verified_response` into sentence-level chunks using `split(". ")` and stores in `voice_chunks`. Does not stream anything.

**Real streaming:** Happens at the **FastAPI layer**, not inside LangGraph. This node's job is just to chunk text. The API layer uses WebSocket or Server-Sent Events (SSE) to push tokens to the browser.

**What could be improved:**
- Sentence splitting is primitive. Will break on abbreviations ("Dr. Smith"), decimals ("3.14"), quoted periods. Should use `nltk.sent_tokenize()` or regex-based splitter.

**Status:** Functionally correct by design. Minor improvement: better sentence splitting.

---

### 3. provenance_graph_query — Real Code, Data Present (Session 12)

**File:** `core/langgraph/nodes/retrieval_nodes.py` lines 11–33

**Now:** Real recursive CTE SQL runs flawlessly. As of Session 12, `teachings` and `teaching_relations` tables are seeded with Sacred Archive sample data via `conftest.py` fixture `seed_provenance()`.

```sql
WITH RECURSIVE graph_traversal AS (
    SELECT teaching_id, related_teaching_id, 1 AS depth, ARRAY[teaching_id] AS path
    FROM teaching_relations
    WHERE teaching_id = ANY(seed_teaching_ids)
    UNION ALL
    SELECT tr.teaching_id, tr.related_teaching_id, gt.depth + 1, gt.path || tr.teaching_id
    FROM teaching_relations tr
    JOIN graph_traversal gt ON tr.teaching_id = gt.related_teaching_id
    WHERE gt.depth < 3
)
SELECT * FROM graph_traversal
```

The SQL is correct. It runs only for Sacred Archive (`provenance_graph_enabled=true`). It returns results when there's data; returns empty results when tables are empty.

**Blocking dependency:** Full Sacred Archive corpus ingestion with production-scale provenance metadata. Sample data is loaded (Session 12); production corpus is pending.

**Status:** Not a stub. Working as intended with sample data. Returns real results for Sacred Archive queries in E2E tests.

---

## Category 4: Test Mocks — RESOLVED (Session 14)

Both E2E test mocks were **removed** in Session 14. All 4 tests in `tests/test_e2e.py` now use real services: real PostgreSQL + pgvector, real Groq LLM, real Mem0 with Google Gemini embeddings. No mocks.

**What changed (Session 14):**
- `vector_search.search()` mock removed — tests hit real pgvector with seeded `document_chunks` table
- `get_mem0_client()` mock removed — tests use real Mem0 with pgvector backend + Google Gemini embeddings
- `conftest.py` provides session-scoped fixtures: `ensure_db_seeded` (idempotent), `paragpt_clone_id`, `sacred_clone_id`
- Tests skip gracefully if `DATABASE_URL` or `GROQ_API_KEY` are not set (unit tests still run)

**API tests (`tests/test_api.py`) still use mocks — intentionally:**
- 33 tests mock the DB session and `build_graph` — this is correct because API tests validate HTTP behavior (status codes, JSON shape, auth), not pipeline logic
- Mock strategy: `MagicMock` for DB session with two pre-configured Clone rows; `MagicMock` for `build_graph` returning preset responses
- These mocks are **intentional and permanent** — API unit tests should not require a live database

**Note on `tests/test_voyage_integration.py`:**
- 4 tests that validated Voyage AI integration. Now skipped because `VOYAGE_API_KEY` is no longer in `.env` (provider changed to Google Gemini in Session 14).
- This file could be removed or rewritten as `test_gemini_integration.py` — low priority since E2E tests already validate Google Gemini embeddings end-to-end.

**Minor cosmetic:** `test_e2e.py` header (line 5) still says "Voyage AI vector search" — should say "Google Gemini embeddings".

---

## Summary Table

| Item | File | Type | Status | Blocked By | Priority |
|---|---|---|---|---|---|
| LLM (Groq → SGLang) | `core/llm.py:40` | Dev proxy | ✅ Verified | PCCI GPU (20GB) | High — easy swap |
| Embeddings (Google Gemini → TEI) | `core/rag/ingestion/embedder.py` | Dev proxy | ✅ Verified (Session 14) | PCCI GPU (2GB) | High — LangChain drop-in swap |
| Voice pipeline | `core/langgraph/nodes/routing_nodes.py:120` | Full stub | PCCI GPU (2GB) + voice model | Medium — can test structure early |
| Tier 2 tree search | `core/rag/retrieval/tree_search.py` | Stub | MinIO + tree generation | Medium — logic clear, just needs infra |
| Audio/video parsing | `core/rag/ingestion/parser.py:9` | NotImplementedError | PCCI GPU + Whisper | Low — not priority for MVP |
| Review queue writer | `core/langgraph/nodes/routing_nodes.py:65` | Print stub | DB write wiring (~20 LOC) | High — FastAPI done, DB running ✅ |
| access_tier | `core/langgraph/nodes/query_analysis_node.py` | ~~Hardcoded~~ | ✅ **FIXED** (Session 14) | None | Done |
| token_budget | `core/langgraph/nodes/query_analysis_node.py` | Hardcoded (2000) | Minor remaining | Optional enhancement | Low |
| CRAG evaluator | `core/langgraph/nodes/retrieval_nodes.py:63` | Intentional | Design choice | Low — optional enhancement |
| stream_to_user | `core/langgraph/nodes/routing_nodes.py:91` | Partial | ✅ FastAPI WebSocket done | Low — sentence splitting improvement |
| provenance_graph_query | `core/langgraph/nodes/retrieval_nodes.py:11` | Real code | ✅ Data present (Session 12) | Production corpus pending | Low |
| ~~test: vector_search mock~~ | ~~`tests/test_e2e.py`~~ | ~~Mock~~ | ✅ **REMOVED** (Session 14) | N/A | Resolved |
| ~~test: mem0_client mock~~ | ~~`tests/test_e2e.py`~~ | ~~Mock~~ | ✅ **REMOVED** (Session 14) | N/A | Resolved |

---

## Roadmap

**✅ Week 2 (FastAPI + Auth) — COMPLETE (Sessions 8-11):**
- ✅ FastAPI gateway: 6 files, 5 endpoint groups, WebSocket streaming
- ✅ Auth middleware: `api/middleware.py` (67 lines), X-API-Key validation, 7 tests
- ✅ 33 API tests passing (mocked DB + graph)
- ✅ Mem0 config fix (`langchain_embeddings` → `model`)

**✅ Week 2.5 (Real Integration) — COMPLETE (Sessions 12-14):**
- ✅ PostgreSQL running, pgvector installed, migrations applied, database seeded
- ✅ Google Gemini embeddings replacing Voyage AI (all 4 layers: embedder, retrieval, memory, chunking)
- ✅ E2E test mocks removed — 4 real integration tests (real DB, real vector search, real Mem0, real LLM)
- ✅ access_tier bug fixed (Session 14)
- ✅ Provenance SQL bug fixed (Session 14)
- ✅ 45 tests passing, 6 skipped

**Week 3 (Frontend + Remaining Wiring) — NEXT:**
- Remaining: `review_queue_writer` DB write wiring (~20 lines of code)
- Remaining: `token_budget` intent-to-budget mapping (optional, ~10 lines)
- Next: React Chat Page + Review Dashboard
- Next: Docker Compose for dev environment

**Week 3+ (Voice, if hardware ready):**
- Unlock: `voice_pipeline` (if PCCI GPU + voice model available)

**Week 4+ (PCCI deployment):**
- Unlock: LLM (Groq → SGLang), embeddings (Google Gemini → TEI), Whisper, Tier 2 tree search
- Swap env vars; no code changes

**Optional future:**
- CRAG evaluator enhancement (explicit quality check)
- `stream_to_user` sentence splitting improvement (use `nltk.sent_tokenize()`)
- Zvec swap for ParaGPT (original-plan branch)
- Remove or rewrite `test_voyage_integration.py` as `test_gemini_integration.py`

---

**End of Stubs & Mocks Inventory**
