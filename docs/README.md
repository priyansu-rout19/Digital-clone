# Documentation

Reference library for the Digital Clone Engine project. Last updated: Session 39.

## Quick Navigation

| Document | Purpose |
|---|---|
| **ARCHITECTURE.md** | Main technical specification (4 layers, 19-node pipeline, design principles) |
| **FRONTEND.md** | Frontend architecture, file inventory (29 files), design system |
| **STUBS-AND-MOCKS.md** | 3 remaining PCCI-blocked stubs + resolved items history |
| **MANAGER-DIRECTIVES.md** | Management priorities, OSS model evaluation plan |
| **PARAGPT-AUDIT-REPORT.md** | Line-by-line SOW compliance audit for ParaGPT (Session 40) |
| **SACRED-AUDIT-REPORT.md** | Line-by-line SOW compliance audit for Sacred Archive (Session 40) |
| **CLIENTS/** | Original SOW contracts (immutable source of truth) |
| **COMPONENTS/** | Engineering specs for each component (01-07) |
| **RESEARCH/** | Open questions, locked decisions, and research notes |
| **archive/** | Retired docs (DEVELOPMENT-PLAN, DESIGN-REFERENCE, SOW-AUDIT) |

## For Quick Onboarding

1. Read **ARCHITECTURE.md** (20 min) — understand the system design
2. Skim **CLIENTS/** — see how two very different clients use the same engine
3. Browse **COMPONENTS/** — understand what's been built and what's next
4. Check **PARAGPT-AUDIT-REPORT.md** / **SACRED-AUDIT-REPORT.md** — current SOW compliance

## Key Concepts

- **One Engine, Two Profiles** — All behavioral differences between ParaGPT and Sacred Archive are driven by `CloneProfile` config, not code branches
- **Profile-First Architecture** — Every node in LangGraph reads the profile and adjusts behavior at runtime
- **No Code Branches** — 100% unified codebase for both clients; config handles all variation
