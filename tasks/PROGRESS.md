# Digital Clone Engine — Progress & Status

**Last Updated:** March 8, 2026 (Session 42)
**Status:** ~99% SOW delivered (all non-PCCI code gaps closed). 97 tests pass, zero TS errors, production build clean.

---

## Project Overview

Unified backend serving two digital clones from one codebase:
- **ParaGPT:** Digital clone of Parag Khanna (geopolitical strategist). Interpretive, voice-enabled, direct streaming.
- **Sacred Archive:** Spiritual teachings mirror. Mirror-only quotes, human review required, air-gapped.

All behavioral differences driven by `CloneProfile` config + `build_graph(profile)` factory. No code branches.

---

## Component Status

| Component | Status | Key Sessions | Notes |
|---|---|---|---|
| Clone Profile Config | COMPLETE | 1, 13 | 7 enums, 17 fields, 2 presets (`core/models/clone_profile.py`) |
| RAG Ingestion | COMPLETE | 13-14 | Semantic chunking (LangChain), Gemini embeddings (1024-dim), pgvector HNSW |
| RAG Retrieval | COMPLETE | 14, 29, 35 | Hybrid vector+BM25, FlashRank reranking, RRF fusion, independent fallback |
| DB Schema | COMPLETE | 3, 12, 29, 40 | 16 tables, 7 migrations, PostgreSQL 17 + pgvector + pgcrypto (`core/db/schema.py`) |
| LangGraph Orchestration | COMPLETE | 4-7, 34 | 19 nodes, 25-key ConversationState, `build_graph(profile)` factory |
| LLM Integration | COMPLETE | 32-33, 35 | OpenRouter (400+ models), per-request override, max_tokens=2048 |
| Mem0 Memory | COMPLETE | 4, 14, 26 | pgvector backend, TruncatedGoogleEmbeddings (3072->1024), ParaGPT only |
| FastAPI Layer | COMPLETE | 8-10, 17, 40 | 9 endpoint groups (+feedback), CORS, rate limiting, role-based access |
| React Frontend | COMPLETE | 19-28, 31, 33, 37, 39, 40 | 31 source files, Vite 6 + React 19 + TS + Tailwind v4 |
| Test Suite | COMPLETE | 10, 16, 34, 42 | 97 tests (34 API + 26 S16 + 10 chunker + 27 S42) |
| Corpus | COMPLETE | 25, 30, 36, 39 | ParaGPT 48+ passages/13 docs, Sacred Archive 41+ passages/10 docs |
| Evaluation | COMPLETE | 39, 40 | `core/evaluation/` + 50-query eval suites + 30-query foundation gate |
| Remaining Stubs (3) | PCCI-BLOCKED | — | LLM swap (SGLang), embeddings swap (TEI), tree search (MinIO) |

---

## Node Implementation Status

| Node | Real/Stub | LLM | Notes |
|---|---|---|---|
| query_analysis | Real | Yes | Intent classification, sub-query decomposition, context-aware (S34) |
| tier1_retrieval | Real | No | pgvector cosine + BM25 hybrid, FlashRank reranking (S29) |
| crag_evaluator | Real | No | Reranker-score confidence (S29) |
| query_reformulator | Real | Yes | Keyword extraction + sub-topic decomposition (S29) |
| tier2_tree_search | Stub | No | Returns passages unchanged — MinIO TODO (PCCI) |
| provenance_graph_query | Real | No | SQL recursive CTE, parameterized (S17) |
| context_assembler | Real | No | Assembles passages into context string |
| conversation_history | Real | No | Last 5 messages from DB (S24, pipeline reorder S34) |
| memory_retrieval | Real | No | Mem0 search (ParaGPT only) |
| memory_writer | Real | No | Saves turns to Mem0 (ParaGPT only) |
| in_persona_generator | Real | Yes | Persona-aware, temp=0.0 for mirror_only (S17) |
| citation_verifier | Real | No | [N] markers, cross-refs passages, source_title pipeline (S25) |
| confidence_scorer | Real | No | Deterministic 4-factor: retrieval(0.35) + citation(0.25) + grounding(0.25) + passages(0.15) (S29) |
| soft_hedge_router | Real | No | Overwrites raw_response AND verified_response (S17/S22) |
| strict_silence_router | Real | No | Silence flag, confidence-first routing (S34 fix) |
| review_queue_writer | Real | No | DB INSERT (S16) |
| stream_to_user | Real | Yes | LLM sentence splitting (S16) |
| voice_pipeline | Real | No | edge-tts MP3 (S16) |

---

## Key Technical Decisions

| Decision | Why |
|---|---|
| `build_graph(profile)` factory | Profile captured in closures. Single code path, different routing per client. |
| Node factories (`make_node_name(profile)`) | Closure keeps node signatures clean. |
| OpenRouter API (was Groq) | 400+ models, per-request switching. Will swap to SGLang on PCCI. |
| Gemini embeddings (1024-dim) | Generous free tier. Matryoshka truncation 3072->1024. Will swap to TEI on PCCI. |
| Deterministic confidence scorer | No LLM self-eval (overconfident). 4-factor formula based on retrieval quality. |
| BM25 + vector hybrid | BM25 breaks stuck CRAG loops (different ranking than embeddings). |
| FlashRank reranking | CPU-only cross-encoder (~34MB). 2-stage: over-retrieve 30, rerank to 10. |

---

## ConversationState Keys (25)

`query_text`, `clone_id`, `user_id`, `sub_queries`, `intent_class`, `access_tier`, `token_budget`, `response_tokens`, `model_override`, `retrieved_passages`, `provenance_graph_results`, `retrieval_confidence`, `retry_count`, `assembled_context`, `user_memory`, `conversation_history`, `raw_response`, `verified_response`, `final_confidence`, `cited_sources`, `silence_triggered`, `suggested_topics`, `voice_chunks`, `audio_base64`, `audio_format`

---

## Session History

| Session | Date | Focus | Key Changes |
|---|---|---|---|
| 1-3 | — | Foundation | CloneProfile, DB schema (15 tables), LangGraph graph skeleton |
| 4-7 | — | Core nodes | Mem0 memory, citation verifier, graph routing fixes, T2 ordering |
| 8-10 | — | API layer | FastAPI endpoints, 33 API tests, WebSocket streaming |
| 12 | — | Database | PostgreSQL 17 live, pgvector, migrations applied, seeded |
| 13-14 | — | RAG pipeline | Semantic chunking, Gemini embeddings, real integration tests, 4 bugs found |
| 16 | — | Stub replacement | 6 stubs -> real: review_queue, voice, token_budget, stream, CRAG, audio parsing |
| 17 | — | Backend audit | 12 fixes: silence bug, SQL injection, path traversal, cross-tenant, temp=0.0 |
| 19-20 | — | Frontend v1 | 21 React files, error boundary, WS resilience, mobile responsive |
| 21-22 | — | Citations + audit | Citation [N] fix, analytics dashboard, GDPR delete, rate limiting, CORS |
| 23 | — | SOW audit | 80% compliance, 12 gaps found (3 P0, 4 P1, 3 P2, 2 PCCI) |
| 24-25 | — | P0 fixes | Multi-turn history, provenance in citations, silence message, sample corpus |
| 26 | — | Dynamic length | LLM-decided response_tokens (100-1000), Mem0 dimension fix (3072->1024) |
| 27 | — | UI overhaul | Copper theme, glassmorphism, citation grouping, collapsible citations |
| 28 | — | P1 fixes | Review EDIT/keyboard shortcuts/cited sources, topic suggestions, reasoning trace |
| 29 | — | RAG overhaul | FlashRank reranking, BM25 hybrid, 4-factor confidence scorer, CRAG loop fix |
| 30 | — | Demo readiness | Real Gemini embeddings in corpus (37 passages), aligned starter questions |
| 31 | — | Frontend polish | 9 fixes: topic pills, thinking bubble, node labels, new conversation, char counter, 404, copy, textarea, audio seek |
| 32 | — | LLM config | Env-var configurable LLM (LLM_MODEL, LLM_BASE_URL, LLM_API_KEY) |
| 33 | — | Model selector | Per-request model override (25th state key), GET /models, ModelSelector.tsx |
| 34 | Mar 6 | Multi-turn fix | 7 bugs: user_id, pipeline reorder, context-aware query analysis, Sacred Archive silence bypass |
| 35 | Mar 7 | OpenRouter | Provider switch (Groq->OpenRouter), 5 bugs: model_override dropped, ModelSelector cache, 402 error, BM25 fallback, Qwen thinking |
| 36 | Mar 7 | Sacred Archive | 0-passages bug (no corpus + access tier mismatch), batch embedding optimization |
| 37 | Mar 7 | Frontend hardening | 19 edge case bugs: unmount safety, race guards, XSS defense, IME, cancelled patterns |
| 38 | Mar 7 | P2 quality | AuditLog writes, rejection->seeker flow, GDPR delete auth |
| 39 | Mar 7 | Corpus + eval | Corpus expanded (89+ passages), Gemini singleton+retry, evaluation framework, role-based access, frontend resilience |
| 40 | Mar 8 | Close all gaps | SOW audits, chat audit logging, prediction hedging, 50-query eval suites, foundation gate, corpus gap detection, pgcrypto encryption, batch review, seeker feedback survey, FeedbackWidget |
| 41 | Mar 8 | Doc-code drift | Fix retries/thresholds/LLM call count drift in 16+ doc files |
| 42 | Mar 8 | Skip-RAG + verification | Self-referential query shortcut, Mem0 provider fix, 27 new tests, S16 test fix |

---

## Architecturally Significant Bug Fixes

These are bugs whose root causes reveal important patterns:

1. **Silence bypass (S17, S22):** Must overwrite BOTH `raw_response` AND `verified_response` when silencing — LLM output leaked through.
2. **Sacred Archive silence bypass (S34):** `after_confidence()` checked `review_required` before confidence threshold — always routed to review, never silence. Fix: check confidence FIRST.
3. **Multi-turn broken (S34):** 3 compounding bugs — hard-coded "anonymous" user_id, pipeline ordering (history after retrieval), context-blind query analysis. Fix: pipeline reorder + context-aware analysis.
4. **CRAG loop stuck (S29):** Paraphrased queries embed to identical vectors. Evaluator was a no-op (passage count always high). Confidence scorer was blind (graded fluency, not groundedness). Fix: FlashRank reranking + BM25 hybrid + deterministic scorer.
5. **BM25 fallback unreachable (S35):** Embedding failure exited `search()` before BM25 ran. Fix: inner try/except, BM25 runs independently.
6. **LangGraph drops undeclared keys (S33/S35):** `model_override` silently dropped because it wasn't in ConversationState TypedDict. Every state key MUST be declared.
7. **Mem0 dimension mismatch (S26):** Gemini outputs 3072-dim, pgvector expects 1024. Ingestion truncated but Mem0 didn't. Fix: `TruncatedGoogleEmbeddings` wrapper.
8. **OpenRouter 402 (S35):** `max_tokens=None` reserved 65K tokens against credits. Fix: default to 2048.
9. **Test identity vs equality (S42):** Tests used `result is state` but code evolved to return `{**state, "review_id": ...}`. Use equality checks for dict comparison, not identity.

---

## Pipeline Flow

```
conversation_history -> query_analysis -> tier1_retrieval -> provenance_graph_query
  -> crag_evaluator -> [retry loop: query_reformulator -> tier1_retrieval -> crag_evaluator]
  -> tier2_tree_search -> context_assembler -> memory_retrieval
  -> in_persona_generator -> citation_verifier -> confidence_scorer
  -> [hedge/silence routing] -> stream_to_user -> memory_writer -> voice_pipeline
```

---

## For Next Session (Session 43)

**Remaining Work:**
1. Demo videos — 5 user journey recordings (manager request, non-code)
2. Run eval suites — `python3 tests/eval_suite_paragpt.py` + `python3 tests/eval_suite_sacred_archive.py`
3. Run foundation gate — `python3 scripts/foundation_gate.py`
4. Full corpus — current 89+ passages / 23 docs is demo-level. Need full library from client.

**PCCI-Blocked (Phase 3 — Production):**
- LLM: OpenRouter -> SGLang (env var swap)
- Embeddings: Gemini -> TEI (LangChain drop-in)
- Tree search: MinIO + PageIndex
- Voice: edge-tts -> OpenAudio (trained voice model)
- Air-gap enforcement for Sacred Archive

**Quick Start:**
```bash
python3 -m pytest tests/ -v                  # expect 97 passed
python3 scripts/foundation_gate.py            # pass/fail gate
python3 scripts/corpus_gap_report.py          # coverage gaps
cd ui && npm run build                        # zero TS errors
```

**Cross-references:** `tasks/lessons.md` (39 lessons), `tasks/todo.md` (action items), `docs/PARAGPT-AUDIT-REPORT.md`, `docs/SACRED-AUDIT-REPORT.md`
