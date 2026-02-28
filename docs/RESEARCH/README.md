# Research & Open Questions

Archived research questions, decisions made, and architectural trade-offs.

**Location:** `open-questions/` in project root (original location — links preserved here for reference)

## Key Decisions (Locked)

These were researched and decided. Do not re-debate.

| # | Question | Decision | Rationale |
|---|---|---|---|
| **Q1** | Vector DB for embeddings (ParaGPT) + Knowledge graph (Sacred Archive) | Zvec (in-process) + pgvector backend for Mem0 | Zvec: no separate service, >8K QPS. pgvector: native PostgreSQL, integrated. |
| **Q2** | Document tree generation cost for 100 docs | ~2-2.5 hours locally, $42 GPT-4o batch as fallback | Acceptable. Run once at ingestion. |
| **Q3** | Mem0 backend for user memory | Use pgvector as backend for Mem0 | Zero custom code. Mem0 handles the abstraction. |
| **Q4** | Provenance graph (Sacred Archive) | Skip Apache AGE. Use pure SQL + recursive CTEs. | Apache AGE core team eliminated Oct 2024. Same power, zero external dependencies. |
| **Q5** | GPU allocation for 4 models | SGLang (LLM, GPU 0) + TEI CPU (embeddings) + Whisper + OpenAudio (GPU 1) | Two RTX 4090s. Qwen3.5-35B requires ~20GB. Other models share or run on CPU. |
| **Q6** | Local LLM for tree generation | Fork PageIndex + one-line base_url fix. Test Qwen3.5 in Week 3, GPT-4o fallback. | Qwen3.5 is capable. Fallback ready if needed. |
| **Q7** | Moving 60GB corpus to air-gapped Sacred Archive | Temporary Ethernet + LUKS encryption, 3-day process | Secure. Audited. Manual process for security. |
| **Q8** | Project timeline buffer | Recommend formal Week 0 (5 days). Project becomes 9 weeks total. | Risk mitigation. Infra validation, dependency checks. |

## How to Reference Research

All original research files are in `open-questions/INDEX.md` at the project root. These are the source documents; this README is a summary.

## Adding New Research

If a new question emerges during development:
1. Create `open-questions/09-<topic>.md`
2. Document the question, alternatives, and recommendation
3. Link it from `open-questions/INDEX.md`
4. Once decided, add to the table above and mark locked
