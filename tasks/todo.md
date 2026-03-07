# Digital Clone Engine -- SOW Gap Action Items

**Source:** `docs/PARAGPT-AUDIT-REPORT.md` (Session 40 audit against `client-sow-paragpt.md.pdf`)
**Created:** March 7, 2026

---

## Before Demo (hours)

- [ ] **Run existing eval tools** -- Execute `python scripts/evaluate_responses.py --clone paragpt-client --limit 50` to get persona fidelity + consistency baselines. *(SOW 8.2, 8.5)*
- [x] **Add voice toggle to Chat.tsx** -- SOW says "if they enable voice" (user choice). Currently always-on per profile. Add UI on/off toggle. *(SOW 3.7, Story 2)*
- [ ] **Add prediction hedging to system prompt** -- Add instruction distinguishing "interpretation" from "prediction" in `generation_nodes.py:44-63`. *(SOW Story 6)*

## Before Production (days)

- [ ] **Build 50-query eval suite** -- Create `tests/eval_suite_paragpt.py` with 50+ predefined queries covering all topic areas. Measure citation accuracy, persona fidelity, consistency. *(SOW 4.9, 8.1, 8.2, 8.5)*
- [ ] **Build 30-query foundation gate script** -- Create gate script that runs 30+ queries and produces pass/fail on >90% citation accuracy + >80% persona fidelity. *(SOW 4.1 gate)*
- [ ] **Enable encryption at rest** -- PostgreSQL TDE or pgcrypto column encryption for corpus data, messages, and analytics. Currently all plaintext. *(SOW 7.2)*
- [ ] **Add corpus gap detection** -- Track `silence_triggered` queries by topic, cluster, and report coverage gaps for corpus expansion. *(SOW 6.4)*

## When PCCI Available (infra)

- [ ] **Swap LLM to SGLang** -- Change `LLM_BASE_URL` + `LLM_API_KEY` + `LLM_MODEL` in `.env` to point at PCCI SGLang endpoint. *(SOW 7.1, 7.4)*
- [ ] **Swap embeddings to TEI** -- Change `EMBEDDING_MODEL` + config in `embedder.py` to use TEI on PCCI. *(SOW 7.1, 7.4)*
- [ ] **Train voice clone with OpenAudio S1-mini** -- Requires 2-5 min clean audio samples from thought leader + PCCI GPU. Swap edge-tts in `routing_nodes.py`. *(SOW 2.2, 6.3)*
- [ ] **Remove all external API calls** -- After above 3 swaps, verify zero data leaves PCCI. *(SOW 7.1, 7.4)*

## Process (external dependencies)

- [ ] **Schedule 2-3 stakeholder review sessions** -- SOW assumes thought leader available for ~2 hours total of persona review. *(SOW 9.2, 8.6)*
- [ ] **Obtain full corpus materials** -- Current demo corpus is 63 passages / 13 docs. Full library of books, essays, interviews, transcripts needed. *(SOW 9.1)*
- [ ] **Obtain clean voice samples** -- 2-5 min, professional mic, quiet environment. Required for voice clone training. *(SOW 9.3)*
