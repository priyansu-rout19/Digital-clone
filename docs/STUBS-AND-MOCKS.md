# Stubs & Mocks Inventory — Digital Clone Engine

**Last Updated:** March 4, 2026 (Session 12 — Database live, seeded) | **Status:** Comprehensive inventory of all stubs, dev proxies, and test mocks. All core embeddings/LLM/API paths functional and verified. 55 tests passing, zero xfails. PostgreSQL running with pgvector 0.8.2.

---

## Overview

The codebase contains **12 things** that are currently stubbed, mocked, or using dev proxies. They fall into three categories:

1. **Hardware-Blocked** (5 items) — PCCI GPU server or MinIO required
2. **Infra-Blocked** (1 item) — Review queue DB writes need wiring (PostgreSQL now running since Session 12, auth middleware complete since Session 11)
3. **Intentional/Partial** (3 items) — Not bugs; design choices or awaiting data
4. **Test Mocks** (2 items) — Test environment limitations

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

### 2. Embeddings — Voyage AI (dev, Session 9) → TEI (prod)

**File:** `core/rag/ingestion/embedder.py` lines 66–92

**Now (Development, Session 9):**
```python
from langchain_voyageai import VoyageAIEmbeddings
client = VoyageAIEmbeddings(
    model="voyage-3",
    voyage_api_key=os.getenv("VOYAGE_API_KEY"),
)
# Returns 1024-dim vectors via api.voyageai.com HTTP API
```

**Real (Production, when PCCI ready):**
```python
from langchain_community.embeddings import HuggingFaceEmbeddings
# Or use TEI via OpenAI-compatible endpoint:
client = HuggingFaceEmbeddings(
    model_name="Qwen3-Embedding-0.6B",
    # Runs locally on PCCI ~2GB VRAM
)
# Returns 1024-dim vectors from local GPU
```

**Status (Session 9):**
- ✅ **Fully functional and verified** — Voyage AI voyage-3 working across all 4 test layers (embedder, retrieval, memory, LangGraph)
- ✅ 1024-dim output (same as production target)
- ✅ LangChain drop-in interface (zero code changes to swap backends)
- ✅ Tested: 4/4 E2E tests pass, 8-doc batch embedding verified, pipeline visualizer complete

**How to make real (when PCCI TEI deployed):**
1. Deploy TEI on PCCI GPU (~2GB VRAM) serving `Qwen3-Embedding-0.6B` or compatible model
2. Update `core/rag/ingestion/embedder.py`:
   - Replace `VoyageAIEmbeddings` with `HuggingFaceEmbeddings` or TEI via OpenAI-compatible endpoint
   - Point to local PCCI server instead of api.voyageai.com
   - Update `.env`: change `VOYAGE_API_KEY` to local model reference
3. No breaking changes — already using LangChain Embeddings interface

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

## Category 2: Infra-Blocked Stubs (FastAPI Complete — Needs DB + Auth)

FastAPI gateway is **fully built** (Session 8) with 5 endpoint groups and 18 passing tests (Session 10). These items now only need a running PostgreSQL database and auth middleware implementation.

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
- FastAPI layer is built ✅ but PostgreSQL isn't running locally yet — need `alembic upgrade head` first.

**How to make real:**
1. Start PostgreSQL locally (or via Docker)
2. Run `alembic upgrade head` to create tables
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

**Blocking dependency:** Running PostgreSQL + `alembic upgrade head`. No hardware needed. Can implement as soon as DB is up.

---

### 2. access_tier + token_budget — Hardcoded → Auth Lookup

**File:** `core/langgraph/nodes/query_analysis_node.py` lines 87–88

**Now:**
```python
"access_tier": "public",  # Always public
"token_budget": 2000,     # Always 2000
```
Hardcoded. No user authentication; everyone gets public access and fixed token budget.

**Real:**
```python
# From FastAPI middleware:
user_id = request.context.get("user_id")
access_tier = request.context.get("access_tier")  # Resolved from JWT claim or users table

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

**Why it's hardcoded:**
- FastAPI gateway exists ✅ but auth middleware hasn't been added yet.
- No JWT validation or user lookup in the request flow.

**How to make real:**
1. Add auth middleware to FastAPI (`api/deps.py` or new `api/auth.py`):
   - Parse JWT token from `Authorization` header.
   - Look up user in `users` table (schema done in migration 0001 ✅).
   - Extract `access_tier` from user row.
2. Pass `access_tier` in initial state to graph (chat route already builds initial state).
3. In `query_analysis` node, use it instead of hardcoding.
4. For `token_budget`, use the intent_to_budget mapping (can be a profile setting).

**Blocking dependency:** Auth middleware implementation (~80 lines of code, no hardware needed).

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

### 3. provenance_graph_query — Real Code, No Data

**File:** `core/langgraph/nodes/retrieval_nodes.py` lines 5–28

**Now:** Real recursive CTE SQL runs flawlessly. However, `teachings` and `teaching_relations` tables are empty.

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

**Blocking dependency:** Sacred Archive corpus ingestion with provenance metadata. The DB schema is complete; just needs data loaded.

**Status:** Not a stub. Working as intended. Awaiting data.

---

## Category 4: Test Mocks

These exist because the test environment doesn't have a live database or all dependencies.

### Mock 1 — vector_search.search

**File:** `tests/test_e2e.py` lines 91–93, 151–152, 183–188

**Why mocked:**
`vector_search.search()` requires:
- Live PostgreSQL with pgvector extension.
- Populated `document_chunks` table with embeddings.
- `clone_documents_idx` HNSW index.

Tests don't have this setup. Instead of hitting a live DB, the mock returns deterministic data.

**What's mocked:**
```python
with patch("core.rag.retrieval.vector_search.search") as mock:
    mock.return_value = (SAMPLE_PASSAGES, 0.85)  # ParaGPT happy path
```

**Mock return:**
- `SAMPLE_PASSAGES`: 2 hardcoded passage dicts (chunk_id, doc_id, passage text, source_type, etc.).
- Confidence float: 0.85 (ParaGPT), 0.96 (Sacred Archive needs > 0.95), or side_effect list `[0.3, 0.3, 0.9]` for CRAG retry test.

**When it becomes real:**
1. Set up test database with populated `document_chunks` table.
2. Remove the mock.
3. Tests will hit the real `vector_search.search()` and return actual results.

**Note:** All other LLM nodes (query_analysis, in_persona_generator, confidence_scorer, query_reformulator, citation_verifier) are **not mocked** — they make real Groq API calls in the tests. Only retrieval is mocked because DB setup is complex.

---

### Mock 2 — get_mem0_client

**File:** `tests/test_e2e.py` lines 103–108

**Why mocked:**
`get_mem0_client()` requires:
- `DATABASE_URL` to connect to pgvector (for memory embeddings storage).
- `VOYAGE_API_KEY` for embeddings (Session 9: switched from OpenAI to Voyage AI voyage-3).
- `GROQ_API_KEY` for LLM extraction.
- Running PostgreSQL + Mem0 setup.

Tests don't have a running Mem0 DB. Instead, return a mock client.

**Session 11 fix:** The embedder config key was corrected from `langchain_embeddings` to `model` (Mem0's `BaseEmbedderConfig` parameter). Instantiation now works when PostgreSQL is available.

**What's mocked:**
```python
with patch("core.mem0_client.get_mem0_client") as mock:
    mem_client = MagicMock()
    mem_client.search.return_value = {"results": []}  # No prior memories
    mem_client.add.return_value = None                # Silent no-op
    mock.return_value = mem_client
```

**Mock behavior:**
- `.search()` returns empty results (no prior user memories).
- `.add()` does nothing (silently succeeds, doesn't persist).

**When it becomes real:**
1. Set up PostgreSQL with Mem0 backend (pgvector extension required).
2. Populate `.env` with: `DATABASE_URL`, `VOYAGE_API_KEY`, `GROQ_API_KEY`.
3. For unit tests: Keep the mock (DB setup overhead not worth it for simple unit tests).
4. For integration tests: Remove the mock. Tests will use real Mem0.
5. Config key is already correct (`model: VoyageAIEmbeddings(...)` — fixed Session 11).

---

## Summary Table

| Item | File | Type | Status | Blocked By | Priority |
|---|---|---|---|---|---|
| LLM (Groq → SGLang) | `core/llm.py:40` | Dev proxy | ✅ Verified | PCCI GPU (20GB) | High — easy swap |
| Embeddings (Voyage AI → TEI) | `core/rag/ingestion/embedder.py:66` | Dev proxy | ✅ Verified (Session 9) | PCCI GPU (2GB) | High — LangChain drop-in swap |
| Voice pipeline | `core/langgraph/nodes/routing_nodes.py:120` | Full stub | PCCI GPU (2GB) + voice model | Medium — can test structure early |
| Tier 2 tree search | `core/rag/retrieval/tree_search.py` | Stub | MinIO + tree generation | Medium — logic clear, just needs infra |
| Audio/video parsing | `core/rag/ingestion/parser.py:9` | NotImplementedError | PCCI GPU + Whisper | Low — not priority for MVP |
| Review queue writer | `core/langgraph/nodes/routing_nodes.py:65` | Print stub | DB write wiring (PostgreSQL running ✅) | High — FastAPI done, needs DB |
| access_tier + token_budget | `core/langgraph/nodes/query_analysis_node.py:87` | Hardcoded | Auth middleware ✅ (Session 11) | High — needed for multi-tenant |
| CRAG evaluator | `core/langgraph/nodes/retrieval_nodes.py:59` | Intentional | Design choice | Low — optional enhancement |
| stream_to_user | `core/langgraph/nodes/routing_nodes.py:91` | Partial | ✅ FastAPI WebSocket done | Low — sentence splitting improvement |
| provenance_graph_query | `core/langgraph/nodes/retrieval_nodes.py:5` | Real code, no data | Real query wiring (data ingested ✅ Session 12) | Low — awaits data |
| test: vector_search mock | `tests/test_e2e.py:91` | Mock | Test DB not available | Low — acceptable trade-off |
| test: mem0_client mock | `tests/test_e2e.py:103` | Mock | Test env setup | Low — acceptable trade-off |

---

## Roadmap

**✅ Week 2 (FastAPI) — COMPLETE (Sessions 8-11):**
- ✅ FastAPI gateway: 6 files, 5 endpoint groups, WebSocket streaming
- ✅ 18 HTTP tests + 4 Voyage AI tests passing
- ✅ Mem0 config fix (`langchain_embeddings` → `model`)

**Week 3 (Database + Frontend) — IN PROGRESS:**
- ✅ Done: PostgreSQL running, pgvector installed, migrations applied, database seeded (Session 12)
- ✅ Done: Auth middleware (Session 11)
- Partially unlocked: `review_queue_writer` (PostgreSQL running, needs DB write wiring in node)
- Partially unlocked: `access_tier` + `token_budget` (auth middleware done, needs query-level enforcement)
- Next: React Chat Page + Review Dashboard, Docker Compose

**Week 3+ (Voice, if hardware ready):**
- Unlock: `voice_pipeline` (if PCCI GPU + voice model available).

**Week 4+ (PCCI deployment):**
- Unlock: LLM, embeddings, Whisper, Tier 2 tree search (hardware-blocked).
- Swap env vars; no code changes.

**Optional future:**
- CRAG evaluator enhancement (explicit quality check).
- `stream_to_user` sentence splitting improvement (use `nltk.sent_tokenize()`).
- Zvec swap for ParaGPT (original-plan branch).
- TEI + SGLang when PCCI ready.

---

**End of Stubs & Mocks Inventory**
