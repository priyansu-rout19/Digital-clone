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

When mocking retrieval, the mock value must account for the profile's threshold. Sacred Archive's 0.95 threshold requires mock value >= 0.95. ParaGPT's 0.80 threshold is satisfied by 0.85.

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
15. **Reasoning mode control varies by backend** — Groq uses `reasoning_effort`, vLLM/SGLang use `enable_thinking`, same problem different solutions
16. **Spec compliance: verify implementation against original spec** — drift happens during incremental development. Check spec when questions arise. Spec is source of truth, not implementation.
17. **Sync code in async framework doesn't require full async rewrite** — FastAPI supports sync dependencies. Measure first (if <100ms, use sync directly). Only use async wrappers if operations are slow.
