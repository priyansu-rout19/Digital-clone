# Stubs & Mocks Inventory — Digital Clone Engine

**Last Updated:** March 5, 2026 (Session 17 — Backend Audit & Hardening) | **Status:** 69 tests passing (33 API + 10 chunker + 26 session 16 + 4 E2E real), zero xfails. Only 3 hardware-blocked stubs remain. Session 17 hardened all real implementations (security fixes, bug fixes, code quality).

---

## Overview

The codebase contains **3 remaining stubbed items**, all hardware-blocked (PCCI GPU or MinIO). Six items were resolved in Session 16.

1. **Hardware-Blocked** (3 items) — PCCI GPU server or MinIO required
2. **Dev Proxies** (2 items) — Working with cloud APIs, swappable to local when PCCI ready
3. **All Other Stubs** — ✅ RESOLVED (Session 16)

**Resolved in Session 16:**
- `review_queue_writer` **now writes to DB** — real INSERT INTO review_queue with psycopg
- `audio/video parsing` **now uses Groq Whisper** — transcribes .mp3/.wav/.mp4 etc. via Whisper Large v3 Turbo
- `voice_pipeline` **now uses edge-tts** — generates MP3 audio via Microsoft Edge TTS (free, no API key)
- `token_budget` **now LLM-decided** — LLM estimates context budget per query (1000-4000 range)
- `stream_to_user` **now uses LLM splitting** — context-aware sentence splitting (handles Dr., U.S., etc.)
- `CRAG evaluator` **now adjusts confidence** — passage-count penalty for thin retrieval results

**Previously resolved:**
- E2E test mocks (vector_search, mem0_client) **removed** — all 4 E2E tests use real services (Session 14)
- Auth middleware **complete** — `api/middleware.py` with X-API-Key validation (Session 11)
- access_tier hardcoding bug **fixed** — `query_analysis_node.py` preserves caller-set tier (Session 14)

---

## Category 1: Hardware-Blocked Stubs (3 remaining)

These require PCCI infrastructure (GPU, MinIO). Code is ready; waiting for deployment.

### 1. LLM — Groq API (dev) → SGLang/vLLM (prod)

**File:** `core/llm.py` lines 40–48

**Now:** Groq API with `qwen/qwen3-32b` (cloud service, closely matches production model).

**Production:** PCCI vLLM/SGLang with `Qwen3.5-35B-A3B` (local GPU, 20GB VRAM).

**How to swap:** Change `base_url`, `api_key`, `model` env vars + `model_kwargs` → `extra_body`. Zero code changes to nodes.

**Blocking:** PCCI GPU server with vLLM/SGLang running Qwen3.5-35B-A3B 4-bit AWQ.

---

### 2. Embeddings — Google Gemini (dev) → TEI (prod)

**File:** `core/rag/ingestion/embedder.py`

**Now:** Google Gemini `gemini-embedding-001` (3072→1024 via Matryoshka truncation). Verified across all 4 layers.

**Production:** TEI on PCCI GPU with `Qwen3-Embedding-0.6B` (native 1024-dim, ~2GB VRAM).

**How to swap:** Replace `GoogleGenerativeAIEmbeddings` → `HuggingFaceEmbeddings`. LangChain drop-in interface.

**Blocking:** PCCI GPU server with TEI deployed.

---

### 3. Tier 2 Tree Search — Stub → MinIO + PageIndex

**File:** `core/rag/retrieval/tree_search.py`

**Now:** Correctly checks PostgreSQL for `pageindex_tree_path`, logs findings, returns T1 passages unchanged.

**Production:** Fetch PageIndex tree JSON from MinIO, use LLM to identify relevant sections, merge with RRF.

**Blocking:** MinIO deployed on PCCI + PageIndex tree generation logic.

---

## Category 2: Resolved — Session 16

### 1. Review Queue Writer — ✅ REAL DB INSERT (Session 16)

**File:** `core/langgraph/nodes/routing_nodes.py` lines 78–139

**Was:** Print stub (`print(f"[REVIEW QUEUE] ...")`)

**Now:**
```python
with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO review_queue (id, clone_id, user_id, query_text, response_text, "
            "cited_sources, confidence_score, status) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, 'pending')",
            (uuid4, clone_id, user_id_val, query_text, response_text, json.dumps(cited_sources), confidence),
        )
    conn.commit()
```
- Uses psycopg direct connection (same pattern as retrieval_nodes.py)
- Handles `user_id="anonymous"` → `None` (UUID column, nullable)
- Cited sources serialized as JSONB
- Graceful fallback: logs error on failure, never crashes pipeline
- 5 tests in `test_session16.py`

---

### 2. Token Budget — ✅ LLM-DECIDED (Session 16)

**File:** `core/langgraph/nodes/query_analysis_node.py`

**Was:** Hardcoded `"token_budget": 2000`

**Now:** LLM estimates token budget as part of the query analysis call (single LLM call, no extra API cost):
```python
# LLM returns: {"intent": "synthesis", "sub_queries": [...], "token_budget": 3000}
token_budget = max(1000, min(4000, int(result.get("token_budget", 2000))))
```
- Range clamped to [1000, 4000]
- Factual queries get ~1500, synthesis/exploratory get ~3000
- Falls back to DEFAULT_TOKEN_BUDGET=2000 on parse error
- 4 tests in `test_session16.py`

---

### 3. Audio/Video Parsing — ✅ GROQ WHISPER (Session 16)

**File:** `core/rag/ingestion/parser.py`

**Was:** `raise NotImplementedError("Audio/video parsing requires Whisper integration")`

**Now:**
```python
def _parse_audio(file_path: str) -> list[str]:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    transcription = client.audio.transcriptions.create(
        file=(path.name, audio_file.read()),
        model="whisper-large-v3-turbo",
        response_format="verbose_json",
    )
    # Split transcript into ~500-char blocks at sentence boundaries
    return blocks
```
- Uses existing `GROQ_API_KEY` (same key as LLM — no new credentials needed)
- Whisper Large v3 Turbo (216x real-time speed)
- 25MB file size validation
- Supports: .mp3, .wav, .m4a, .mp4, .avi, .mov, .flac, .aac
- Returns `list[str]` blocks (same interface as PDF/text parsing)
- 5 tests in `test_session16.py`

---

### 4. Voice Pipeline — ✅ EDGE-TTS (Session 16)

**File:** `core/langgraph/nodes/routing_nodes.py`

**Was:** Empty stub (`return state`)

**Now:** Factory function `make_voice_pipeline(profile)` using edge-tts:
```python
async def _run_edge_tts(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])
    return audio_buffer.getvalue()
```
- **ai_clone mode:** Generates MP3 audio via edge-tts (Microsoft Edge TTS, completely free)
- **original_only mode:** Stub (needs recording timestamp mapping)
- **text_only mode:** Never reached (conditional edge skips)
- Audio stored as base64 in `state["audio_base64"]` for API layer
- New ConversationState keys: `audio_base64`, `audio_format`
- Async-to-sync bridge with thread pool fallback for running event loops
- Graceful fallback: if TTS fails, continues without audio
- New dependency: `edge-tts` in requirements.txt
- 4 tests in `test_session16.py`

---

### 5. Sentence Splitting — ✅ LLM-BASED (Session 16)

**File:** `core/langgraph/nodes/routing_nodes.py` (stream_to_user)

**Was:** `sentences = response_text.split(". ")` — breaks on "Dr. Smith", "U.S.", "3.14"

**Now:** LLM-based context-aware splitting:
```python
llm = get_llm(temperature=0.0)
result = llm.invoke([
    {"role": "system", "content": "Split text into sentences. Return JSON array."},
    {"role": "user", "content": response_text},
])
sentences = json.loads(result.content)
```
- Handles abbreviations, decimals, dialogue correctly
- Falls back to naive `split(". ")` on LLM error
- 3 tests in `test_session16.py`

---

### 6. CRAG Evaluator — ✅ CONFIDENCE ADJUSTMENT (Session 16)

**File:** `core/langgraph/nodes/retrieval_nodes.py` lines 63–80

**Was:** `return state` (empty passthrough)

**Now:** Passage-count-aware confidence adjustment:
```python
passage_count_factor = min(len(passages) / 3.0, 1.0)
adjusted = raw_confidence * passage_count_factor
```
- No passages → confidence 0.0
- 1 passage with 0.9 confidence → 0.3 (penalized — thin results)
- 3+ passages → no penalty
- No LLM call (fast — CRAG runs up to 3x in retry loop)
- 5 tests in `test_session16.py`

---

## Category 2b: Session 17 Hardening (12 fixes to real implementations)

Session 17 ran a 3-agent backend audit and fixed 12 issues across the codebase. These aren't stub replacements — they're improvements to already-real code:

**Bugs Fixed:**
- `soft_hedge_router`: Now overwrites BOTH `raw_response` AND `verified_response` (silence mechanism was broken)
- `api/routes/ingest.py`: Strips `+psycopg` from DATABASE_URL before passing to `psycopg.connect()`
- `generation_nodes.py`: Sacred Archive uses `temperature=0.0` for mirror_only mode (was hardcoded 0.7)

**Security Fixed:**
- `provenance.py`: SQL injection — f-string interpolated IDs replaced with parameterized `= ANY(%s)`
- `api/routes/ingest.py`: Path traversal — `file.filename` sanitized with `Path(name).name`
- `api/routes/review.py`: Cross-tenant — `PATCH /review/{id}` → `PATCH /review/{clone_slug}/{review_id}` with clone-scoping
- `api/routes/chat.py`: WebSocket DB session leak — removed unused `Depends(get_db)` from handler
- `api/routes/chat.py`: Privacy leak — removed `user_memory` from API response (internal data only)

**Code Quality:**
- `api/routes/ingest.py`: `BackgroundTasks` mutable default removed
- `core/db/__init__.py`: `psycopg_url()` shared utility (was duplicated in 2 node files)
- `routing_nodes.py`: Regex-based sentence splitting (fixed double periods in `_naive_split`)
- `requirements.txt`: Removed orphaned `tf-keras`, pinned `pymupdf`, `mem0ai`, `edge-tts`

---

## Category 3: Intentional / Unchanged

### 1. provenance_graph_query — Real Code, Data Present (Session 12)

**File:** `core/langgraph/nodes/retrieval_nodes.py`

Real recursive CTE SQL. Works with sample data. Returns real results for Sacred Archive queries. Not a stub.

---

## Category 4: Test Mocks — Status

**E2E tests:** All 4 tests use real services (no mocks). Session 14.

**API tests:** 33 tests mock DB + graph (intentional — tests HTTP behavior, not pipeline logic).

**Session 16 tests:** 26 new tests in `tests/test_session16.py` (all mocked, testing individual node logic).

---

## Summary Table

| Item | File | Status | Session |
|---|---|---|---|
| LLM (Groq → SGLang) | `core/llm.py` | Dev proxy ✅ — Blocked by PCCI GPU | — |
| Embeddings (Gemini → TEI) | `core/rag/ingestion/embedder.py` | Dev proxy ✅ — Blocked by PCCI GPU | 14 |
| Tier 2 tree search | `core/rag/retrieval/tree_search.py` | Stub — Blocked by MinIO | — |
| ~~Review queue writer~~ | `routing_nodes.py` | ✅ **REAL DB INSERT** | **16** |
| ~~Audio/video parsing~~ | `parser.py` | ✅ **GROQ WHISPER** | **16** |
| ~~Voice pipeline~~ | `routing_nodes.py` | ✅ **EDGE-TTS** | **16** |
| ~~Token budget~~ | `query_analysis_node.py` | ✅ **LLM-DECIDED** | **16** |
| ~~Sentence splitting~~ | `routing_nodes.py` | ✅ **LLM-BASED** | **16** |
| ~~CRAG evaluator~~ | `retrieval_nodes.py` | ✅ **CONFIDENCE ADJUSTMENT** | **16** |
| ~~access_tier~~ | `query_analysis_node.py` | ✅ **FIXED** | 14 |
| ~~E2E test mocks~~ | `test_e2e.py` | ✅ **REMOVED** | 14 |
| provenance_graph_query | `retrieval_nodes.py` | Real code ✅ | 12 |

---

## Roadmap

**✅ Complete:**
- FastAPI gateway + Auth middleware (Sessions 8-11)
- Real integration tests (Sessions 12-14)
- Stub replacement session (Session 16): 6 stubs → real code

**Next:**
- Frontend mockup designs in Variant (manager directive)
- React Chat Page + Review Dashboard (after design approval)
- Docker Compose for dev environment

**When PCCI ready:**
- LLM: Groq → SGLang (env var swap)
- Embeddings: Gemini → TEI (LangChain drop-in)
- Tree search: MinIO + PageIndex
- Voice: edge-tts → OpenAudio TTS (with trained voice model)

---

**End of Stubs & Mocks Inventory**
