# Digital Clone Engine -- SOW Gap Action Items

**Source:** `docs/PARAGPT-AUDIT-REPORT.md` (Session 40 audit against `client-sow-paragpt.md.pdf`)
**Created:** March 7, 2026

---

## Before Demo (hours)

- [ ] **Run existing eval tools** -- Execute `python scripts/evaluate_responses.py --clone paragpt-client --limit 50` to get persona fidelity + consistency baselines. *(SOW 8.2, 8.5)*
- [x] **Add voice toggle to Chat.tsx** -- SOW says "if they enable voice" (user choice). Currently always-on per profile. Add UI on/off toggle. *(SOW 3.7, Story 2)*
- [x] **Add prediction hedging to system prompt** -- Added in Session 40. *(SOW Story 6)*

## Before Production (days)

- [x] **Build 50-query eval suite** -- `scripts/eval_suite_paragpt.py` + `scripts/eval_suite_sacred_archive.py`. Built in Session 40. *(SOW 4.9, 8.1, 8.2, 8.5)*
- [x] **Build 30-query foundation gate script** -- `scripts/foundation_gate.py`. Built in Session 40. *(SOW 4.1 gate)*
- [x] **Enable encryption at rest** -- pgcrypto `dce_encrypt`/`dce_decrypt` (migration 0007). Built in Session 40. *(SOW 7.2)*
- [x] **Add corpus gap detection** -- `scripts/corpus_gap_report.py`. Built in Session 40. *(SOW 6.4)*

## Before Production (optimization)

- [ ] **Profile + graph TTL cache** -- Add in-process 5-min TTL cache in `api/deps.py` for `CloneProfile` + compiled `LangGraph`. Eliminates DB query + graph recompilation per request. Pattern: same as `api/routes/models.py:22-24`. Add `invalidate_profile_cache()` helper + pre-warm in `lifespan` startup. Full plan in `.claude/plans/peppy-soaring-wand.md`. *(Session 43)*
- [ ] **Document SGLang prefix caching constraint** -- Add note in `docs/ARCHITECTURE.md` that system prompt prefix must stay stable (variable data like Mem0/history appended after, never injected into middle) so RadixAttention KV cache hits work. *(Session 43)*

## When PCCI Available (infra)

- [ ] **Swap LLM to SGLang** -- Change `LLM_BASE_URL` + `LLM_API_KEY` + `LLM_MODEL` in `.env` to point at PCCI SGLang endpoint. *(SOW 7.1, 7.4)*
- [ ] **Swap embeddings to TEI** -- Change `EMBEDDING_MODEL` + config in `embedder.py` to use TEI on PCCI. *(SOW 7.1, 7.4)*
- [ ] **Train voice clone with OpenAudio S1-mini** -- Requires 2-5 min clean audio samples from thought leader + PCCI GPU. Swap edge-tts in `routing_nodes.py`. *(SOW 2.2, 6.3)*
- [ ] **Remove all external API calls** -- After above 3 swaps, verify zero data leaves PCCI. *(SOW 7.1, 7.4)*

## Process (external dependencies)

- [ ] **Schedule 2-3 stakeholder review sessions** -- SOW assumes thought leader available for ~2 hours total of persona review. *(SOW 9.2, 8.6)*
- [ ] **Obtain full corpus materials** -- Current demo corpus is 70+ passages / 16 docs (ParaGPT). Full library of books, essays, interviews, transcripts needed. *(SOW 9.1)*
- [ ] **Obtain clean voice samples** -- 2-5 min, professional mic, quiet environment. Required for voice clone training. *(SOW 9.3)*
