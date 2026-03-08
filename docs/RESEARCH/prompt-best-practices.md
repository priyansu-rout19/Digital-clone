# LangGraph Node System Prompts: Best Practices for Quality, Consistency & Performance

*Research date: 2026-03-08*
*Stack: FastAPI + LangGraph + OpenRouter + PostgreSQL*

---

## The Short Answer

Your prompt architecture is already well-structured (5 focused prompts, centralized registry, profile-driven behavior). The biggest wins now are: (1) enable OpenRouter's automatic prompt caching for free latency/cost savings, (2) add JSON schemas to structured-output prompts for 99%+ parse reliability, and (3) add 1-2 few-shot examples only to the query classifier (the node most likely to misclassify). Don't over-engineer — your 2-client system doesn't need a prompt management platform.

---

## Why This Approach

After researching what production LangGraph teams actually do (not just what blog posts recommend), the pattern is clear: **keep prompts focused and task-specific, let the graph encode the workflow logic, and invest in caching + structured output rather than prompt complexity.**

Your system already follows this pattern — 5 small prompts (~2,050 tokens total) doing one job each. The research confirms this is the right call. Teams that stuff everything into a single system prompt pay 20,000+ extra tokens per request and get worse results.

The gains from here are incremental optimizations, not architectural changes.

---

## The Alternatives (and why we're not using them)

| Approach | Why Not For Us |
|----------|---------------|
| **Prompt management platforms** (Langfuse, PromptLayer, Braintrust) | Overkill for 5 prompts and 2 clients. Worth revisiting at 20+ prompts or when A/B testing becomes a priority |
| **Dynamic skill loading** (SKILL.md files loaded per request) | Solves the "50 skills bloating the system prompt" problem. We have 5 prompts, not 50 |
| **Few-shot examples in every node** | Adds ~500-2000 tokens per node per request. Only justified for the query classifier where intent misclassification is most impactful |
| **Database-stored prompts** | Adds latency (DB read per request) and complexity. Python constants in registry.py are simpler and faster for our scale |
| **Prompt chaining with LLM-as-judge** | Useful for complex agentic workflows. Our pipeline is fixed (not agentic), so the graph structure itself handles the chain |

---

## How to Implement in Our Stack

### Quick Win 1: OpenRouter Prompt Caching (Free, Zero Code Changes)

OpenRouter **automatically caches** prompt prefixes. No config needed. When the same system prompt tokens appear at the start of consecutive requests, OpenRouter reuses the cached KV state.

**What this means for us:**
- Our 5 system prompts are static (same text every request, except `interpretive_generator_prompt` which varies by clone)
- The `QUERY_CLASSIFIER_PROMPT` (~700 tokens) and `CRAG_REFORMULATOR_PROMPT` (~500 tokens) are identical across ALL requests — perfect cache candidates
- Cached reads cost **0.25x** of input token price (OpenAI models) or free (some providers)
- **Estimated savings:** ~10-15% on input token costs with zero effort

**One thing to watch:** Cache hits require the *exact same token prefix*. If you change a single character in the system prompt, the cache misses. This is another reason to keep prompts in `registry.py` as constants rather than building them dynamically.

**Source:** https://openrouter.ai/docs/guides/best-practices/prompt-caching

---

### Quick Win 2: JSON Schemas in Structured-Output Prompts

**Problem:** Your query classifier and CRAG reformulator instruct the model to "Return JSON only" — but the model sometimes wraps it in markdown code fences or adds commentary. You already handle this with stripping logic, but it's a reliability band-aid.

**Fix:** Add an explicit JSON schema definition to the prompt. Research shows this pushes parse reliability from ~85% to 99%+.

**Where to apply (in `core/prompts/registry.py`):**

For `QUERY_CLASSIFIER_PROMPT`, add after the current JSON example:

```
JSON Schema:
{
  "intent": string (one of: "factual", "synthesis", "opinion", "temporal", "exploratory"),
  "sub_queries": string[] (1-5 search queries),
  "token_budget": integer (range: 1000-4000),
  "response_tokens": integer (range: 100-1000),
  "rewritten_query": string | null
}
```

For `CRAG_REFORMULATOR_PROMPT`, add:

```
JSON Schema:
{
  "alternatives": string[] (exactly 3 search queries using different strategies)
}
```

**Why this works:** When the model sees a formal schema, it constrains its output generation to match. The schema acts as a "type annotation" for the LLM's output.

**Source:** https://medium.com/@vishal.dutt.data.architect/structured-prompting-with-json-the-engineering-path-to-reliable-llms-2c0cb1b767cf

---

### Quick Win 3: Few-Shot Example for Query Classifier Only

The query classifier is the node most likely to make mistakes (intent misclassification, bad follow-up rewriting). Adding 1-2 examples dramatically improves accuracy.

**Where:** Add to `QUERY_CLASSIFIER_PROMPT` in `registry.py`, after the schema definition:

```
Example 1 (standalone factual):
User: "What is ASEAN's role in global trade?"
Output: {"intent": "factual", "sub_queries": ["ASEAN role global trade"], "token_budget": 2000, "response_tokens": 400, "rewritten_query": null}

Example 2 (follow-up):
History: "User: What is ASEAN's role in global trade?\nAssistant: ASEAN plays a central role..."
User: "How does India fit into that?"
Output: {"intent": "synthesis", "sub_queries": ["ASEAN global trade integration", "India ASEAN trade relationship"], "token_budget": 2500, "response_tokens": 500, "rewritten_query": "How does India fit into ASEAN's role in global trade?"}
```

**Why only the classifier:** It's the disambiguation node — getting intent wrong cascades through the entire pipeline (wrong token budget, wrong retrieval strategy). Other nodes (generation, CRAG) have clearer tasks that don't benefit as much from examples.

**Token cost:** ~200 extra tokens per request. Acceptable given 3 LLM calls per typical query (query_analysis + generation + sentence splitter; up to 5 with 2 CRAG retries) averaging ~2000 tokens each.

---

### Medium-Term: Cap Output Tokens on Intermediate Nodes

Your intermediate nodes (query_reformulator, sentence_splitter) don't need 2048 max_tokens. Capping them reduces cost:

| Node | Current max_tokens | Suggested | Reasoning |
|------|-------------------|-----------|-----------|
| query_analysis | default (2048) | 512 | JSON output is ~100-200 tokens max |
| query_reformulator | default (2048) | 512 | JSON with 3 queries is ~100 tokens |
| sentence_splitter | default (2048) | match input | Output length = input length |
| in_persona_generator | LLM-estimated (100-1000) | Keep as-is | Already dynamic, well-calibrated |

**Impact:** ~20% token reduction on intermediate calls. These nodes run 1-3x per query.

**Where to change:** In each node file where `get_llm()` is called, pass `max_tokens=512` for classification/reformulation nodes.

---

### Medium-Term: Semantic Caching for Repeat Queries

If users frequently ask similar questions (e.g., "What is ASEAN?" and "Tell me about ASEAN"), a semantic cache can return previous answers without running the full pipeline.

**How it works:**
1. Embed the incoming query
2. Check cache for similar embeddings (cosine similarity > 0.95)
3. If hit: return cached response (skip entire pipeline)
4. If miss: run pipeline, cache result

**Implementation:** Redis + pgvector (you already have pgvector). Store `(query_embedding, clone_id, response, cited_sources, timestamp)` with a TTL.

**When to do this:** Only after you see repeat query patterns in production logs. Premature caching adds complexity without proven benefit.

---

## Watch Out For

1. **Prompt caching breaks on dynamic prefixes.** If your system prompt changes per-request (e.g., injecting user memory into the system message), caching won't work. Keep dynamic content in the *user message*, not the system prompt. Your current architecture already does this correctly.

2. **Few-shot examples can cause overfitting.** If your examples all use ASEAN queries, the model may anchor on ASEAN for all classification. Use examples from different domains.

3. **JSON mode vs. JSON instructions.** Some providers offer a `response_format: json_object` parameter that enforces valid JSON at the decoding level. OpenRouter passes this through to supporting models. However, this forces the ENTIRE response to be JSON — bad for generation nodes that produce prose. Only use it for classification nodes.

4. **Don't optimize for token cost before you have usage data.** You're pre-launch. Optimize for correctness first, cost second. The quick wins above are free or near-free. The bigger optimizations (semantic caching, output capping) should wait until you see real usage patterns.

5. **Prompt versioning discipline.** Now that prompts live in `registry.py`, every change should bump the version comment (`# v2 — 2026-03-15: added JSON schema`). This makes `git log -p core/prompts/registry.py` a complete changelog.

---

## If You Want to Go Deeper

1. **OpenRouter Prompt Caching Docs** — How automatic caching works, per-provider behavior
   https://openrouter.ai/docs/guides/best-practices/prompt-caching

2. **Structured Prompting with JSON (Engineering Guide)** — Why schemas beat "return JSON" instructions, with benchmarks
   https://medium.com/@vishal.dutt.data.architect/structured-prompting-with-json-the-engineering-path-to-reliable-llms-2c0cb1b767cf

3. **Stop Stuffing Your System Prompt (LangGraph Skills Pattern)** — The modular skill loading pattern for when you outgrow 5 prompts
   https://pessini.medium.com/stop-stuffing-your-system-prompt-build-scalable-agent-skills-in-langgraph-a9856378e8f6

4. **Langfuse A/B Testing for Prompts** — When you're ready to test prompt variants systematically
   https://langfuse.com/docs/prompt-management/features/a-b-testing

5. **Prompt Compression for Cost Reduction** — Advanced techniques for reducing token usage without quality loss
   https://machinelearningmastery.com/prompt-compression-for-llm-generation-optimization-and-cost-reduction/

---

## Open Questions

1. **Does OpenRouter's caching work with our Qwen3 model?** The docs confirm OpenAI and Gemini models support it. Need to verify Qwen3 on OpenRouter specifically.

2. **Should we use `response_format: json_object` for classification nodes?** This is a provider-level enforcement. Need to test if OpenRouter + Qwen3 supports it.

3. **When to add A/B testing?** Currently low priority (pre-launch), but worth tracking as an open question for post-launch iteration.

*These could be added to `open-questions/INDEX.md` if we want to track them formally.*
