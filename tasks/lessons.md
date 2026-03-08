# Lessons Learned — Digital Clone Engine

## Session 1: TECH-TEAM-RESPONSE Document (Feb 27, 2026)

### Lesson 1: Voice Consistency in Technical Writing
**What happened:** Initial TECH-TEAM-RESPONSE.md used "I", "we", and "our" inconsistently when responding to a team report.

**The pattern:** When writing a response TO a team about THEIR report, only "I" applies to research actions (I found, I recommend). When referring to the system/architecture, use neutral language (the system, the stack, this scale, the graph).

**Rule for future:**
- "I" = research verbs only (reviewed, analyzed, tested, recommend)
- "We/our" = never in response documents
- System references = neutral third-person (the system, the architecture, the approach)
- Test: replace "I'm running X" with "the system runs X"

---

### Lesson 2: Avoid Stylistic Markers That Look AI-Generated
**What happened:** Document used em dashes (—) throughout, which made it read as AI-written.

**The pattern:** Simple stylistic choice (punctuation, word choice) can make human-written docs look machine-generated. Even if technically correct, it breaks authenticity.

**Rule for future:**
- Avoid em dashes — use commas, periods, or rephrase instead
- Prefer simple connectors: "because", "since", "so" over complex punctuation
- Read for rhythm: does it sound like a person wrote it, or a language model?

---

### Lesson 3: Don't Include Information You Explicitly Excluded
**What happened:** TECH-TEAM-RESPONSE included timeline commentary (Week 0, Week 3, Week 4) when user said "don't do anything with timeline".

**The pattern:** When user says "exclude X", that means remove it completely — not just the main section, but also all tangential references. One incomplete removal breaks the exclusion.

**Rule for future:**
- Search the entire document for references to excluded topic
- Remove all related context, not just the main section
- Verify with grep/search that zero references remain

---

### Lesson 4: Answers Should Be Concise but Not Hollow
**What happened:** Initial answers in corrections and questions sections were long (500+ words). User asked to trim them, but said "not very short — good way to understand the thing".

**The pattern:** There's a middle ground between data dumps and one-liners. Good answer = decision + key reason why + practical impact. Nothing more.

**Rule for future:**
- Answer format: statement (what) → justification (why, 1-2 sentences) → impact (so what)
- Cut everything that's not one of those three
- Cut all time estimates, project planning commentary, and timeline references unless explicitly asked
- Cut all "this will take X days" or "saves Y days" commentary

---

### Lesson 5: Understand the User's Context Before Suggesting Structure
**What happened:** Proposed folder structure and MD files before understanding user's workflow preferences and how Claude Code should be used.

**The pattern:** User works with people effectively when context is clear and structured. Structure files not for machines, but for human understanding and Claude Code sessions. Each file should be a self-contained unit of work.

**Rule for future:**
- Read CLAUDE.md FIRST before designing any workflow
- Plan mode must check project instructions, not just assume best practices
- One spec file = one task for Claude Code = one self-contained context
- Structure mirrors the user's thinking (not the system's architecture)

---

### Lesson 6: Pydantic v2 Enum Serialization for Config Objects
**What happened:** Implemented CloneProfile with 6 enums. Used `str, Enum` pattern to ensure JSON serialization produces string values, not enum repr objects.

**The pattern:** Config objects stored in JSON (JSONB in PostgreSQL) must serialize cleanly. When enum values appear in a JSONB column, they need to be JSON-native strings, not Python enum representations. `class MyEnum(str, Enum)` makes this automatic — no custom serializers needed.

**Rule for future:**
- Config enums should inherit from `str, Enum` (not just `Enum`)
- This makes `model_dump_json()` produce clean strings: `"interpretive"` not `MyEnum.interpretive`
- For API/config objects, `str, Enum` is the default pattern
- Verified: both ParaGPT and Sacred Archive presets serialized to valid JSON with all 16 fields

---

### Lesson 7: Model Validators vs Field Validators in Pydantic v2
**What happened:** Used `@model_validator(mode="after")` to validate cross-field relationships (voice_mode + voice_model_ref).

**The pattern:** Field validators check single fields; model validators check relationships between fields after all fields are set. For business logic like "voice_model_ref must be non-null if and only if voice_mode is ai_clone", use `@model_validator(mode="after")`.

**Rule for future:**
- Use `@field_validator` for single-field constraints (min/max, regex, enum check)
- Use `@model_validator(mode="after")` for cross-field relationships
- Test validators with invalid inputs to ensure they catch errors (did this: tested 2 invalid combos, both caught)
- Pydantic v2 syntax is different from v1 — always check docs

---

### Lesson 8: Conditional Routing in LangGraph with Profile-Driven Closures
**What happened:** Implemented LangGraph StateGraph with conditional edges that check CloneProfile fields. Routing decisions (which node to visit next) are made by closures that capture the profile at build time.

**The pattern:** Each conditional routing function reads profile fields like `profile.review_required`, `profile.voice_mode`, etc., and returns the next node name. This lets the SAME graph structure serve two completely different clients with different behavioral paths. ParaGPT's `confidence_scorer` → `stream_to_user` path, but Sacred Archive's `confidence_scorer` → `review_queue_writer` path (because `review_required=true`). No code branches — just routing logic.

**Rule for future:**
- Conditional edges in LangGraph take a function that returns a string (node name)
- Capture external config (like CloneProfile) in closures at graph build time
- Use dictionaries in `add_conditional_edges()` to map return values to node names
- Test both code paths by building graphs for different profiles and invoking them

---

### Lesson 9: Stub Nodes with Correct State Signatures Unblock Integration
**What happened:** Implemented 16 nodes with full type signatures and state updates. Nodes that depend on missing components (RAG, DB, LLM) are stubs — they return mock data with correct shapes. Graph structure and routing verified WITHOUT waiting for RAG/DB implementation.

**The pattern:** Stubs have:
1. Correct function signature: `(state: TypedDict) -> TypedDict`
2. Correct state keys: each stub returns state with the right keys set (e.g., `retrieval_confidence`, `raw_response`)
3. `# STUB: depends on component XX` comment so it's clear what's not production-ready
4. Mock data: returns 0.0 for confidence, empty list for passages, etc.

This lets us test the ORCHESTRATION (routing, state flow) without the actual implementations. When component 02 (RAG) is built, `tier1_retrieval` node is updated to call the real `retrieve()` function — graph structure unchanged.

**Rule for future:**
- Always include stub nodes in the graph, even if implementation is deferred
- Correct state shapes are critical — stub nodes return state dicts with the same keys
- STUB comments make it obvious what needs real implementation later
- Invoke the graph with stubs to verify routing logic works

---

### Lesson 10: Factory Pattern for Profile-Dependent Nodes in LangGraph
**What happened:** Integrated real LLM calls into stub nodes. Some nodes needed access to the CloneProfile (e.g., in_persona_generator needs the persona prompt, soft_hedge_router needs the silence_message). But LangGraph node functions have signature `(state) -> state`, which doesn't include profile.

**The pattern:** Node factory functions solve this with closures:
```python
def make_in_persona_generator(profile: CloneProfile):
    def in_persona_generator(state):
        # profile is captured in closure
        system_prompt = f"You are {profile.display_name}..."
    return in_persona_generator
```
Then: `graph.add_node("in_persona_generator", make_in_persona_generator(profile))`

**Rule for future:**
- If a node needs external config, use a factory function with closure
- Factory is called at graph.add_node() time, not execution time
- Keep profile out of state (state is request-specific, profile is config)

---

### Lesson 11: Real LLM Integration and Model Deprecation Handling
**What happened:** Integrated Groq API to power 5 key nodes. Selected model `qwen-qwq-32b` but it was deprecated. Pivoted to `llama-3.3-70b-versatile` — same quality, still available.

**The pattern:** When integrating external LLM APIs, models change. Solution:
1. Keep model name in one place (`core/llm.py` `get_llm()`)
2. Store API keys in `.env` (gitignored, never in code)
3. Graceful fallbacks: try/except on JSON parsing, sensible defaults on error
4. Test early: verify LLM connection before wiring into complex graphs

Real LLM calls now power:
- `query_analysis`: intent classification + query decomposition (JSON with heuristic fallback)
- `in_persona_generator`: persona-aware response generation (uses profile.generation_mode)
- `confidence_scorer`: LLM rates response quality 0.0-1.0 (with 0.5 fallback on parse error)
- `query_reformulator`: rephrases low-confidence queries (JSON alternatives list)
- `soft_hedge_router`: uses profile.silence_message (no LLM)

**Rule for future:**
- API keys in `.env`, model names in `core/llm.py`
- JSON parsing always includes try/except with sensible fallback
- Test LLM integration early (don't wait until everything is wired)

---

### Lesson 12: Environment Dependency Pinning — Silent Downgrades Break Silently
**What happened:** Session 6 ran `pip install mem0ai` which silently downgraded `langchain-core` from 1.2.16 → 0.3.83. The requirements.txt pinned 1.2.16, but pip chose a compatible version for mem0ai that broke everything downstream. Tests couldn't run because of ImportError for `ContextOverflowError` which doesn't exist in 0.3.83.

**The pattern:** Dependency managers resolve package conflicts by selecting compatible versions. If Package A requires `langchain-core<1.0.0` and you try to install `langchain-core==1.2.16`, the resolver might downgrade instead of failing loudly. This happens SILENTLY — no error until you try to import something from the newer version.

**Solution:** After adding any new dependencies (especially LLM ecosystem packages):
1. Run `pip install package_name` + immediately run `pip show langchain-core langchain langchain-openai`
2. Verify versions match requirements.txt
3. If mismatch, upgrade the entire ecosystem: `pip install "langchain>=0.4.0" "langchain-community>=0.4.0"`
4. Alternatively: pin all related packages explicitly in requirements.txt

**Rule for future:**
- Never install from requirements.txt without verifying final versions: `pip show <key-packages>`
- LangChain ecosystem is especially prone to version conflicts (0.3.x vs 1.x series)
- If adding mem0ai or similar, upgrade langchain group immediately after
- Keep a checklist: after `pip install X`, verify the 5 most-changed packages

---

### Lesson 13: Mock Path Resolution — Import Location vs Definition Location
**What happened:** Session 6 E2E tests needed to mock `get_mem0_client()`. Initial attempts patched `"core.mem0_client.get_mem0_client"` which failed because the test framework couldn't find the attribute at the module level.

**The pattern:** `unittest.mock.patch()` works with how Python imports work. When `context_nodes.py` does:
```python
def memory_retrieval(state):
    from core.mem0_client import get_mem0_client  # lazy import
    mem = get_mem0_client()
```

You can't patch at the module level (`core.langgraph.nodes.context_nodes.get_mem0_client`) because the import hasn't happened yet. You patch at the SOURCE where it's defined: `"core.mem0_client.get_mem0_client"`.

BUT the correct approach is to patch where the IMPORT HAPPENS (the place where you're calling the function), not where it's defined. However, since the import is lazy (inside the function), the standard approach is to patch at the definition point.

After iteration, the correct mock path was: `"core.mem0_client.get_mem0_client"` — patching the source, not the lazy import site.

**Rule for future:**
- When mocking: patch at the source of the function (`"module.function"`), not the import site
- For lazy imports (inside functions), patch still works at source
- Test the mock path EARLY (run one test before running the full suite)
- If patch fails with "does not have the attribute", check:
  1. Is the function actually in that module?
  2. Is there a typo in the path?
  3. Try running `python3 -c "from module import function"` to verify the import works

---

### Lesson 14: E2E Test Fixtures and Confidence Thresholds
**What happened:** Session 6 built 4 E2E test cases. Two tests (ParaGPT, CRAG loop) use the same `mock_retrieval` fixture returning confidence 0.85. But Sacred Archive has a DIFFERENT confidence threshold (0.95). Fixture value 0.85 is below that, which triggers CRAG loop in Sacred Archive test when it shouldn't.

**The pattern:** Confidence-based routing depends on threshold comparison:
```python
if retrieval_confidence < profile.confidence_threshold:
    # trigger CRAG loop
```

When mocking retrieval, the mock value must account for the profile's threshold. Sacred Archive's 0.95 threshold requires mock value >= 0.95. ParaGPT's threshold (factory 0.80, DB 0.60) is satisfied by 0.85.

Solution: Use INLINE patches for profile-specific tests, FIXTURE for shared tests.

**Rule for future:**
- Confidence-dependent tests: check the profile's threshold FIRST
- Create fixtures for shared threshold values (all profiles use same threshold)
- Use inline patches for profile-specific thresholds (override at test level)
- Comment the threshold check in every test that mocks retrieval

---

### Lesson 15: Reasoning Mode Control Varies by Backend & Model Version

**What happened:** Session 6.5 fixed `<think>` tags in LLM responses. Qwen3-32B on Groq used `reasoning_effort="none"`, but production Qwen3.5-35B-A3B will use `enable_thinking=False`.

**The pattern:** Different inference backends expose reasoning control differently:
- **Groq API** (proprietary): `reasoning_effort` enum ("none", "default", "low", "medium", "high")
- **vLLM/SGLang** (open-source): `enable_thinking` boolean (True/False)
- **Qwen3 soft prompts**: `/think` and `/nothink` tokens (unreliable on some backends)

Qwen3-32B and Qwen3.5-35B-A3B both generate `<think>...</think>` by default. Same problem, different solutions.

**Rule for future:**
- When swapping inference backends (Groq → SGLang/vLLM), reasoning control parameters change
- Research the backend's API documentation FIRST before assuming parameter names match
- For `core/llm.py`: use `model_kwargs` for Groq, `extra_body` for OpenAI-compatible servers
- Qwen3.5-35B requires vLLM 0.9.0+ for stable `enable_thinking` support
- When PCCI GPU server launches, update `get_llm()` to detect environment and use correct parameter
- Test reasoning-disabled behavior early to catch backend-specific bugs (e.g., vLLM 0.8.5 had a bug with `enable_thinking=False`)

---

### Lesson 17: FastAPI Dependency Injection + Database Sessions for Sync Code

**What happened:** Session 8 built FastAPI layer exposing LangGraph orchestrator. Key design choice: use sync SQLAlchemy sessions (not async SQLAlchemy) to avoid rewriting existing `core/db/schema.py` code.

**The pattern:** FastAPI supports BOTH async and sync dependencies. When you have sync code (like `core/db/schema.py` ORM models), you can use sync sessions in FastAPI routes:

```python
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/clone/{slug}/profile")
async def get_profile(slug: str, db: Session = Depends(get_db)):
    # db is a sync SQLAlchemy Session
    # Can be used in async route without blocking issues
    return db.query(Clone).filter(...).first()
```

**Why this works:** FastAPI routes are async, but individual operations inside them can be sync. The database query is fast enough (<100ms) that blocking doesn't matter. If queries took seconds, we'd need `run_in_executor()` to move them to a thread pool.

**Trade-offs considered:**
1. **Full async (async SQLAlchemy)** — requires rewriting all `core/db/schema.py` ORM models. Not worth it for this stage.
2. **Sync sessions in async route** — minimal changes, works fine for <100ms operations. ✅ Chosen.
3. **Async wrapper with executor** — hybrid approach, more complex. Only needed if queries get slow.

**Rule for future:**
- When integrating sync code (ORM, DB, LLM) into async framework (FastAPI):
  - First: measure operation time (is it <100ms?)
  - If yes: use sync directly in async route (simpler)
  - If no (seconds): wrap with `run_in_executor()` or convert to async client
  - Don't pre-maturely convert entire codebase to async
- Dependency injection pattern: `Depends(get_db)` yields a Session that FastAPI manages (calls cleanup in finally block)
- Each request gets a fresh DB session (no connection reuse across requests)

---

### Lesson 16: Spec Compliance — Read Original Docs, Don't Assume Implementation

**What happened:** Session 7 discovered that Tier 2 (tree_search) was positioned AFTER the CRAG loop when the original spec said it should run IMMEDIATELY after T1 (before CRAG). Current implementation: `T1 → CRAG → T2 → context`. Spec: `T1 → T2 → CRAG`. CRAG should evaluate the enriched T1+T2 result, not just T1.

**The pattern:** Implementation details can drift from spec during development. Especially when:
1. Building incrementally (finish T1, then add CRAG, then add T2)
2. Stub nodes make it easy to defer decisions
3. No one re-reads the original spec after initial implementation

The current approach worked (all tests passed), but it meant CRAG couldn't benefit from T2's structural enrichment on the first pass. The retry loop still worked, but was sub-optimal.

**Solution:** Always check the original spec document when someone asks a question like "how does feature X work?". If their description doesn't match current implementation, the spec is the source of truth.

**Rule for future:**
- When implementing multi-component systems, write out the expected sequence ONCE (in spec or comments)
- After implementation completes, verify actual code matches that sequence
- If implementation diverged, fix it to match spec (not the other way around)
- Reference the spec document in code comments so future readers know the source of truth
- For Tier 2: added comment to `after_tier1()` function explaining T2 runs immediately after T1, before CRAG evaluates

---

### Lesson 18: FastAPI Testing with Mocked Dependencies

**What happened:** Session 10 built comprehensive HTTP endpoint tests for FastAPI layer using httpx.AsyncClient, async fixtures, and mocked dependencies (DB session + LangGraph graph).

**The pattern:** FastAPI testing with real async endpoints requires:
1. **Async fixtures** — Must declare fixtures with `@pytest.fixture` (non-async) but use async client inside them
2. **Dependency overrides** — FastAPI's `app.dependency_overrides[get_db]` lets tests inject mocks globally
3. **ASGITransport** — httpx requires `ASGITransport(app=app)` to send requests to the FastAPI app
4. **Mock strategy** — Mock database session with pre-configured clones; mock graph with preset final states
5. **Flexible query mocking** — For multiple model types (Clone vs ReviewQueue), use `side_effect` functions that dispatch based on model type
6. **pytest-asyncio** — Enables `@pytest.mark.asyncio` on async test functions; requires conftest.py setup

**Rule for future:**
- Always use `httpx.AsyncClient(transport=ASGITransport(app=app))` for FastAPI async endpoint testing
- Store original side_effect before overriding; restore after test (prevents recursion)
- Create shared fixtures for common mocks (clones, profiles); override per-test for specific behaviors
- Prefer `@pytest.mark.skipif` with infrastructure checks over `@pytest.mark.xfail` for infra-dependent tests
- Mark async test functions with `@pytest.mark.asyncio`, async fixtures don't need decorator
- Load .env in conftest.py at session startup (before test collection)

---

### Lesson 20: DATABASE_URL format mismatch (SQLAlchemy vs raw psycopg)

**Date:** Session 12 | **Category:** Database connectivity

**What happened:** The `IngestionPipeline` and `indexer.py` call `psycopg.connect(db_url)` directly (not via SQLAlchemy). The `.env` has `DATABASE_URL=postgresql+psycopg://postgres@localhost/dce_dev` which works for SQLAlchemy's `create_engine()` but causes errors with raw `psycopg.connect()` because psycopg doesn't understand the `+psycopg` dialect prefix.

**Fix:** Strip the dialect prefix before passing to pipeline/indexer:
```python
PSYCOPG_URL = DATABASE_URL.replace("+psycopg", "")
```

**Rule for future:**
- SQLAlchemy URLs use dialect format: `postgresql+psycopg://`
- Raw psycopg URLs use standard format: `postgresql://`
- When mixing ORM (SQLAlchemy) and raw driver (psycopg) in the same codebase, maintain both URL formats
- Always check whether the consuming library is SQLAlchemy or raw psycopg before passing DATABASE_URL

---

### Lesson 21: Alembic shebang trap on Fedora

**Date:** Session 12 | **Category:** Python tooling

**What happened:** Running bare `alembic upgrade head` used `/usr/bin/alembic` which has `#!/usr/bin/python3 -sP` shebang. The `-sP` flags strip site-packages from sys.path, causing `ModuleNotFoundError: No module named 'pydantic'` (and any other pip-installed package).

**Fix:** Always use `python3 -m alembic` instead of bare `alembic` — this runs Alembic through the Python interpreter with the full sys.path including site-packages.

**Rule for future:**
- Never trust system-installed Python tool wrappers (`/usr/bin/alembic`, `/usr/bin/pytest`, etc.) — they may have restrictive shebangs
- Always prefer `python3 -m <tool>` for pip-installed tools (alembic, pytest, uvicorn)
- This is especially common on Fedora/RHEL where system Python has strict isolation policies

---

### Lesson 22: Semantic Chunking vs Fixed-Size Chunking

**Date:** Session 13 | **Category:** RAG pipeline

**What happened:** Called our chunker "semantic" but it was actually paragraph-aware fixed-size (splits by token count, not topic). Chunks accumulated paragraphs until hitting 512 tokens with 15% overlap — no embedding similarity was used during chunking.

**Root cause:** No embedding similarity used during chunking. The old chunker respected paragraph boundaries but still split based on token count limits, not topic coherence. A chunk could contain the end of one topic and the beginning of another if they fit within the token budget.

**Fix:** Replaced with LangChain's `SemanticChunker` (`langchain-experimental==0.4.1`) + Voyage AI embeddings. The SemanticChunker embeds sentence groups, compares cosine similarity between consecutive groups, and splits at points where similarity drops (topic boundaries). Old chunker preserved as fallback via `ChunkingStrategy` enum (`fixed_size` vs `semantic`) on CloneProfile.

**Result:** Re-ingested sample documents: 4 fixed-size chunks became 8 semantic chunks. Each chunk is now a self-contained topic unit, improving retrieval precision (queries match the right topic, not a mixed chunk).

**Rule for future:**
- True semantic chunking requires embedding-based similarity comparison between text segments
- Fixed-size chunking with paragraph boundaries is NOT semantic chunking — it's paragraph-aware fixed-size
- When choosing chunking strategy: semantic = better retrieval quality, fixed-size = more predictable chunk sizes
- Always verify chunk quality by inspecting actual output (not just counting chunks)
- Keep the old strategy as a fallback — some use cases may prefer predictable sizes over topic coherence

---

### Lesson 23: Silence Mechanism — Both Response Fields Must Be Overwritten

**Date:** Session 17 | **Category:** Pipeline bug

**What happened:** `soft_hedge_router` set `raw_response = profile.silence_message` when confidence was low, but left `verified_response` unchanged. The downstream `stream_to_user` node reads `verified_response` first (it's the citation-verified version). So the hedge message never reached the user — they got the original un-hedged LLM response instead.

**Root cause:** The pipeline has two response fields: `raw_response` (from LLM) and `verified_response` (from citation_verifier). When overwriting a response (hedge, silence, etc.), BOTH must be set. Otherwise the downstream consumer picks up the old value from the field you didn't touch.

**Fix:** Added `"verified_response": profile.silence_message` alongside `"raw_response"` in the hedge router return.

**Rule for future:**
- When ANY node overwrites a response, it must overwrite ALL response-carrying state fields
- Check which field downstream consumers actually read (not which one you think they read)
- State fields that are "copies" or "refined versions" of each other must stay in sync when either is modified

---

### Lesson 24: SQL Parameterization — Defense-in-Depth Even for Trusted Inputs

**Date:** Session 17 | **Category:** Security

**What happened:** `provenance.py` built SQL queries with f-string interpolated IDs: `seed_ids_sql = ",".join([f"'{id}'" ...])` then `WHERE ... IN ({seed_ids_sql})`. The IDs came from our own database (chunk IDs from vector search), so practical risk was low. But this is still a SQL injection vector — if any upstream change causes user-controlled data to flow into those IDs, the vulnerability activates silently.

**Fix:** Replaced all `IN ({seed_ids_sql})` with parameterized `= ANY(%s)` passing a Python list. The same file already used `ANY(%s)` correctly in other queries, making the inconsistency obvious.

**Rule for future:**
- NEVER interpolate values into SQL strings, even if they "come from the database"
- Use `= ANY(%s)` with a list parameter instead of `IN (...)` with interpolated values
- If you see `f"'{variable}'"` in SQL, it's a bug. Fix it immediately.
- Check for consistency within the same file — if some queries are parameterized and others aren't, fix the outliers

---

### Lesson 25: Path Traversal in File Uploads — Always Sanitize Filenames

**Date:** Session 17 | **Category:** Security

**What happened:** `api/routes/ingest.py` used `file_path = upload_dir / file.filename` directly from the multipart upload. A crafted filename like `../../etc/passwd` or `../../../home/user/.env` could write files outside the upload directory.

**Fix:** Sanitize to basename only: `file_path = upload_dir / Path(file.filename).name`. The `Path.name` property strips all directory components, returning only the filename part.

**Rule for future:**
- NEVER use `file.filename` from HTTP uploads directly in path construction
- Always sanitize with `Path(filename).name` (strips directory traversal)
- Consider additional sanitization: reject names with special chars, limit length
- This applies to ANY user-provided filename — multipart uploads, form fields, API parameters

---

### Lesson 26: Multi-Tenant API Routes — Every Mutation Needs Clone-Scoping

**Date:** Session 17 | **Category:** Security / Architecture

**What happened:** `PATCH /review/{review_id}` had no clone-scoping — any API key holder could approve/reject any clone's reviews by guessing the UUID. The `GET /review/{slug}` endpoint was correctly scoped (required clone slug), but the PATCH endpoint accepted a bare review ID without verifying which clone it belonged to.

**Fix:** Changed route to `PATCH /review/{clone_slug}/{review_id}`, added `get_clone` dependency, and added `ReviewQueue.clone_id == clone_id` to the query filter.

**The pattern:** Read endpoints might be acceptable without strict scoping (public profiles, etc.), but write/update/delete endpoints MUST verify the resource belongs to the authenticated tenant. It's easy to scope GET but forget to scope PATCH/PUT/DELETE because they were added later.

**Rule for future:**
- Every mutation endpoint (POST, PUT, PATCH, DELETE) must include tenant scoping
- Use the same `get_clone(slug)` dependency that read endpoints use
- Add `clone_id` to the database query filter, not just the URL path
- Audit all endpoints when adding multi-tenancy — check read AND write paths
- Test cross-tenant access: can tenant A modify tenant B's resources?

---

### Lesson 27: Embedding Dimension Mismatch — Wrapper Libraries Don't Auto-Truncate

**Date:** Session 26 | **Category:** RAG / Mem0

**What happened:** Mem0 cross-session memory silently failed since Session 4. `GoogleGenerativeAIEmbeddings` outputs 3072-dim vectors. Mem0's pgvector config sets `embedding_model_dims: 1024`. When Mem0 calls `embed_query()` → gets 3072 dims → INSERT into pgvector fails with dimension mismatch. The `memory_writer` node catches this in a bare `except Exception` and logs a warning, so it failed silently for 22 sessions.

**Root cause:** The ingestion pipeline (`embedder.py`) manually truncates via `[v[:1024] for v in embeddings]`, but `mem0_client.py` assumed Mem0's `embedding_dims: 1024` config would handle truncation. It doesn't — that config only tells pgvector what dimension to expect in the schema, not to truncate incoming vectors. Mem0's `LangchainEmbedding` wrapper calls `embed_query(text)` without passing `output_dimensionality`.

**Fix:** Created `TruncatedGoogleEmbeddings` subclass that overrides `embed_query()` and `embed_documents()` to truncate `[:1024]`. Passed this to Mem0 instead of raw `GoogleGenerativeAIEmbeddings`.

**Rule for future:**
- Never assume a library config field will auto-truncate or auto-transform data — read the library source
- When wrapping embeddings for a third-party library, verify what methods it calls and what dimensions it receives
- If a feature "works but produces no visible output", test it in isolation (not just via the full pipeline)
- Side-effect nodes with bare `except Exception` can hide critical bugs for months — consider logging at WARNING level minimum

---

### Lesson 28: LLM Self-Evaluation is Unreliable for Confidence Scoring

**Date:** Session 29 | **Category:** RAG pipeline / Confidence scoring

**What happened:** The `confidence_scorer` node asked the LLM to rate its own response quality (0.0-1.0). It consistently returned ~1.0 (or 0.85+ at minimum), even for responses built on completely irrelevant passages. The LLM had no calibration — it always thought its answer was great.

**Root cause:** LLMs are overconfident in self-evaluation (arXiv:2508.06225 reports 84%+ overconfidence). When given context and asked "how good is your response?", the LLM anchors on the fact that it produced coherent text, not on whether the context was actually relevant.

**Fix:** Replaced with deterministic 4-factor scoring (no LLM call):
- Retrieval confidence (0.35) — from reranker or cosine similarity
- Citation coverage (0.25) — fraction of passages actually cited
- Response grounding (0.25) — lexical overlap between response and context
- Passage count factor (0.15) — enough source material?

**Rule for future:**
- Never use LLM self-evaluation for binary/numeric quality judgments — it's systematically overconfident
- Deterministic scoring with multiple independent signals is more calibrated
- If you must use LLM for evaluation, use a DIFFERENT model than the one that generated the response

---

### Lesson 29: Paraphrased Queries Embed Identically — Reformulation Must Change Strategy

**Date:** Session 29 | **Category:** RAG pipeline / CRAG

**What happened:** The CRAG reformulator asked the LLM to "rephrase the query differently." The LLM generated paraphrases like "Explain ASEAN's future" → "What lies ahead for ASEAN?" These embed to nearly identical vectors and retrieve the exact same passages every retry. The CRAG loop ran 3 times but retrieved identical results each time.

**Root cause:** Vector embeddings capture semantic meaning, not surface form. Two sentences with the same meaning produce nearly identical embeddings regardless of wording. The reformulator was changing words without changing meaning.

**Fix:** Rewrote reformulator prompt to require different STRATEGIES, not different words:
1. Extract specific KEYWORDS and ENTITIES (BM25 search finds different results than vector)
2. DECOMPOSE into sub-topics
3. Use DOMAIN JARGON
4. Try the OPPOSITE angle
5. BROADEN or NARROW scope dramatically

Added BM25 hybrid search — keyword queries with different terms actually retrieve different passages.

**Rule for future:**
- Paraphrasing is useless for vector search reformulation — embeddings capture meaning, not words
- BM25 keyword search is the key complement — same meaning ≠ same keywords
- Show the reformulator what it already found (actual passage text + scores) so it can diagnose and pivot

---

### Lesson 30: Seed Data Must Use Real Embeddings — Random Vectors Break Pipeline Testing

**Date:** Session 30 | **Category:** Testing / Demo corpus

**What happened:** `seed_paragpt_corpus.py` used `np.random.randn(1024)` for demo embeddings. Every query returned ~7% reranker confidence because random vectors have no semantic relationship to any query. The FlashRank reranker correctly scored them as irrelevant, triggering hedges on every query. We couldn't test if the RAG pipeline actually worked.

**Root cause:** Random 1024-dim vectors have cosine similarity ~0.0 with any real query embedding. The reranker (cross-encoder) also scores random text-query pairs at ~7%. The pipeline was working perfectly — it was correctly identifying that the "retrieved" passages were nonsense.

**Fix:** Replaced `_random_embedding()` with `get_embedder().embed()` for real Gemini embeddings. Also added `search_vector` (tsvector) to the INSERT for BM25 support. After fix: ASEAN queries scored 77% confidence, chocolate cake queries scored 23%.

**Additional learning:** Profile config is loaded from the database (`clone.profile` JSONB), not from Python presets in `clone_profile.py`. Changing `confidence_threshold` in Python had no effect until we also ran an SQL UPDATE on the `clones` table.

**Rule for future:**
- Always use real embeddings for demo/test corpora — random vectors make the pipeline look broken when it's working perfectly
- When profile changes don't take effect, check if the value is loaded from DB (not Python code)
- Include `search_vector` (tsvector) in seed scripts for BM25 support
- Test with both relevant AND irrelevant queries to verify both answer and hedge paths

---

### Lesson 31: Multi-Turn Conversation — Three Compounding Bugs Disabled It Entirely

**Date:** Session 34 | **Category:** Architecture / Pipeline ordering / Frontend

**What happened:** Follow-up questions like "what that mean in context of india" (after asking about ASEAN) triggered the silence/hedge mechanism instead of building on conversation context. The system responded with "I don't have a specific teaching on that topic..." for every follow-up, across all models.

**Root causes (3 compounding bugs):**

1. **Frontend hard-coded "anonymous" user_id:** `App.tsx:61` passed `sendMessage(query, 'anonymous', ...)`. Then `context_nodes.py:163` explicitly returned empty history for `user_id == "anonymous"`. Result: conversation history was NEVER loaded for frontend users.

2. **Pipeline ordering:** `conversation_history` node ran AFTER retrieval and query analysis (`context_assembler -> conversation_history`). Even with a valid user_id, query analysis happened without conversation context, generating poor sub_queries.

3. **Query analysis was context-blind:** `query_analysis_node.py` only read `query_text`, never `conversation_history`. The LLM prompt had no awareness of prior conversation, so vague follow-ups like "what about India?" generated irrelevant sub_queries, dropping confidence below threshold.

**Additional bugs found during testing:**

4. **CLI script didn't save messages:** `ask_clone.py` never wrote messages to the DB, so `conversation_history_node` found nothing.

5. **Reranker used wrong query:** `vector_search.py` scored passages against raw `query_text` ("what that mean in context of india") instead of the rewritten sub_queries. Good ASEAN passages scored near-zero.

6. **Confidence scorer ignored conversation history:** `_compute_grounding_score` only checked `assembled_context`, not `conversation_history`. Follow-up responses mention terms from history that aren't in retrieved passages.

**Fixes (7 files changed):**
- Removed `== "anonymous"` guard in context_nodes.py
- Generated persistent UUID user_id via localStorage in App.tsx
- Reordered pipeline: conversation_history -> query_analysis (not after context_assembler)
- Made query_analysis context-aware with follow-up detection and query rewriting
- Added message DB persistence to CLI script
- Changed reranker to use longest sub_query for scoring
- Added conversation_history to grounding score + multi-turn confidence bonus (+0.10)

**Rule for future:**
- Pipeline node ordering matters hugely. Nodes that provide context to other nodes must run FIRST
- Never hard-code sentinel values ("anonymous") as guards. Use proper empty/null checks
- When testing multi-turn conversation, verify messages are actually persisted to DB between turns
- Reranking/scoring must use the BEST AVAILABLE query (rewritten), not the raw user input
- Test multi-turn with at least 3-4 sequential turns, including one very vague follow-up

---

### Lesson 32: Conditional Edge Ordering — review_required Must Not Short-Circuit Silence

**Date:** Session 34 (continued) | **Category:** LangGraph / Routing logic

**What happened:** All 3 Sacred Archive tests showed `Silence: False` despite confidence (0.00-0.50) being well below the 0.95 strict_silence threshold. Sacred Archive was never silencing low-confidence responses.

**Root cause:** In `conversation_flow.py:after_confidence()`, the routing logic checked `profile.review_required` BEFORE the confidence threshold:

```python
# BROKEN: review_required checked FIRST
if profile.review_required:           # Always True for Sacred Archive
    return "review_queue_writer"      # Skips confidence check entirely
if final_confidence >= profile.confidence_threshold:  # Never reached
    return "stream_to_user"
```

Since Sacred Archive has `review_required=True`, EVERY response went straight to `review_queue_writer`, bypassing both the confidence check and the `strict_silence_router`. The silence mechanism was completely disabled for Sacred Archive since Session 17 (when `review_required` was added).

**Fix:** Reorder so confidence is checked first. Low-confidence responses route to silence handler, which then routes to review queue via its own `after_strict_silence` conditional edge (which already existed and already checked `review_required`):

```python
# FIXED: confidence checked FIRST
if final_confidence >= profile.confidence_threshold:
    if profile.review_required:
        return "review_queue_writer"
    return "stream_to_user"
# Low confidence → silence handler
```

**Rule for future:**
- In conditional routing with multiple concerns (confidence, review, silence), never let an administrative flag (review_required) short-circuit a safety check (confidence threshold)
- When adding new routing conditions, trace ALL possible paths through the graph for EACH client profile
- Test the complete matrix: {high confidence, low confidence} x {review_required, not required} x {soft_hedge, strict_silence}

---

### Lesson 33: LangGraph TypedDict Drops Undeclared State Keys

**Date:** Session 35 | **Category:** LangGraph / State management

**What happened:** `model_override` was set in `build_initial_state()` (in `chat.py`) and passed to `graph.invoke()`, but by the time it reached the first LLM-calling node, it was gone. All 4 LLM nodes saw `state.get("model_override")` as `None`, ignoring the per-request model selection.

**Root cause:** LangGraph's `StateGraph` uses the `TypedDict` class as its state schema. During state propagation between nodes, LangGraph validates the state against the TypedDict and **silently drops any key not declared in the TypedDict**. `model_override` was being set correctly at init but wasn't declared in `ConversationState`, so LangGraph discarded it at the first edge.

**Fix:** Added `model_override: str` to the `ConversationState` TypedDict in `conversation_flow.py`.

**Rule for future:**
- Every new state key MUST be declared in the TypedDict — LangGraph silently drops undeclared keys
- Test by inspecting state AFTER the first node (not just at init) to verify keys survive propagation
- If a state key "mysteriously disappears" between nodes, check the TypedDict first

---

### Lesson 34: OpenRouter max_tokens Credit Reservation

**Date:** Session 35 | **Category:** LLM provider / Billing

**What happened:** After switching from Groq to OpenRouter, the pipeline returned 402 errors: "This request requires more credits. You requested up to 65536 tokens, but can only afford 31329."

**Root cause:** OpenRouter **reserves** `max_tokens` against your credit balance before processing. When `max_tokens=None`, the LangChain ChatOpenAI client doesn't send it, and OpenRouter defaults to the model's full context window (e.g., 65K for Llama 3.3). Even a simple "hello" query would try to reserve 65K tokens worth of credits. Groq didn't have this behavior because it's a flat-rate API.

**Fix:** Default `max_tokens=2048` in `get_llm()` when not explicitly specified. This is enough for all pipeline use cases (query analysis ~100 tokens, generation ~500 tokens, reformulation ~200 tokens).

**Rule for future:**
- Always set explicit `max_tokens` for pay-per-token providers (OpenRouter, OpenAI, Anthropic API)
- `None`/unlimited is only safe for flat-rate APIs (Groq, local inference)
- Check provider billing docs when switching — credit reservation behavior varies

---

### Lesson 35: LangChain model_kwargs vs extra_body — Provider-Specific Params

**Date:** Session 35 | **Category:** LangChain / LLM integration

**What happened:** Qwen3.5-35B-A3B on OpenRouter burned 1,268 reasoning tokens on internal `<think>` reasoning per call, causing timeouts. The fix (`reasoning={"effort": "none"}`) worked via direct HTTP but broke when passed through LangChain's `model_kwargs`.

**Root cause:** LangChain's `ChatOpenAI` inspects `model_kwargs` for known keys. When it sees `reasoning`, it interprets it as an instruction to use structured content blocks and converts `response.content` from a plain `str` to a `list[dict]` like `[{"type": "text", "text": "..."}]`. The entire pipeline (citation verifier, confidence scorer, etc.) expected `str` content and broke.

**Fix:** Use `extra_body={"reasoning": {"effort": "none"}}` instead of `model_kwargs`. `extra_body` passes parameters directly in the HTTP request body without LangChain interpreting them. The response comes back as a normal `str`.

**Rule for future:**
- `model_kwargs` → params that LangChain knows about (temperature, top_p, etc.) — LangChain may interpret them
- `extra_body` → params that bypass LangChain entirely — sent raw in HTTP body
- For provider-specific features (thinking suppression, response format overrides), prefer `extra_body`
- Verify `type(response.content)` after switching — should be `str`, not `list`
- Different providers use different suppression methods: Groq uses `reasoning_effort` (top-level param), OpenRouter uses `reasoning.effort` (extra_body)

---

## Session Patterns to Remember

1. **User is learning by building** — every spec/decision should explain the why, not just the what
2. **Teaching mode applies** — simple language, no jargon without context, explain tradeoffs
3. **CLAUDE.md is the law** — plan mode, subagents for research, lessons captured, verification before done
4. **Folder structure matters** — build/, tasks/, open-questions/ as persistent workspaces
5. **No code in specs** — specs drive implementation, not the other way around
6. **Config objects need clean serialization** — use `str, Enum` for JSON portability
7. **Cross-field validation is crucial** — `@model_validator` catches business logic errors
8. **Conditional routing is the secret** — LangGraph closures over config + conditional edges = unified codebase
9. **Stubs with correct state unblock integration** — build the orchestration layer first, fill in implementations later
10. **Factory pattern powers profile-aware nodes** — closures let nodes access config without state bloat
11. **Real LLM integration requires graceful fallbacks** — API keys in `.env`, JSON parsing with sensible defaults
12. **Environment dependency pinning matters** — pip can silently downgrade packages; verify after install
13. **Mock path resolution: patch at source, not import site** — for lazy imports, patch where function is defined
14. **E2E test fixtures must respect profile thresholds** — confidence thresholds differ per profile
15. **Reasoning mode control varies by backend** — Groq uses `reasoning_effort`, OpenRouter uses `reasoning.effort` via `extra_body`, vLLM/SGLang use `enable_thinking`
16. **Spec compliance: verify implementation against original spec** — drift happens during incremental development. Check spec when questions arise. Spec is source of truth, not implementation.
17. **Sync code in async framework doesn't require full async rewrite** — FastAPI supports sync dependencies. Measure first (if <100ms, use sync directly). Only use async wrappers if operations are slow.
18. **FastAPI testing with async fixtures and dependency overrides** — Use httpx.AsyncClient(transport=ASGITransport), override dependencies globally, mock flexible models with side_effect dispatchers. Always restore original side_effect to avoid recursion.
19. **Mem0 langchain provider uses `model` key, not `langchain_embeddings`** — Mem0's `BaseEmbedderConfig.__init__()` accepts `model: Optional[str]` which the `LangchainEmbedding` class duck-types to accept a LangChain `Embeddings` instance. The config dict keys must match `BaseEmbedderConfig` constructor params exactly since `EmbedderFactory.create()` unpacks them as `BaseEmbedderConfig(**config)`. Always read the library source to confirm parameter names.
20. **DATABASE_URL format: SQLAlchemy vs psycopg** — `+psycopg` dialect prefix works for SQLAlchemy but fails for raw psycopg. Strip it when passing to pipeline/indexer.
21. **Always `python3 -m alembic` not bare `alembic`** — system wrappers may strip site-packages via shebang flags (-sP).
22. **True semantic chunking requires embedding-based similarity** — fixed-size with paragraph boundaries is NOT semantic chunking. Use SemanticChunker + embeddings for topic-boundary detection.
23. **Silence mechanism: overwrite ALL response fields** — `raw_response` AND `verified_response` must both be set when hedging. Downstream consumers read `verified_response` first.
24. **SQL parameterization is non-negotiable** — even when inputs come from trusted DB. Use `= ANY(%s)` not `IN ({interpolated})`. Defense-in-depth prevents future vulnerabilities.
25. **Sanitize uploaded filenames** — always `Path(filename).name` to strip directory traversal. Never trust `file.filename` from multipart uploads.
26. **Multi-tenant mutation endpoints need clone-scoping** — every PATCH/PUT/DELETE must verify `clone_id` matches the authenticated tenant. Easy to scope reads but forget writes.
27. **Embedding dimension mismatch hides in silent failures** — wrapper libraries (Mem0) don't auto-truncate embeddings. Config fields like `embedding_dims` only declare schema, not transform data. Always verify what the library actually does with your embeddings.
28. **LLM self-evaluation is systematically overconfident** — always returns ~1.0 for confidence scoring. Use deterministic multi-factor scoring instead (retrieval score + citation coverage + grounding + passage count). No LLM call = faster + calibrated.
29. **Paraphrased queries embed identically** — reformulating via paraphrases doesn't change vector search results. Use keyword extraction, sub-topic decomposition, domain jargon, and BM25 hybrid search to actually retrieve different passages.
30. **Seed data with random embeddings breaks pipeline testing** — use real embeddings for demo corpora. Also: profile config loads from DB (not Python preset), so changes require DB UPDATE. Always test both relevant and irrelevant queries.
31. **Multi-turn conversation: 3 compounding bugs** — hard-coded "anonymous" user_id, pipeline ordering (history after analysis), context-blind query analysis. Fix all three for follow-ups to work.
32. **Conditional edge ordering: safety before admin flags** — `review_required` must not short-circuit `confidence_threshold` check. Check confidence FIRST, then decide review vs silence.
33. **LangGraph TypedDict drops undeclared keys** — every state key must be declared in TypedDict. Undeclared keys silently disappear between nodes.
34. **OpenRouter max_tokens credit reservation** — always set explicit max_tokens for pay-per-token providers. None reserves full context window worth of credits.
35. **LangChain model_kwargs vs extra_body** — use `extra_body` for provider-specific params (thinking suppression). `model_kwargs` gets intercepted by LangChain, changing response format.
36. **CRAG retry loop degrades confidence** — 4 inter-related bugs: (1) passage replacement instead of accumulation discards good results, (2) reranker scores collapse when query drifts from reformulation, (3) multiplication in CRAG evaluator amplifies degradation, (4) using the same threshold for CRAG retries and final silencing triggers futile retries at 52% that spiral to 0%. Fix: accumulate+deduplicate passages across retries, re-rerank merged set against original query_text, use separate lower threshold (min(threshold*0.5, 0.40)) for CRAG retries, cap retries at 2.
37. **Confidence and passages can decouple** (see below)
38. **Doc-code drift on thresholds and retries** — Session 41 Q&A audit found 16+ files with outdated values: (1) "3 retries" in 3 docs (actual: 2 since S34), (2) ParaGPT threshold "0.80" in 15+ places (factory default is 0.80 but DB runtime value is 0.60 since S35), (3) CRAG retry threshold comment said "< 40%" but actual ParaGPT value is 0.30 (0.60 × 0.5), (4) "3-4 LLM calls" (actual: 3 typical, 5 worst case). **Rule:** When tuning a runtime value (DB override), grep all docs for the old value and annotate "factory default X, DB override Y". Keep SOW spec values unchanged but add runtime notes.
37. **Confidence and passages can decouple** — 6 bugs where valid passages get 0.0 confidence: (1) empty reranked list after reranker scores all passages low, (2) re-rerank block skipped or throws exception but confidence not recalculated, (3) LLM returns `{"alternatives": []}` bypassing default, (4) CRAG evaluator multiplies zero raw_confidence by passage_factor = still zero, (5) stale retry_count from previous query blocks CRAG retries, (6) search_meta not initialized in state. Root cause: confidence tracked separately from passage existence. Fix: add 0.15 floor when passages exist but scores unavailable, recalculate confidence in all fallback paths, use `or` instead of default param for alternatives, add base floor in evaluator when raw_confidence=0 but passages present, reset retry_count in query_analysis, initialize search_meta.

---

### Lesson 39: Test identity (`is`) vs equality for evolving return values
**What happened:** Session 16 tests used `assert result is state` for review_queue_writer.
Session 40 changed the function to return `{**state, "review_id": review_id}` — a new dict.
Tests passed for 4 sessions before being caught in S42.

**The pattern:** When a function evolves from returning its input unchanged to returning a modified
copy, identity assertions (`is`) break silently in downstream tests.

**Rule for future:**
- Use `assert result["key"] == expected` (equality) not `assert result is state` (identity)
- When adding new return fields to a node, grep tests for `result is state` on that function
- Pre-existing test failures must be investigated immediately, not carried forward

---

### Lesson 40: Externalize Persona and Behavioral Rules into Markdown Files

**Date:** Session 43 | **Category:** Architecture / Prompt engineering

**What happened:** Clone persona and behavioral constraints were defined as inline Python strings inside `clone_profile.py` factory functions and `registry.py` prompt templates. When rules needed updating (e.g., adding citation guidelines), changes required editing Python code, restarting the server, and understanding string escaping. The same rule sometimes appeared in both the profile factory and the prompt template, creating two sources of truth that drifted apart.

**Fix:** Created `profiles/{client}/soul.md` (identity) and `profiles/{client}/guardrails.md` (behavioral constraints) as standalone markdown files. Added `CloneProfile.guardrails_document` field and `load_profile_markdown()` helper. Factory functions read from markdown at build time. Prompt registry accepts external documents as parameters.

**Rule for future:**
- Persona identity and behavioral rules belong in markdown files, not inline Python strings
- One file per concern (soul = who you are, guardrails = how you behave)
- When rules appear in 2+ places, extract to a single source and inject at all consumption points
- Non-engineers should be able to edit persona and guardrails without touching Python code

---

### Lesson 41: Template-Guardrails Duplication — Lean Templates, External Rules

**Date:** Session 45 | **Category:** Prompt engineering / Maintenance

**What happened:** After Session 43 externalized guardrails into markdown files, the generation prompt template in `registry.py` still contained inline citation rules, persona consistency rules, and a 4-category intent description. Session 44 changed intent classes from 6 to binary (persona|retrieval), but the template's inline rules still referenced the old 4-category system. This created contradictions: guardrails Section 3 used "persona" and "retrieval" (correct) while the template body described "conversational", "factual", "synthesis", and "exploratory" (stale).

**Fix:** Stripped the prompt template down to ~120 tokens: identity line (`You are {display_name}`), persona document block, guardrails document block, and a current-mode instruction (persona vs retrieval). ALL behavioral rules (citation style, response formatting, hedge language, memory behavior) now live exclusively in the external markdown files.

**Rule for future:**
- When building system prompts from external documents, the template should contain ONLY identity + mode instruction
- All behavioral rules belong in the external documents — duplicating them in the template creates maintenance burden
- After changing a classification taxonomy (e.g., 6 → 2 intent classes), grep ALL files that reference the old taxonomy — including prompt templates, guardrails, and test assertions
- Template size is a smell: if your template is >200 tokens, you're probably duplicating rules that belong in an external document

---

### Lesson 42: DB-Loaded Config Must Hydrate from Source-of-Truth Files

**Date:** Session 46 | **Category:** Architecture / Data loading

**What happened:** ParaGPT fabricated biographical details ("grew up primarily in the United States") instead of using facts from `profiles/paragpt-client/soul.md` ("grew up across the UAE, then moved to Queens, New York as a teenager"). The `persona_document` and `guardrails_document` fields were added to `CloneProfile` in Session 43 with `default=""`. The factory function loads from disk correctly, but at runtime the profile is reconstructed from the DB JSONB column (`CloneProfile(**clone_row.profile)`). The DB was seeded before S43, so the JSONB doesn't contain these keys — Pydantic silently uses the empty default. The LLM gets no biographical facts and hallucinates from training data.

**Fix:** Added `@model_validator(mode="after")` called `hydrate_markdown_documents` that loads `soul.md` and `guardrails.md` from disk every time a `CloneProfile` is constructed. Markdown files are the permanent runtime source of truth — no more DB drift. Unknown slugs without profile directories gracefully keep DB/default values.

**Rule for future:**
- When config has both a source of truth (files on disk) and a persistent store (DB JSONB), the persistent store will drift
- Adding new fields with defaults means old DB rows silently use defaults instead of the source of truth
- Fix with `model_validator` that always hydrates from the canonical source
- File reads are <1ms each (OS page cache), negligible vs LLM latency
