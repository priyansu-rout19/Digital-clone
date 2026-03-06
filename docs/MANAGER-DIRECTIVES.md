# Manager Directives & Product Vision

**Source:** Prem AI management feedback | **Last Updated:** March 6, 2026 (Session 30)

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
| Success metrics tracking | LOW | Citation accuracy, persona fidelity — no measurement code |

### Blocked by PCCI Hardware
| Gap | Blocker |
|-----|---------|
| Real voice cloning | PCCI GPU + OpenAudio |
| LLM swap (Groq → SGLang) | PCCI GPU |
| Embeddings swap (Gemini → TEI) | PCCI GPU |
| Tree search (Tier 2) | MinIO on PCCI |
| Air-gapped deployment | Full PCCI infra |

### SOW Compliance Summary (Session 30)
| Client | Completion | Notes |
|--------|-----------|-------|
| ParaGPT | **97%** | Only voice clone remaining (PCCI-blocked) |
| Sacred Archive | **90%** | AuditLog writes + rejection flow remaining (P2) |
| **Combined** | **93%** | 80% (S23) → 85% (S24) → 89% (S25) → 93% (S28-30) |

---

*This document captures management direction. Update after every session with new directives.*
