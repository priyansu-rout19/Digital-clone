# Digital Clone Engine — Frontend Documentation

**Last updated:** Session 20B (March 5, 2026)
**Tech stack:** Vite 6 + React 19 + TypeScript + Tailwind CSS v4
**Entry point:** `ui/src/main.tsx` | **Build:** `cd ui && npm run build`

---

## Architecture

```
ui/src/
  api/          → Backend communication (REST + WebSocket)
  hooks/        → Reusable React hooks (chat, audio, profile)
  components/   → Shared UI components (6 files)
  pages/        → Route-specific pages (ParaGPT, Sacred Archive, Review)
  themes/       → Design token exports (not currently used at runtime)
  index.css     → Global styles + glass morphism + markdown rendering
  App.tsx       → Router + clone profile loader + page dispatch
  main.tsx      → React root with StrictMode
```

**Routing:** `/:slug` auto-detects ParaGPT vs Sacred Archive via `profile.generation_mode`
**Proxy:** Vite dev server proxies `/chat`, `/clone`, `/review`, `/ingest` to `http://localhost:8000`

---

## File Inventory (23 source files)

### API Layer (`ui/src/api/`)

| File | Purpose |
|------|---------|
| `types.ts` | 21 TypeScript interfaces mirroring backend models (ChatMessage, CloneProfile, WSMessage, etc.) |
| `client.ts` | 4 REST functions with 15s AbortController timeout + API key header |
| `websocket.ts` | WebSocket manager class (unused — `useChat` hook handles WS directly) |

### Hooks (`ui/src/hooks/`)

| File | Purpose |
|------|---------|
| `useChat.ts` | WebSocket chat hook — sends queries, receives progress events + response. 60s timeout resets on each progress event. Cleanup on unmount. |
| `useCloneProfile.ts` | Fetches `CloneProfile` from `/clone/{slug}/profile` on mount |
| `useAudio.ts` | Base64 audio decode → `<Audio>` playback. Object URL cleanup on unmount. |

### Components (`ui/src/components/`)

| File | Purpose |
|------|---------|
| `MessageBubble.tsx` | Chat message rendering. Markdown via `react-markdown`. Typewriter animation for latest assistant message. Responsive widths. |
| `ChatInput.tsx` | Text input + send button. Spinner when loading. Enter to send, Shift+Enter for newline. |
| `CitationCard.tsx` | Collapsible citation card. Shows source name, expandable chunk text. ParaGPT (teal) / Sacred Archive (gold) variants. |
| `NodeProgress.tsx` | Animated dots showing current LangGraph node ("Searching knowledge base..."). |
| `AudioPlayer.tsx` | Play/pause button + progress bar for voice responses. |
| `ErrorBoundary.tsx` | React class component catching render errors with "Try Again" button. |

### Pages (`ui/src/pages/`)

| File | Purpose |
|------|---------|
| `paragpt/Landing.tsx` | Profile card (avatar, name, bio, topic tags), 3 starter questions, sticky input bar |
| `paragpt/Chat.tsx` | Chat view — top bar with avatar, message list, citations, audio, input bar |
| `sacred-archive/Landing.tsx` | Tier selector (Devotee/Friend/Follower), "Continue to Archive" button |
| `sacred-archive/Chat.tsx` | Chat view — serif quotes with gold accents, provenance citations |
| `review/Dashboard.tsx` | 3-column review queue (pending/approved/rejected). Mobile: stacked columns. |

### Other Files

| File | Purpose |
|------|---------|
| `App.tsx` | React Router, ErrorBoundary wrapper, ClonePage (loads profile, dispatches to landing/chat) |
| `main.tsx` | `createRoot` + `StrictMode` |
| `index.css` | Tailwind import, `@theme` color tokens, `.glass` / `.glass-sacred` utilities, `.markdown-body` styles, scrollbar styling |
| `themes/paragpt.ts` | Design token export (colors, fonts) |
| `themes/sacred-archive.ts` | Design token export (colors, fonts) |

---

## Design System

### ParaGPT Theme
- **Background:** `#0a1628` (dark navy)
- **Accent:** `#00d4aa` (teal) / `#00b894` (teal dark, hover)
- **Cards:** Glass morphism — `rgba(16, 32, 56, 0.6)` + 16px blur
- **Text:** White primary, `#94a3b8` (slate) secondary
- **Font:** Inter, system-ui, sans-serif

### Sacred Archive Theme
- **Background:** `#2c2c2c` (charcoal)
- **Accent:** `#c4963c` (gold) / `#a67c2e` (gold dark)
- **Cards:** `rgba(44, 44, 44, 0.8)` + 12px blur, gold border
- **Text:** `#faf8f0` (ivory) primary, gold accents
- **Font:** Playfair Display, Georgia, serif

---

## Key Patterns

### WebSocket Protocol
```
Client → Server: { query, user_id, access_tier }
Server → Client: { type: "progress", node: "query_analyzer" }  // repeated per node
Server → Client: { type: "response", response, confidence, cited_sources, ... }
Server → Client: { type: "error", message: "..." }  // on failure
```

Timeout: 60s per node (resets on each progress event). Total pipeline can run as long as needed as long as nodes keep reporting progress.

### Typewriter Animation
`MessageBubble` reveals assistant text at 3 chars/12ms (~250 chars/sec). Only animates the latest message — older messages render instantly. Uses `useEffect` with `setInterval`, no ref guard (React StrictMode compatible).

### Markdown Rendering
`react-markdown` renders LLM output. Custom `.markdown-body` CSS:
- Paragraph spacing (0.75rem)
- Bold → white text, 600 weight
- Blockquotes → teal left border
- Code → translucent background
- Headers scaled down to 0.95em (prevented in prompt but handled gracefully)

### Avatar
Local image at `ui/public/avatars/parag-khanna.png`. Hardcoded in Landing.tsx and Chat.tsx (ignores `profile.avatar_url` which may be stale in DB).

---

## Dependencies

```json
{
  "react": "^19.2.0",
  "react-dom": "^19.2.0",
  "react-router-dom": "^7.13.1",
  "react-markdown": "^latest",
  "tailwindcss": "^4.2.1"
}
```

Dev: `typescript`, `@vitejs/plugin-react`, `@types/react`, `eslint`

---

## Build & Dev

```bash
# Development
cd ui && npm run dev          # Vite dev server on :5173

# Type check
cd ui && npx tsc --noEmit     # Zero errors required

# Production build
cd ui && npm run build        # Output: ui/dist/ (56+ modules)
```

---

## Session History

| Session | Changes |
|---------|---------|
| **19** | Initial scaffold — 21 source files, Vite+React+TS+Tailwind, all pages, hooks, components |
| **20** | Polish — ErrorBoundary, WS resilience (30s timeout), mobile responsive, loading states, safe-area padding |
| **20B** | Avatar photo fix (hardcoded path), WS timeout fix (reset on progress, bumped to 60s), typewriter animation (StrictMode fix), react-markdown rendering, markdown CSS, LLM prompt rewrite (conversational tone, max_tokens=500) |

---

## Known Issues / Future Work

- `websocket.ts` class exists but is unused — `useChat` handles WS directly
- Avatar hardcoded to Parag Khanna — should use `profile.avatar_url` once DB is updated
- Sacred Archive Chat.tsx doesn't use react-markdown (plain text + quotes is intentional for mirror_only mode)
- No suggested follow-up questions (would need backend `suggested_questions` field)
- No inline superscript citations (citations are separate cards below message)
