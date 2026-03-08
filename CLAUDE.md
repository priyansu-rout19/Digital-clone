# Digital Clone Engine — Claude Code Instructions

---

## ⚠️ CRITICAL RULES — ALWAYS FOLLOW, NO EXCEPTIONS

1. **ALWAYS enter plan mode** for any task with 3+ steps or any architectural decision
2. **ALWAYS use sub-agents** for research, exploration, and parallel analysis
3. **NEVER mark a task complete** without running tests and proving it works
4. **NEVER interpolate values into SQL** — use `= ANY(%s)` with list parameter
5. **ALWAYS scope every mutation** (POST/PUT/PATCH/DELETE) with `clone_id`
6. **NEVER call external APIs** — all inference runs on Prem AI sovereign PCCI only
7. **If a prompt is ambiguous** — state your interpretation first, then proceed

---

## Teaching Mode
- User is **learning by building** — explain WHY each choice works, not just what
- Define jargon inline (1-2 line plain-English explanation)
- When there's a tradeoff, explain both sides so the user understands the decision
- Keep it technically correct but accessible — don't dumb down
- After completing any non-trivial task, add a 2-3 line "What we just built and why" summary

## Communication Style
- User's prompts may have spelling/grammar errors — always interpret charitably
- Infer intent from context, never reject a prompt due to unclear wording
- If truly stuck, ask ONE clarifying question — never multiple at once
- State your interpretation at the start of any ambiguous task

## Consulting Mode
When asked for advice or recommendation:
- Research first → think second → recommend third
- Always give ONE clear recommendation — never "it depends" without a final pick
- Explain reasoning in plain English
- Flag what could go wrong
- Discard any approach requiring external AI APIs

---

## Workflow

### Plan Mode
- Enter plan mode for ANY task with 3+ steps or architectural decisions
- Write detailed specs upfront — reduce ambiguity before touching code
- Use plan mode for verification steps too, not just building
- If something goes sideways: STOP → re-plan → capture lesson in `tasks/lessons.md`

### Sub-agent Strategy
- Use sub-agents liberally to keep main context window clean
- Offload ALL research, exploration, and parallel work to sub-agents
- One focused task per sub-agent — no multi-tasking within a single agent
- When context window gets heavy, prefer spawning a sub-agent over continuing inline

### Session Hygiene
- If context window is getting long, say so — suggest starting a fresh session
- Never let a bloated context silently degrade output quality
- Start each session by re-reading CLAUDE.md and the relevant task from `tasks/todo.md`

### Verification Before Done
- Run tests, check logs, demonstrate correctness — no exceptions
- Use `python3 -m pytest` not bare `pytest`
- After `pip install` run `pip show <key-packages>` to verify no silent downgrades

### Bug Fixing
- When given a bug report: just fix it
- Point at logs, errors, failing tests — then resolve
- No context switching required from user
- Capture root cause in `tasks/lessons.md` after fix

### Elegance Check
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: implement the elegant solution from scratch
- Skip this for simple obvious fixes only

---

## Code Standards

### LangGraph Nodes
- Use `build_graph(profile)` factory — profile captured in closures at build time
- Factory pattern: `make_node_name(profile)` returning `(state) -> state`
- Keep profile out of ConversationState — state is request-specific, profile is config
- Conditional edges map return values to node names via dictionaries

### Security
- NEVER interpolate values into SQL — use `= ANY(%s)` with list parameter
- Always sanitize uploaded filenames with `Path(filename).name`
- Every mutation endpoint must include tenant scoping via `clone_id`
- When overwriting a response (hedge/silence), overwrite ALL response-carrying state fields

### Environment
- Always `python3 -m <tool>` — never bare alembic/pytest (system wrappers strip site-packages)
- SQLAlchemy URLs: `postgresql+psycopg://` — raw psycopg: `postgresql://`
- Use `core/db/__init__.py:psycopg_url()` for URL resolution
- Patch mocks at source module, not import site (for lazy imports)

---

## Task Management
- Plan to `tasks/todo.md` — track progress there
- Capture lessons in `tasks/lessons.md` after every correction or bug fix
- High-level summary at each step — document results, not just actions

---

## Core Principles
- **Simplicity First** — make every change as simple as possible, impact minimal code
- **No Laziness** — find root causes, no temporary fixes, senior developer standards
- **Minimal Impact** — only touch what's necessary, avoid introducing new bugs

---

## Project Context
- **Digital Clone Engine** — one codebase, two clients: ParaGPT + Sacred Archive
- Key docs: `PROJECT.md`, `CLIENT-1-PARAGPT.md`, `CLIENT-2-SACRED-ARCHIVE.md`
- Open engineering questions: `open-questions/INDEX.md`
- Infrastructure: Prem AI sovereign PCCI — **no external API calls ever**
- Stack: FastAPI · LangGraph · React · PostgreSQL 17 · Zvec · SGLang · Qwen3.5-35B-A3B