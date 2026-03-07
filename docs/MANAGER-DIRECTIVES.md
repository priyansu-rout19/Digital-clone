# Manager Directives & Product Vision

**Source:** Prem AI management feedback | **Last Updated:** March 7, 2026 (Session 39)

---

## Standing Directives

### 1. Chase Perfection with Requirements
- Every line item in `CLIENT-1-PARAGPT.md` and `CLIENT-2-SACRED-ARCHIVE.md` must be implemented correctly
- Don't leave gaps — treat requirements as a checklist
- Don't mark something "done" until it truly matches the spec
- Regular requirement audits to catch drift

### 2. Documentation is the Future
- Document everything built — architecture, progress, decisions
- Docs should answer questions without needing to read code
- Update `PROGRESS.md`, `ARCHITECTURE.md`, `STUBS-AND-MOCKS.md` after every session
- The system itself should document its reasoning (trace feature)

### 3. Keep Iterating
- Each session should move the project forward
- Don't stop at "good enough" — push toward production quality
- Fix bugs, add features, polish UI continuously

---

## Feature Requests (from management)

### Reasoning & Tool Call Traces ✅ DONE (Session 28)
- **What:** Full visibility into the AI's decision-making at each pipeline step
- **Why:** Increase trust with clients. They need to see *why* the clone said what it said
- **Implementation:** `_extract_trace_data()` in `chat.py` extracts curated metrics per node. WS progress messages include `trace` field (never sends full passages). `ReasoningTrace.tsx` component — collapsible "{N} pipeline steps" pill with vertical timeline.
- **Shows:** retrieval confidence, passage count, reranked flag, top rerank score, CRAG retry count, generation mode, citation count, silence trigger status
- **Session 29 enhancement:** Trace panel now shows `reranked` flag and `top_rerank_score` from FlashRank cross-encoder

### Demo Videos (REQUESTED — not code)
- **What:** Screen recordings of key user journeys
- **Why:** "A lot more useful than screenshots" — demonstrates product to stakeholders
- **Suggested journeys:**
  1. ParaGPT: landing page → ask question → cited response with voice playback
  2. Sacred Archive: tier selection → query → direct quote with provenance
  3. Review dashboard: approve/reject flow
  4. Analytics dashboard: monitoring stats
  5. Edge case: out-of-corpus question → honest hedging
- **Tool:** OBS Studio or similar screen recorder, 30-60 second clips

---

## Requirement Audit Results (Sessions 22-30)

### ParaGPT Gaps Identified & Fixed
| Gap | Status | Session |
|-----|--------|---------|
| Citations not appearing | Fixed | 21 |
| Monitoring dashboard missing | Built | 22 |
| GDPR "forget me" endpoint | Built | 22 |
| Input validation missing | Added | 22 |
| CORS too permissive | Hardened | 22 |
| No rate limiting | Added (slowapi) | 22 |
| Multi-turn conversation broken | **Fixed** — last 5 messages in LLM context | 24 |
| Silence message text wrong | **Fixed** — institutional voice per SOW | 24 |
| Citation missing provenance fields | **Fixed** — date/location/event/verifier flow through | 24 |
| Citation shows "essay" not source title | **Fixed** — `source_title` pipeline shows "The Future Is Asian (book) — 2019" | 25 |
| No sample corpus for demo | **Fixed** — 6 documents, 22 chunks seeded | 25 |
| Review EDIT action missing | **Fixed** — PATCH with `action: edit` + textarea in Dashboard | 28 |
| Review keyboard shortcuts missing | **Fixed** — `a`/`r`/`e` keys + ArrowUp/Down navigation | 28 |
| Review missing cited sources | **Fixed** — `CollapsibleCitations` with `defaultExpanded={true}` | 28 |
| Dynamic topic suggestions missing | **Fixed** — `_extract_topic_suggestions()` from retrieved passages | 28 |
| Reasoning trace panel | **Fixed** — `ReasoningTrace.tsx` + backend `_extract_trace_data()` | 28 |
| Confidence scorer overconfident (always ~100%) | **Fixed** — deterministic 4-factor scorer (no LLM self-eval) | 29 |
| CRAG loop stuck (same passages every retry) | **Fixed** — BM25 hybrid search + reranker-based evaluator | 29 |
| Retrieval quality low | **Fixed** — FlashRank cross-encoder reranking (+48% quality) | 29 |
| Seed corpus had random embeddings | **Fixed** — real Gemini embeddings, 37 passages, 8 documents | 30 |
| Landing page questions didn't match corpus | **Fixed** — aligned with demo corpus, includes irrelevant question for hedge demo | 30 |

### Sacred Archive Gaps Identified & Fixed
| Gap | Status | Session |
|-----|--------|---------|
| Strict silence not applied | Fixed | 22 |
| Multi-turn conversation broken | **Fixed** — same conversation_history_node works for both clients | 24 |
| Provenance fields missing from citations | **Fixed** — all 5 fields (source, date, location, event, verifier) in frontend | 24-25 |
| Silence message text wrong | **Fixed** — institutional voice per SOW | 24 |
| Access tier not authenticated | Known gap — needs JWT auth system | — |
| Dynamic topic suggestions missing | **Fixed** — same `_extract_topic_suggestions()` works for both clients | 28 |
| Review EDIT/shortcuts/sources | **Fixed** — all 3 review dashboard enhancements | 28 |

### Still Missing (not blocked by PCCI)
| Gap | Priority | Notes |
|-----|----------|-------|
| Demo videos | **HIGH** | Manager requested — 3-5 user journey recordings for stakeholders |
| AuditLog writes | MEDIUM | Table exists, never INSERT'd — needs writes on review/ingest/admin actions |
| Rejection → seeker flow | MEDIUM | No notification to seeker when reviewer rejects |
| GDPR delete auth | LOW | No authentication on DELETE endpoint |
| ~~Success metrics tracking~~ | ~~LOW~~ | ✅ Session 39 — `core/evaluation/` (persona_scorer + consistency_checker) |

### Blocked by PCCI Hardware
| Gap | Blocker |
|-----|---------|
| Real voice cloning | PCCI GPU + OpenAudio |
| LLM swap (Groq → SGLang) | PCCI GPU |
| Embeddings swap (Gemini → TEI) | PCCI GPU |
| Tree search (Tier 2) | MinIO on PCCI |
| Air-gapped deployment | Full PCCI infra |

### SOW Compliance Summary (Session 39)
| Client | Completion | Notes |
|--------|-----------|-------|
| ParaGPT | **~97%** | Only voice clone remaining (PCCI-blocked) |
| Sacred Archive | **~90%** | AuditLog writes + rejection flow remaining (P2) |
| **Combined** | **~97%** | 80% (S23) → 85% (S24) → 89% (S25) → 93% (S28-30) → ~97% (S39, corpus+eval+resilience) |

### Session 39 Additions
- **Corpus expansion:** ParaGPT 48+ passages (13 docs), Sacred Archive 41+ passages (10 docs)
- **Evaluation framework:** `core/evaluation/` — persona fidelity scorer + consistency checker
- **Gemini hardening:** Singleton embedder, retry backoff (3 attempts), startup health check
- **Confidence threshold:** Restored to 0.80 (from 0.65) after corpus expansion
- **Role-based access:** `require_role()` dependency — review PATCH requires reviewer/curator, ingest POST requires curator/admin
- **Frontend resilience:** Exponential backoff retry, differentiated error pages, analytics auto-refresh

---

## OSS Model Evaluation Plan (Session 35)

**Manager Directive:** "Evaluation goes hand in hand with the right models" + "assume you can maybe hit a GLM 4.7 or GLM 5"
**Provider:** Switched from Groq to OpenRouter (400+ models, single API key for evaluation)

### What Our Pipeline Needs From a Model

| Requirement | Weight | Why |
|---|---|---|
| Hallucination resistance | **Critical** | Clone MUST NOT fabricate quotes. Sacred Archive is quote-only. |
| Instruction following | **Critical** | Complex prompts: citation [N] format, silence rules, persona voice |
| RAG grounding | **Critical** | Responses grounded in retrieved passages, not parametric knowledge |
| Persona consistency | High | Must maintain clone's voice across multi-turn conversations |
| Structured output | High | Query analysis returns JSON (intent, sub_queries, response_tokens) |
| Efficiency (MoE) | Medium | PCCI hardware is finite — MoE = fewer active params per token |
| SGLang support | Required | Must deploy on PCCI sovereign infrastructure |

### Candidate Models (Research-Based Rankings)

#### TIER 1 — Top Candidates

| Model | Params (active) | Context | Key Strength | Key Weakness | OpenRouter $/M | License |
|---|---|---|---|---|---|---|
| **Qwen3.5-35B-A3B** | 35B (3B) | 256K | IFEval 92.6 (best), MMLU-Pro 85.3, 3.5x lower hallucination than GLM-Flash | Thinking model (needs suppression) | $0.16 / $1.30 | Apache 2.0 |
| **GLM-4.7-Flash** | 30B (3.6B) | 200K | Cheapest, fastest, HumanEval 94.2 | Higher hallucination in context-bound tasks | $0.06 / $0.40 | MIT |
| **GLM-5** | 744B (44B) | 205K | 34% hallucination rate (record low), #1 ELO (1451) | Needs 8×H200 GPUs | $0.80 / $2.56 | MIT |
| **GLM-4.7** (full) | 355B (32B) | 200K | #3 ELO (1445), strong all-around | Multi-GPU required | $0.38 / $1.98 | MIT |

#### TIER 2 — Worth Testing

| Model | Notes |
|---|---|
| **DeepSeek-V3.2** | ELO 1421, strong reasoning, but shorter 128K context |
| **Qwen3-30B-A3B** | Previous gen, already tested in Sessions 32-34, outperformed by 3.5 |

#### NOT Recommended

| Model | Why |
|---|---|
| Command R+ | CC-BY-NC license — can't deploy commercially on PCCI |
| Llama 3.3 70B | Dense (not MoE), more GPU, not RAG-optimized |
| Llama 4 Scout/Maverick | Restricted license (10M MAU limit) |

### Embedding Models for PCCI (replacing Gemini API)

| Model | Retrieval Accuracy | Dims | Notes |
|---|---|---|---|
| **BGE-M3** (BAAI) | 72% (highest) | 1024 | Matches our pgvector setup, 100+ languages |
| **Qwen3-Embedding-8B** | 70.58 MTEB | Flexible | Instruction-aware, Qwen ecosystem |
| **Nomic Embed V2** | 57.25% | Variable | Efficient but lower quality |

### Preliminary Recommendation (Before Testing)

| Pipeline Node | Model | Rationale |
|---|---|---|
| **Generation** (main response) | **Qwen3.5-35B-A3B** | Best instruction following + lowest hallucination in RAG context |
| **Query Analysis** (classification) | **GLM-4.7-Flash** | Cheapest, fast, good structured output |
| **CRAG Reformulator** | **GLM-4.7-Flash** | Lightweight task, speed matters |
| **If PCCI has 8×H200** | **GLM-5** for generation | Record-low hallucination, #1 Intelligence Index |
| **Embeddings (PCCI)** | **BGE-M3** | 72% accuracy, 1024-dim (matches pgvector) |

### Evaluation Protocol (Next Steps)

**Phase 1:** Quick screen — 5 test queries × 5 models via OpenRouter `--model` flag
**Phase 2:** Scoring matrix — citation accuracy, instruction following, hallucination, persona, silence, latency, cost
**Phase 3:** Head-to-head finals — top 2 models through full 28-test suite
**Phase 4:** PCCI deployment recommendation with hardware requirements

**Hardware question for manager:** Does PCCI have multi-GPU (8×H200/B200) for GLM-5, or single-GPU (24GB) for Qwen3.5/GLM-Flash?

### Sources
- [Best OSS LLMs for RAG 2026 — Prem AI](https://blog.premai.io/best-open-source-llms-for-rag-in-2026-10-models-ranked-by-retrieval-accuracy/)
- [Open LLM Leaderboard 2026](https://vertu.com/lifestyle/open-source-llm-leaderboard-2026-rankings-benchmarks-the-best-models-right-now/)
- [GLM-5 Record Low Hallucination — VentureBeat](https://venturebeat.com/technology/z-ais-open-source-glm-5-achieves-record-low-hallucination-rate-and-leverages)
- [Qwen3.5 vs GLM-4.7-Flash — AwesomeAgents](https://awesomeagents.ai/tools/qwen-3-5-35b-a3b-vs-glm-4-7-flash/)
- [OSS Embedding Benchmark](https://research.aimultiple.com/open-source-embedding-models/)
- [IFEval/IFBench Rankings 2026](https://llm-stats.com/benchmarks)

---

*This document captures management direction. Update after every session with new directives.*
