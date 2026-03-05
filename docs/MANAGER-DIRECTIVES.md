# Manager Directives & Product Vision

**Source:** Prem AI management feedback | **Last Updated:** March 5, 2026 (Session 25)

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

### Reasoning & Tool Call Traces (REQUESTED — not yet built)
- **What:** Full visibility into the AI's decision-making at each pipeline step
- **Why:** Increase trust with clients. They need to see *why* the clone said what it said
- **Details:** Show which sources were retrieved, what confidence scores were, whether CRAG retried, what citations were verified vs hallucinated
- **Current state:** WebSocket sends node names only (`{"type": "progress", "node": "tier1_retrieval"}`) — no actual data payload
- **Target:** Collapsible "Show reasoning" panel under each response with full pipeline trace

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

## Requirement Audit Results (Sessions 22-25)

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

### Sacred Archive Gaps Identified & Fixed
| Gap | Status | Session |
|-----|--------|---------|
| Strict silence not applied | Fixed | 22 |
| Multi-turn conversation broken | **Fixed** — same conversation_history_node works for both clients | 24 |
| Provenance fields missing from citations | **Fixed** — all 5 fields (source, date, location, event, verifier) in frontend | 24-25 |
| Silence message text wrong | **Fixed** — institutional voice per SOW | 24 |
| Access tier not authenticated | Known gap — needs JWT auth system | — |

### Still Missing (not blocked by PCCI)
| Gap | Priority | Notes |
|-----|----------|-------|
| Reasoning trace panel | **HIGH** | Manager requested — increases trust. Show pipeline decisions under each response |
| Demo videos | **HIGH** | Manager requested — 3-5 user journey recordings for stakeholders |
| Success metrics tracking | MEDIUM | Citation accuracy, persona fidelity, latency — no measurement code |
| Review EDIT action | MEDIUM | Only approve/reject — SOW requires edit capability |
| Review keyboard shortcuts | MEDIUM | Mouse-only — SOW requires batch efficiency (50+/day) |
| Dynamic topic suggestions | MEDIUM | Silence message doesn't suggest related topics |

### Blocked by PCCI Hardware
| Gap | Blocker |
|-----|---------|
| Real voice cloning | PCCI GPU + OpenAudio |
| LLM swap (Groq → SGLang) | PCCI GPU |
| Embeddings swap (Gemini → TEI) | PCCI GPU |
| Tree search (Tier 2) | MinIO on PCCI |
| Air-gapped deployment | Full PCCI infra |

### SOW Compliance Summary (Session 25)
| Client | Completion | Notes |
|--------|-----------|-------|
| ParaGPT | **96%** | Only voice clone remaining (PCCI-blocked) |
| Sacred Archive | **83%** | Review dashboard enhancements + audit log remaining |
| **Combined** | **89%** | Up from 80% (Session 23) → 85% (Session 24) → 89% (Session 25) |

---

*This document captures management direction. Update after every session with new directives.*
