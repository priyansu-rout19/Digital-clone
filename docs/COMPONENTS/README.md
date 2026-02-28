# Components

Engineering specifications for each component of the Digital Clone Engine.

| # | Component | Status | Files |
|---|---|---|---|
| **01** | Clone Profile Config Model | ✅ COMPLETE | `core/models/clone_profile.py` |
| **02** | RAG Pipeline (Ingestion + Retrieval) | ⏳ NEXT | `core/rag/` |
| **03** | PostgreSQL Database Schema | ✅ COMPLETE | `core/db/schema.py`, `core/db/migrations/` |
| **04** | LangGraph Orchestration (18-node graph) | ✅ COMPLETE | `core/langgraph/conversation_flow.py` |

## Component 01: Clone Profile Config

**Location:** `core/models/clone_profile.py` (197 lines)

The configuration object that drives all behavioral differences between ParaGPT and Sacred Archive. 6 enums, 16 fields, Pydantic model with cross-field validators.

See [ARCHITECTURE.md](../ARCHITECTURE.md#3-clone-profile--the-configuration-object) for details.

## Component 02: RAG Pipeline

**Location:** `core/rag/` (to be built)

Ingestion pipeline (parse → chunk → embed → index) and retrieval (Tier 1 vector search + Tier 2 tree search with self-correction).

## Component 03: Database Schema

**Location:** `core/db/schema.py` (360 lines) + `core/db/migrations/` (14 tables)

SQLAlchemy 2.0 ORM models. 6 core tables (all clients) + 8 provenance tables (Sacred Archive).

See [core/db/README.md](../../core/db/README.md) for schema details.

## Component 04: LangGraph Orchestration

**Location:** `core/langgraph/conversation_flow.py` (289 lines) + `core/langgraph/nodes/` (5 files)

The orchestration graph. 18 nodes (query analysis, retrieval, context assembly, generation, verification, routing). Profile-driven conditional edges via closures.

4 nodes have real LLM integration. 11 nodes are stubs with correct state shapes, awaiting downstream components.
