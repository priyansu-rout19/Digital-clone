# Documentation

Reference library for the Digital Clone Engine project.

## Quick Navigation

| Folder | Purpose |
|---|---|
| **ARCHITECTURE.md** | Main technical specification (4 layers, design principles) |
| **CLIENTS/** | Client-specific SOWs and configuration |
| **COMPONENTS/** | Engineering specs for each component (01-04) |
| **RESEARCH/** | Open questions, decisions, and research notes |

## For Quick Onboarding

1. Read **ARCHITECTURE.md** (20 min) — understand the system design
2. Skim **CLIENTS/** — see how two very different clients use the same engine
3. Browse **COMPONENTS/** — understand what's been built and what's next

## Key Concepts

- **One Engine, Two Profiles** — All behavioral differences between ParaGPT and Sacred Archive are driven by `CloneProfile` config, not code branches
- **Profile-First Architecture** — Every node in LangGraph reads the profile and adjusts behavior at runtime
- **No Code Branches** — 100% unified codebase for both clients; config handles all variation
