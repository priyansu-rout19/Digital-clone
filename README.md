# Digital Clone Engine

One codebase powering two AI-powered digital clones: **ParaGPT** (interpretive, voice-enabled, public) and **Sacred Archive** (mirror-only, human-reviewed, air-gapped). Built by Prem AI.

---

## The Original Plan

The spec (v4.0, Feb 26 2026) called for a single agentic RAG pipeline controlled entirely by a per-clone config object — no `if client == "x"` branches anywhere. Four design principles drove every decision:

1. **One pipeline, configurable behavior.** The same LangGraph workflow handles both clients. The `CloneProfile` config controls generation mode, confidence thresholds, review requirements, and voice output.
2. **Two-tier retrieval.** Fast vector search (<100ms) handles most queries. For structured documents with hierarchy (books, transcripts), reasoning-based tree search (PageIndex) escalates when the first tier isn't sufficient.
3. **No unnecessary services.** Embed databases in-process where possible (Zvec). Fewer moving parts on PCCI sovereign hardware.
4. **Sovereignty by default.** All data, all models, all inference stays on PCCI. Zero external network calls. Satisfies Sacred Archive's air-gap requirement and ParaGPT's data privacy commitment.

The 5-step pipeline: **Query Analysis → Two-Tier Retrieval (with self-correction) → Context Assembly → Generation → Output Routing**

---

## What It Does Now

The core backend is functional end-to-end. Given a user query and a clone profile, the engine:

1. **Classifies intent** — Dual-layer routing: fast prefilter for greetings, then LLM binary classifier (`persona` or `retrieval`). Decomposes complex queries into sub-queries.
2. **Retrieves relevant passages** — pgvector cosine search across the clone's document corpus. Multiple sub-queries are merged with RRF (Reciprocal Rank Fusion) to surface passages relevant across all angles of the question.
3. **Self-corrects (CRAG)** — If retrieval confidence is low, the query is automatically reformulated with different search strategies and re-retrieved (up to 2 cycles).
4. **Traverses the teaching graph** (Sacred Archive only) — Recursive SQL CTE walks the `teaching_relations` graph to surface thematically connected teachings.
5. **Generates a response** — Persona-aware, with profile-controlled generation mode (interpretive for ParaGPT, mirror-only for Sacred Archive).
6. **Routes output** — ParaGPT streams direct to user. Sacred Archive queues every response for human review before delivery.

The ingestion pipeline is also complete: feed a PDF/text file → parse → semantic chunk → embed → index into pgvector. Documents become searchable immediately.

---

## Build Status

| Component | Status | Key File |
|---|---|---|
| Clone Profile Config | ✅ Complete | `core/models/clone_profile.py` |
| PostgreSQL Schema (16 tables) | ✅ Complete | `core/db/schema.py` |
| LangGraph Orchestration (19 nodes) | ✅ Complete | `core/langgraph/conversation_flow.py` |
| RAG Ingestion Pipeline | ✅ Complete | `core/rag/ingestion/` |
| RAG Retrieval (pgvector + BM25 hybrid) | ✅ Complete | `core/rag/retrieval/vector_search.py` |
| FlashRank Reranking | ✅ Complete | `core/rag/retrieval/vector_search.py` |
| Provenance Graph Query | ✅ Complete | `core/rag/retrieval/provenance.py` |
| Cross-Session Memory (Mem0) | ✅ Complete | `core/mem0_client.py` |
| Citation Verification | ✅ Complete | `core/langgraph/nodes/generation_nodes.py` |
| FastAPI Gateway (9 endpoint groups) | ✅ Complete | `api/` |
| Voice Output (edge-tts) | ✅ Complete | `core/langgraph/nodes/routing_nodes.py` |
| React Frontend (31 files) | ✅ Complete | `ui/src/` |
| Model Selector (400+ models) | ✅ Complete | `ui/src/components/ModelSelector.tsx` |
| Evaluation Framework | ✅ Complete | `core/evaluation/` + `scripts/` |
| Test Suite (161 tests) | ✅ Complete | `tests/` |
| Externalized Profiles | ✅ Complete | `profiles/` (soul.md + guardrails.md per clone) |
| Database Seeding | ✅ Complete | `scripts/seed_db.py` |

---

## Stack

**Runtime:** Python 3.12 · FastAPI · LangGraph · SQLAlchemy 2.0 · Alembic · Pydantic v2

**Models (production PCCI):** Qwen3.5-35B-A3B via SGLang · Qwen3-Embedding-0.6B via TEI · OpenAudio S1-mini (TTS) · Whisper Large V3 (transcription)

**Models (dev, Session 35+):** OpenRouter API (400+ models, default meta-llama/llama-3.3-70b-instruct) · gemini-embedding-001 via Google Gemini (3072→1024-dim Matryoshka) · edge-tts for voice

**Retrieval:** pgvector cosine + BM25 hybrid search · FlashRank cross-encoder reranking · RRF fusion · CRAG self-correction (2 retries max)

**Storage:** PostgreSQL 17 + pgvector + pgcrypto · MinIO (raw files) · Redis (cache) · Mem0 (user memory)

---

## Structure

```
core/           ← all runtime code
  models/       ← CloneProfile config (Component 01)
  db/           ← SQLAlchemy schema + Alembic migrations (Component 03)
  langgraph/    ← 19-node orchestration graph (Component 04)
  rag/          ← ingestion + retrieval pipeline (Component 02)
docs/           ← architecture + client specs
tasks/          ← progress tracking
```

---

## Plan vs Reality

Where the implementation differs from the original spec, and why:

| What Spec Said | What We Built | Why |
|---|---|---|
| **Zvec** for vector search (embedded, in-process) | **pgvector** (PostgreSQL extension) | Zvec API wasn't confirmed stable; pgvector works today, Zvec is a drop-in swap when ready |
| **Apache AGE** for provenance graph queries | Pure SQL **recursive CTEs** | Apache AGE core team was eliminated in Oct 2024 — extension is effectively dead |
| **SGLang** for LLM serving (production) | **OpenRouter API** (dev, Session 35) | Hardware (PCCI GPU server) not available yet; OpenRouter provides 400+ models including Llama 3.3 70B |
| **TEI** for embedding (production) | **Google Gemini gemini-embedding-001** (dev, 3072→1024 Matryoshka) | Same hardware dependency; same schema, zero migration needed when TEI arrives |
| **Whisper** for audio/video transcription | Not implemented | GPU server not available yet; parser raises `NotImplementedError` for audio files as a clear placeholder |
| **OpenAudio TTS** for voice output | **edge-tts** (dev, Session 16) | Free Microsoft Edge TTS as development proxy; OpenAudio for trained voice clone on PCCI |
| **PageIndex tree search** (Tier 2) | Designed stub | Requires MinIO for tree JSON storage — MinIO setup is Week 3; interface is correct and ready |
| **Mem0** for cross-session user memory | ✅ Implemented (Session 4) | pgvector backend, Google Gemini embeddings, user-scoped memories |

**Short version:** The core logic (orchestration, retrieval, generation, routing) is real and working. The hardware-dependent features (Whisper, voice, production LLM/embedding) run on dev fallbacks or stubs until the PCCI server is provisioned.

---

## Docs

- [System Architecture](docs/ARCHITECTURE.md)
- [ParaGPT Spec](docs/CLIENTS/CLIENT-1-PARAGPT.md)
- [Sacred Archive Spec](docs/CLIENTS/CLIENT-2-SACRED-ARCHIVE.md)
- [Progress Log](tasks/PROGRESS.md)
