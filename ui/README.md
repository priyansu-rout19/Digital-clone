# Digital Clone Engine — Frontend

**Stack:** Vite 6 + React 19 + TypeScript + Tailwind CSS v4
**Source files:** 29 (after S39 cleanup)

## Quick Start

```bash
cd ui
npm install
npm run dev       # Vite dev server on :5173
npx tsc --noEmit  # Type check (zero errors required)
npm run build     # Production build → ui/dist/
```

## Structure

```
ui/src/
  api/          → REST client (client.ts) + TypeScript interfaces (types.ts)
  hooks/        → useChat (WebSocket), useCloneProfile (profile fetch), useAudio (playback)
  components/   → 10 shared: MessageBubble, ChatInput, CitationCard, CitationGroupCard,
                  CitationList, CollapsibleCitations, AudioPlayer, ReasoningTrace,
                  ErrorBoundary, ModelSelector
  pages/        → paragpt/ (Landing, Chat), sacred-archive/ (Landing, Chat),
                  review/Dashboard, analytics/Dashboard
```

## Routing

`/:slug` auto-detects ParaGPT vs Sacred Archive via `profile.generation_mode`.
Analytics at `/:slug/analytics`. Vite proxies `/chat`, `/clone`, `/review`, `/ingest`, `/analytics`, `/users`, `/models` to `http://localhost:8000`.

## Design Themes

- **ParaGPT:** Near-black (#0d0d0d) + copper (#d08050), glassmorphism, sans-serif
- **Sacred Archive:** Charcoal (#2c2c2c) + gold (#c4963c), serif typography

## Full Documentation

See [docs/FRONTEND.md](../docs/FRONTEND.md) for complete file inventory, component details, design system specs, and session history.
