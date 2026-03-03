# ARCHITECTURE: Digital Clone Engine — Unified Technical System Design

**Version:** 4.0 | **Date:** February 26, 2026 | **Prepared by:** Prem AI — Solution Architecture

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
  confidence_threshold: 0.80         # 0.0–1.0
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
| `confidence_threshold` | `0.80` | `0.95` |
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

### Layer 1: Client
- Public Chat Page (React SPA)
- Review Dashboard (for Sacred Archive reviewers)
- Creator Dashboard (analytics)
- WebSocket streaming

### Layer 2: Gateway + Orchestration
- FastAPI + Nginx (OAuth, rate limiting)
- **LangGraph Orchestrator** — 18-node stateless pipeline
- Persona Manager
- Ingestion Pipeline (Celery)
- Review Queue + notification service

The orchestrator is the **core** — it reads the clone profile and adjusts behavior at each pipeline step.

### Layer 3: Inference (GPU Models on PCCI)
- **Qwen3.5-35B-A3B** (4-bit AWQ) — Primary LLM, ~20GB VRAM
- **Qwen3-Embedding-0.6B** — Embeddings, ~2GB
- **OpenAudio S1-mini** — TTS (ParaGPT only), ~2GB
- **Whisper Large V3** — Transcription, ~6GB

All served via **SGLang** (OpenAI-compatible API, continuous batching, prefix caching).

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
**Tier 1 — Vector Search** (<100ms):
- Embed each sub-query
- Search against Zvec collection
- Reciprocal rank fusion for multiple sub-queries
- If `provenance_graph_enabled`: parallel Apache AGE queries

**Tier 2 — Tree Search** (conditional, +1-2s):
- Runs immediately after Tier 1 (if profile enables it + documents have PageIndex trees)
- LLM reasons about hierarchical sections of structured documents
- Especially valuable for books, transcripts with hierarchy
- Augments T1 results with structurally-relevant passages

**Self-Correction (CRAG loop)**:
- Evaluates the combined T1+T2 result
- If confidence below threshold, reformulate query and retry both tiers
- Max 3 hops

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
- Score confidence (0.0-1.0)
- Route based on profile:
  - High confidence → Stream to user
  - Low confidence + soft_hedge → Hedge message
  - Low confidence + strict_silence → Silence Mode
  - review_required → Queue for human review
- If voice enabled: TTS streams audio interleaved with text

---

## 6. Codebase Structure (Current Status)

| Component | Location | Status |
|---|---|---|
| **Config Model** | `core/models/clone_profile.py` | ✅ COMPLETE |
| **LLM Client** | `core/llm.py` | ✅ COMPLETE |
| **LangGraph Orchestrator** | `core/langgraph/conversation_flow.py` | ✅ COMPLETE |
| **Orchestration Nodes** | `core/langgraph/nodes/` | ✅ COMPLETE (4 real LLM, 11 stubs) |
| **Database Schema** | `core/db/schema.py` | ✅ COMPLETE |
| **Migrations** | `core/db/migrations/` | ✅ COMPLETE |
| **RAG Pipeline** | `core/rag/` | ⏳ NEXT |
| **FastAPI Layer** | `api/` | ⏳ NEXT |
| **Frontend** | `web/` | ⏳ NEXT |

---

## 7. Key Decisions (Locked)

- **Profile-driven routing** via closures + conditional edges (no code branches per client)
- **Groq + qwen/qwen3-32b** as development LLM proxy
- **Pydantic models** for clean JSON serialization
- **Stubs with correct state shapes** to verify orchestration before building dependencies
- **No Apache AGE** — use pure SQL tables + recursive CTEs (team eliminated Oct 2024)
- **BIGSERIAL for audit_log + query_analytics** — guarantees immutable ordering

---

See [CLIENTS/](CLIENTS/) for ParaGPT and Sacred Archive specific requirements.
See [COMPONENTS/](COMPONENTS/) for engineering specifications for each component.
