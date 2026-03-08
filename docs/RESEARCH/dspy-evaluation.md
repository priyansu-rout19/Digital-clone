# Do We Need DSPy for the Digital Clone Engine?

*Research date: 2026-03-08*
*Stack: FastAPI + LangGraph + OpenRouter + PostgreSQL*

---

## The Short Answer

**No, not right now.** Your system has 5 hand-tuned prompts that work, a small eval dataset (50+30 queries), and you're pre-launch. DSPy shines when you have 500+ labeled examples and measurable performance gaps to close. Add it later when production data reveals which prompts actually need optimization — don't optimize blind.

---

## Why This Approach

DSPy is a **prompt compiler** — it takes your pipeline, runs many LLM calls to find better prompts, and returns optimized versions. Sounds great. But here's the reality check for *your* project:

1. **You have 5 prompts, not 50.** DSPy's ROI scales with pipeline complexity. With 5 hand-tuned prompts in a well-structured registry, you can iterate manually in minutes. DSPy adds dependency complexity for marginal gains.

2. **Your eval dataset is too small.** DSPy needs labeled data to optimize against. Your 50-query eval suite + 30-query foundation gate = 80 examples. DSPy needs 200+ to learn reliably, and 500+ to generalize. With 80, it'll overfit to your test distribution.

3. **You're pre-launch.** You don't know which prompts are the bottleneck yet. Maybe the query classifier is perfect but the generation prompt needs work. Or vice versa. Running DSPy now is optimizing without a target — you'll burn API credits ($500-1000) and time (3-4 days) without knowing if you're fixing the right thing.

4. **PCCI deployment blocks it anyway.** Your production target is SGLang on sovereign PCCI infrastructure — no external API calls. DSPy's optimization runs require many LLM calls during compilation. On PCCI, this burns local GPU time. Better to wait until the infra is ready.

5. **Your prompts just got better.** We just added JSON schemas and few-shot examples (v2 prompts). These are the same techniques DSPy would discover — you did it manually in 10 minutes instead of running a 2-hour optimization loop.

---

## The Alternatives (and why we're not using them)

| Approach | Why Not For Us |
|----------|---------------|
| **DSPy (full integration)** | Too early — small dataset, pre-launch, unclear bottlenecks. Revisit with production data |
| **DSPy (pilot on 1 node)** | Tempting, but even a pilot needs 200+ labeled examples to beat hand-tuning. We have 80 |
| **TextGrad** | "Autograd for text" — refines outputs at inference time. Adds latency per request. Wrong tradeoff for a chat system |
| **GEPA** | Newer (July 2025), more sample-efficient than DSPy. Worth watching but too bleeding-edge for production |
| **Arize Prompt Learning** | Simpler feedback loops. Lower bar than DSPy but still needs production data we don't have |
| **Hand-tune + eval loop (current)** | This is what we should keep doing. Edit prompts in registry.py, run eval suite, measure, repeat |

---

## How to Implement in Our Stack (When the Time Comes)

If you revisit DSPy after launch (500+ production queries logged), here's the integration path:

**Phase 1 — Query Classifier (lowest risk, highest clarity)**
```python
# DSPy signature for query classification
class QueryClassifier(dspy.Signature):
    """Classify user query intent and decompose into sub-queries."""
    query_text: str = dspy.InputField()
    conversation_history: str = dspy.InputField(default="")
    intent: str = dspy.OutputField(desc="one of: factual, synthesis, opinion, temporal, exploratory")
    sub_queries: list[str] = dspy.OutputField()
    token_budget: int = dspy.OutputField()
    response_tokens: int = dspy.OutputField()
    rewritten_query: str = dspy.OutputField(default=None)
```

- Use `dspy.LM(model="openrouter/qwen/...", api_key=...)` for OpenRouter compatibility
- Train on production query logs (intent labels from your deterministic scorer)
- Metric: intent_accuracy + token_budget_error (MAE)
- Replace `QUERY_CLASSIFIER_PROMPT` in registry.py with DSPy-compiled prompt

**Phase 2 — CRAG Reformulator (medium risk)**
- Signature: `(query_text, failure_diagnosis) -> alternative_queries`
- Metric: % of reformulations that improve retrieval_confidence
- Training data: CRAG retry logs (queries that failed + what eventually worked)

**Phase 3 — Generation (high risk, do last)**
- Dual signatures: interpretive vs mirror_only
- Metric: persona_fidelity + citation_coverage (multi-objective)
- Warning: DSPy may rewrite your carefully tuned persona prompt in ways that sound different. Needs heavy validation.

**Integration point:** DSPy modules live *inside* LangGraph nodes. LangGraph handles routing/state, DSPy handles prompt optimization. They complement, don't conflict.

---

## Watch Out For

1. **Model-specific optimization.** A prompt DSPy optimizes for Qwen3 may not work well on GPT-4 or Claude. When you switch models (OpenRouter today → SGLang on PCCI tomorrow), you'd need to re-optimize. That's wasted work if you do it now.

2. **Black box rewriting.** DSPy can't explain *why* it changed your prompt. If the optimized prompt breaks Sacred Archive's strict quoting rules, debugging is hard. Always validate against your foundation gate.

3. **Context overflow.** DSPy adds few-shot examples during compilation. If your system prompt + few-shots + user message exceeds the model's context window, it fails silently. Your prompts are already ~700 tokens for the classifier — adding 5-10 few-shot examples could push past limits on smaller models.

4. **Cost during optimization.** Each DSPy compilation run calls the LLM dozens to hundreds of times. At OpenRouter rates, optimizing all 3 nodes = ~$500-1000. Not terrible, but not free — and you'd redo it every time you change models or significantly update the corpus.

5. **False confidence.** DSPy can show "95% accuracy on eval set" while overfitting to your 80 test queries. The real test is production queries you haven't seen yet.

---

## If You Want to Go Deeper

1. **DSPy Official Tutorial — RAG Pipeline**
   https://dspy.ai/tutorials/rag/
   *Shows exactly how to build a DSPy-optimized RAG system. Compare with your current LangGraph pipeline.*

2. **DSPy vs Hand-Tuned Prompts — When to Use Which**
   https://www.statsig.com/perspectives/dspy-vs-prompt-tuning
   *Honest comparison. Key takeaway: DSPy wins at scale (many components, many examples), hand-tuning wins for small focused systems.*

3. **LangGraph + DSPy Integration Pattern**
   https://medium.com/@akankshasinha247/langgraph-dspy-orchestrating-multi-agent-ai-workflows-declarative-prompting-93b2bd06e995
   *Shows the architecture: LangGraph for orchestration, DSPy for prompt optimization inside nodes.*

---

## Open Questions

1. **When is the right trigger to revisit DSPy?** Suggested trigger: when you have 500+ production query logs AND a specific metric (citation accuracy, persona fidelity, CRAG success rate) is below target.

2. **Does DSPy work with SGLang on PCCI?** DSPy supports any OpenAI-compatible endpoint via LiteLLM. SGLang exposes one. Should work, but untested.

3. **Could we use DSPy's eval framework without its optimizer?** DSPy has good evaluation tooling separate from compilation. Might be useful even without the full optimization loop.

*Consider adding these to `open-questions/INDEX.md` if the team wants to track them.*
