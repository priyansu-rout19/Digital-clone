# Digital Clone Engine — Claude Code Instructions

## Teaching Mode

- User is **learning by building** — explain why each choice works, not just what it does
- Define jargon inline (1-2 line plain-English explanation)
- When there's a tradeoff, explain both sides so the user understands the decision
- Keep it technically correct but accessible — don't dumb down

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- Write detailed specs upfront to reduce ambiguity
- Use plan mode for verification steps, not just building
- If something goes sideways: STOP, re-plan, and capture the lesson in `tasks/lessons.md`

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- One task per subagent for focused execution

### 3. LangGraph Profile-Aware Nodes
- Use `build_graph(profile)` factory — profile captured in closures at build time
- If a node needs config, use a factory function: `make_node_name(profile)` returning `(state) -> state`
- Keep profile out of ConversationState (state is request-specific, profile is config)
- Conditional edges map return values to node names via dictionaries

### 4. Verification Before Done
- Never mark complete without proving it works — run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it — point at logs, errors, failing tests, then resolve
- Zero context switching required from the user

### 7. Dependency & Environment Verification
- After `pip install`: run `pip show <key-packages>` to verify no silent downgrades
- SQLAlchemy URLs use `postgresql+psycopg://`; raw psycopg needs `postgresql://` — use `core/db/__init__.py:psycopg_url()`
- Always `python3 -m <tool>` (not bare alembic/pytest) — system wrappers may strip site-packages
- Patch mocks at source module, not import site (for lazy imports)

### 8. Security by Default
- NEVER interpolate values into SQL — use `= ANY(%s)` with list parameter
- Always sanitize uploaded filenames with `Path(filename).name`
- Every mutation endpoint (POST/PUT/PATCH/DELETE) must include tenant scoping via `clone_id`
- When overwriting a response (hedge/silence), overwrite ALL response-carrying state fields

## Task Management

- Plan to `tasks/todo.md`, track progress, capture lessons in `tasks/lessons.md` after corrections
- High-level summary at each step; document results

## Core Principles

- **Simplicity First:** Make every change as simple as possible. Impact minimal code.
- **No Laziness:** Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact:** Changes should only touch what's necessary. Avoid introducing bugs.

## Project Context

- This is the **Digital Clone Engine** — one codebase powering two clients (ParaGPT + Sacred Archive)
- Key docs: `PROJECT.md` (technical spec), `CLIENT-1-PARAGPT.md`, `CLIENT-2-SACRED-ARCHIVE.md`
- Open engineering questions tracked in `open-questions/INDEX.md`
- All infrastructure runs on Prem AI's sovereign PCCI (no external API calls)
- Tech stack: FastAPI, LangGraph, React, PostgreSQL 17, Zvec, SGLang, Qwen3.5-35B-A3B
