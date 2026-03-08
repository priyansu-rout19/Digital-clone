# ARCHITECTURE: Digital Clone Engine — Unified Technical System Design

**Version:** 5.2 | **Date:** March 7, 2026 (Session 39) | **Prepared by:** Prem AI — Solution Architecture

**Note:** This is the **specification/design document** (target production). For **current implementation status**, see [PROGRESS.md](../tasks/PROGRESS.md). Development currently uses drop-in proxy models (Google Gemini for embeddings, OpenRouter for LLM inference) pending PCCI infrastructure — zero code changes needed when production models available.

---

## 1. Overview

The Digital Clone Engine is a **single codebase** that powers two initial clients:

- **ParaGPT** — Personal brand digital clone (interpretive, voice-enabled, public)
- **Sacred Archive** — Spiritual teaching preservation (mirror-only, human-reviewed, air-gapped)

Every behavioral difference between the two clients is driven by a **per-clone configuration object** (clone profile), not a code branch. The same pipeline, same models, same infrastructure — just different settings.

**Core Principle:** One Engine, Two Profiles.

```
Analyze → Retrieve → Assemble → Generate → Verify
```

The orchestrator reads the clone profile and adjusts behavior at each step.

---

## 2. Design Principles

1. **One pipeline, configurable behavior.** The agentic RAG pipeline is the same for all clones. The clone profile controls generation mode, confidence thresholds, review requirements, and voice output.

2. **No unnecessary services.** We embed where we can (Zvec in-process, Apache AGE in PostgreSQL) rather than deploying standalone servers. Fewer services means fewer failure modes on PCCI.

3. **Two-tier retrieval.** Fast vector search handles most queries (<100ms). For structured documents (books, transcripts with hierarchy), reasoning-based tree search (PageIndex) provides precision when the first tier isn't sufficient. The orchestrator decides when to escalate.

4. **Sovereignty by default.** All data, all models, all inference stays on PCCI. Zero external network calls. This satisfies the Sacred Archive's air-gap requirement and ParaGPT's data privacy commitment.

---

## 3. Clone Profile — The Configuration Object

Every clone instance is governed by a profile stored in PostgreSQL. The orchestrator reads this at request time.

```yaml
clone_profile:
  # Identity
  slug: "parag-khanna"
  display_name: "Parag Khanna"
  bio: "Geopolitical strategist..."
  avatar_url: "/static/avatars/pk.jpg"

  # Generation behavior
  generation_mode: "interpretive"    # interpretive | mirror_only
  confidence_threshold: 0.80         # 0.0–1.0 (factory default; ParaGPT DB override: 0.60)
  silence_behavior: "soft_hedge"     # soft_hedge | strict_silence
  silence_message: "..."

  # Review
  review_required: false             # true → all responses queued

  # Memory
  user_memory_enabled: true          # Mem0 cross-session tracking

  # Voice
  voice_mode: "ai_clone"             # ai_clone | original_only | text_only
  voice_model_ref: "voice_pk_v1"

  # Retrieval
  retrieval_tiers: ["vector"]        # [vector] | [vector, tree_search]
  provenance_graph_enabled: false    # Cypher graph queries
  access_tiers: ["public"]           # [public] | [devotee, friend, follower]

  # Deployment
  deployment_mode: "standard"        # standard | air_gapped
```

### How Configuration Unifies the Two Clients

| Setting | ParaGPT | Sacred Archive |
|---|---|---|
| `generation_mode` | `interpretive` | `mirror_only` |
| `confidence_threshold` | `0.80` (factory; DB: `0.60`) | `0.95` |
| `silence_behavior` | `soft_hedge` | `strict_silence` |
| `review_required` | `false` | `true` |
| `user_memory_enabled` | `true` | `false` |
| `voice_mode` | `ai_clone` | `original_only` |
| `retrieval_tiers` | `[vector]` | `[vector, tree_search]` |
| `provenance_graph_enabled` | `false` | `true` |
| `access_tiers` | `[public]` | `[devotee, friend, follower]` |
| `deployment_mode` | `standard` | `air_gapped` |

**No conditional code paths per client** — just configuration-driven branching at each pipeline step.

---

## 4. System Architecture — Four Layers

### Layer 1: Client (React SPA)

**Tech Stack:** Vite 6 + React 19 + TypeScript + Tailwind CSS v4

**File Structure:**

    ui/src/
    ├── api/         → REST client + WebSocket manager + TypeScript interfaces
    ├── hooks/       → useChat (WS), useCloneProfile, useAudio (base64→playback)
    ├── components/  → ChatInput, MessageBubble, NodeProgress, AudioPlayer, CitationCard, CitationGroupCard, CitationList, CollapsibleCitations, ReasoningTrace, ErrorBoundary
    ├── pages/
    │   ├── paragpt/        → Landing (glassmorphism, corpus-aligned questions) + Chat (copper accent, reasoning trace)
    │   ├── sacred-archive/ → Landing (tier selector) + Chat (serif+gold, reasoning trace)
    │   ├── review/         → Dashboard (3-column approve/reject)
    │   └── analytics/     → Monitoring dashboard (stats, charts)
    └── themes/      → Design tokens per clone profile

**Routing:** `/:slug` auto-detects ParaGPT vs Sacred Archive via `generation_mode` field from profile API. No hardcoded clone switching — fully data-driven.

**Integration Points:**
- REST: `GET /clone/{slug}/profile`, `POST /chat/{slug}`, `GET /review/{slug}`, `PATCH /review/{slug}/{id}`, `GET /analytics/{slug}`, `DELETE /users/{user_id}/data`
- WebSocket: `ws://host/chat/ws/{slug}` — streams node progress events, then final response
- Vite dev proxy: `/chat`, `/clone`, `/review`, `/ingest`, `/analytics`, `/users` → `http://localhost:8000`

**Design System:** Clone-profile-driven theming:
- ParaGPT: Near-black (#0d0d0d) + copper (#d08050), glassmorphism cards, sans-serif, header-less chat with thinking bubble
- Sacred Archive: Deep brown (#2c2c2c) + gold (#c4963c), serif typography, decorative quotes

### Layer 2: Gateway + Orchestration
- FastAPI + slowapi rate limiting (60/min chat, 10/min ingest)
- CORS hardened via `CORS_ORIGINS` env var
- **LangGraph Orchestrator** — 19-node stateless pipeline
- Analytics pipeline — `query_analytics` table populated after each query (latency, confidence, tier, silence)
- GDPR delete — `DELETE /users/{user_id}/data` (messages, analytics, Mem0 memories)
- Monitoring dashboard — `GET /analytics/{slug}` aggregate stats endpoint
- Ingestion Pipeline (BackgroundTasks)
- Review Queue

The orchestrator is the **core** — it reads the clone profile and adjusts behavior at each pipeline step.

### Layer 3: Inference (GPU Models on PCCI)
**Production (target):**
- **Primary LLM** — one of: Qwen3.5-35B-A3B, GLM-4.7-Flash, GLM-4.7, GLM-5 (all OSS, OpenAI-compatible via SGLang)
- **Qwen3-Embedding-0.6B** — Embeddings via TEI, ~2GB
- **OpenAudio S1-mini** — TTS (ParaGPT only), ~2GB
- **Whisper Large V3** — Transcription, ~6GB
- All served via **SGLang** (OpenAI-compatible API, continuous batching, prefix caching)

**Development (current):**
- **OpenRouter API** — meta-llama/llama-3.3-70b-instruct (default) via env-var configurable `core/llm.py` (`LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`). 400+ models available. Switched from Groq in Session 35.
- **Google Gemini** — gemini-embedding-001 (3072→1024-dim Matryoshka, HTTP API via LangChain). Singleton embedder with retry backoff (3 attempts) + startup health check (Session 39).
- Both are drop-in replacements with identical output dimensions/signatures
- **Zero code changes** needed to swap production models — just set env vars
- **Experiment script:** `scripts/test_model.py` tests any model against 5 use-case prompts

### Layer 4: Data + Memory
- **Zvec** — Embedded vector DB (in-process)
- **PageIndex** — Hierarchical tree indices (JSON on filesystem)
- **Apache AGE** — Provenance graph (Sacred Archive only)
- **Mem0** — Cross-session user memory (ParaGPT only)
- **PostgreSQL 17** — Clone config, review queue, audit logs
- **MinIO** — Raw corpus files
- **Redis 7** — Cache + session state

---

## 5. The Pipeline — Five Steps

Every query flows through this pipeline. The clone profile controls behavior at each step.

### Step 1: Query Analysis
- LLM classifies intent (factual, synthesis, temporal, opinion, exploratory)
- Decomposes complex queries into sub-queries
- Checks access tier permissions
- **~0.3s, 1 LLM call**

### Step 2: Two-Tier Retrieval with Self-Correction
**Tier 1 — Hybrid Search (Vector + BM25)** (<200ms):
- Embed each sub-query via Gemini embeddings (3072→1024 truncated)
- **Vector search:** pgvector cosine similarity against `document_chunks.embedding`
- **BM25 keyword search:** PostgreSQL `tsvector`/`tsquery` full-text search against `document_chunks.search_vector` (GIN index, migration 0006)
- **RRF fusion:** `sum(1/(60+rank_i))` merges vector and BM25 results. BM25 retrieves DIFFERENT passages from vector search — critical for CRAG reformulation.
- If `provenance_graph_enabled`: parallel provenance graph queries (recursive CTEs)

**Reranking** (Session 29):
- Over-retrieves 30 candidates (3x top_k), then reranks to top 10
- **FlashRank** cross-encoder (`ms-marco-MiniLM-L-12-v2`, ~34MB, CPU-only)
- Per-passage `rerank_score` stored. Mean of top-5 = `retrieval_confidence`
- Graceful fallback to RRF order if FlashRank unavailable

**Tier 2 — Tree Search** (conditional, +1-2s):
- Runs immediately after Tier 1 (if profile enables it + documents have PageIndex trees)
- LLM reasons about hierarchical sections of structured documents
- Augments T1 results with structurally-relevant passages

**Self-Correction (CRAG loop)** (Session 29 fix):
- **Evaluator:** Uses reranker scores (not passage-count heuristic). Mean reranker score * passage factor.
- **Reformulator:** Sees actual passage text + reranker scores. Generates keyword extraction, sub-topic decomposition, domain jargon queries — NOT paraphrases (which embed identically).
- BM25 breaks the stuck loop: keyword queries with different terms retrieve genuinely different passages.
- Max 2 retries (reduced from 3 — Session 34 found 3rd retry has diminishing returns).

### Step 3: Context Assembly
- Format retrieved passages into 8K-32K token context window
- Prepend persona system prompt
- For Sacred Archive: inject full provenance (date, location, event, verifier)

### Step 4: In-Persona Generation
The LLM generates a response using:
- Assembled context
- Persona system prompt (varies by profile)
- User memory (if enabled)
- Generation rules

**If `generation_mode: interpretive`** → Synthesize + cite sources
**If `generation_mode: mirror_only`** → Direct quotes only, no paraphrasing

### Step 5: Verification + Output
- Verify each cited source against retrieved passages
- **Multi-factor confidence scoring** (Session 29 — deterministic, no LLM call):
  - Retrieval confidence (0.35 weight) — from reranker scores or cosine similarity
  - Citation coverage (0.25) — fraction of passages actually cited in response
  - Response grounding (0.25) — lexical overlap between response and context (content words only)
  - Passage count factor (0.15) — did we find enough source material?
- Route based on profile:
  - High confidence → Stream to user
  - Low confidence + soft_hedge → Hedge message
  - Low confidence + strict_silence → Silence Mode
  - review_required → Queue for human review
- If voice enabled: TTS streams audio interleaved with text

---

## 6. Codebase Structure (Current Status — March 7, 2026, Session 39)

| Component | Location | Status | Notes |
|---|---|---|---|
| **Config Model** | `core/models/clone_profile.py` | ✅ COMPLETE | 7 enums, 17+ fields, 2 presets (ParaGPT factory=0.80, DB=0.60), `persona_eval` field (S39) |
| **LLM Client** | `core/llm.py` | ✅ COMPLETE | OpenRouter (dev) → SGLang (prod), Qwen thinking suppression, max_tokens=2048 |
| **Embeddings Client** | `core/rag/ingestion/embedder.py` | ✅ COMPLETE | Google Gemini (dev) → TEI (prod), 3072→1024-dim truncated, singleton + retry backoff (S39) |
| **Mem0 Client** | `core/mem0_client.py` | ✅ COMPLETE | pgvector backend, `TruncatedGoogleEmbeddings` wrapper (Session 26) |
| **LangGraph Orchestrator** | `core/langgraph/conversation_flow.py` | ✅ COMPLETE | 19 nodes, T2 before CRAG |
| **Orchestration Nodes** | `core/langgraph/nodes/` | ✅ COMPLETE | Real LLM, real retrieval, real memory, multi-factor scorer (S29) |
| **Database Schema** | `core/db/schema.py` | ✅ COMPLETE | 15 tables, pgvector indexing |
| **Migrations** | `core/db/migrations/` | ✅ COMPLETE | 6 migrations (0006: BM25 tsvector + GIN index, Session 29) |
| **RAG Ingestion** | `core/rag/ingestion/` | ✅ COMPLETE | Parser + chunker (semantic) + embedder + indexer (with tsvector) |
| **RAG Retrieval** | `core/rag/retrieval/` | ✅ COMPLETE | Hybrid vector+BM25, FlashRank reranking, RRF fusion, CRAG (S29) |
| **FastAPI Layer** | `api/` | ✅ COMPLETE | 7 endpoint groups, WebSocket + reasoning trace, rate limiting, CORS |
| **Test Suite** | `tests/` | ✅ COMPLETE | 97 tests passing (4 test files) |
| **Database Seeding** | `scripts/` | ✅ COMPLETE | 2 clones, 1 user, 13 docs (ParaGPT) + 10 docs (Sacred), 48+ passages (S39 corpus expansion) |
| **Evaluation** | `core/evaluation/` | ✅ COMPLETE | Persona fidelity scorer + consistency checker (S39) |
| **Frontend** | `ui/` | ✅ COMPLETE | 29 source files (2 dead files removed S39), ModelSelector, ReasoningTrace, CollapsibleCitations, copper theme, resilience hardening (S37-39) |

---

## 7. Key Decisions (Locked)

- **Profile-driven routing** via closures + conditional edges (no code branches per client)
- **OpenRouter** as development LLM proxy (switched from Groq in S35, 400+ models)
- **Pydantic models** for clean JSON serialization
- **Stubs with correct state shapes** to verify orchestration before building dependencies
- **No Apache AGE** — use pure SQL tables + recursive CTEs (team eliminated Oct 2024)
- **BIGSERIAL for audit_log + query_analytics** — guarantees immutable ordering
- **Semantic chunking** via LangChain SemanticChunker + Google Gemini embeddings (Session 13). Old fixed-size chunker preserved as fallback
- **FlashRank cross-encoder reranking** (Session 29) — `ms-marco-MiniLM-L-12-v2` (~34MB, CPU-only). Over-retrieve 3x, rerank to top_k. No PyTorch dependency
- **BM25 hybrid search** (Session 29) — PostgreSQL `tsvector` column + GIN index. Combined with vector results via RRF. Breaks CRAG retry loop where paraphrased queries retrieved identical passages
- **Deterministic confidence scoring** (Session 29) — 4-factor weighted formula replaces LLM self-evaluation (which always returned ~1.0). No LLM call = faster + calibrated

---

See [CLIENTS/](CLIENTS/) for ParaGPT and Sacred Archive specific requirements.
See [COMPONENTS/](COMPONENTS/) for engineering specifications for each component.
