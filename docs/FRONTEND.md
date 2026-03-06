# Digital Clone Engine — Frontend Documentation

**Last updated:** Session 31 (March 6, 2026)
**Tech stack:** Vite 6 + React 19 + TypeScript + Tailwind CSS v4
**Entry point:** `ui/src/main.tsx` | **Build:** `cd ui && npm run build`

---

## Architecture

```
ui/src/
  api/          → Backend communication (REST + WebSocket)
  hooks/        → Reusable React hooks (chat, audio, profile)
  components/   → Shared UI components (10 files)
  pages/        → Route-specific pages (ParaGPT, Sacred Archive, Review, Analytics)
  themes/       → Design token exports (not currently used at runtime)
  index.css     → Global styles + glass morphism + markdown rendering
  App.tsx       → Router + clone profile loader + page dispatch
  main.tsx      → React root with StrictMode
```

**Routing:** `/:slug` auto-detects ParaGPT vs Sacred Archive via `profile.generation_mode`. Analytics at `/:slug/analytics`.
**Proxy:** Vite dev server proxies `/chat`, `/clone`, `/review`, `/ingest`, `/analytics`, `/users` to `http://localhost:8000`

---

## File Inventory (29 source files)

### API Layer (`ui/src/api/`)

| File | Purpose |
|------|---------|
| `types.ts` | 22 TypeScript interfaces mirroring backend models (ChatMessage, CloneProfile, WSMessage, TraceRecord, etc.). Shared `NODE_LABELS` (28 entries) + `NODE_DISPLAY_NAMES` (22 entries) constants. |
| `client.ts` | 5 REST functions (cloneProfile, chat, review, reviewAction, analytics) with 15s AbortController timeout + API key header |
| `websocket.ts` | WebSocket manager class (unused — `useChat` hook handles WS directly) |

### Hooks (`ui/src/hooks/`)

| File | Purpose |
|------|---------|
| `useChat.ts` | WebSocket chat hook — sends queries, receives progress events + response. 60s timeout resets on each progress event. Cleanup on unmount. |
| `useCloneProfile.ts` | Fetches `CloneProfile` from `/clone/{slug}/profile` on mount |
| `useAudio.ts` | Base64 audio decode → `<Audio>` playback. `seek(percentage)` for clickable progress bar. Object URL cleanup on unmount. |

### Components (`ui/src/components/`)

| File | Purpose |
|------|---------|
| `MessageBubble.tsx` | Chat message rendering. Markdown via `react-markdown`. Typewriter animation for latest assistant message. Copy-to-clipboard icon on hover (green checkmark feedback). Full-width assistant bubbles, constrained user bubbles with copper glow. |
| `ChatInput.tsx` | Textarea with auto-resize (max 4 rows). Enter sends, Shift+Enter newline. Character counter (2000 limit, red warning). Spinner when loading. |
| `CitationCard.tsx` | Single citation card with `passageOnly` mode for use inside groups. Shows source name, expandable chunk text. ParaGPT (copper) / Sacred Archive (gold) variants. |
| `CitationGroupCard.tsx` | Groups multiple passages from same document. Expandable with passage count badge. Uses CitationCard in passageOnly mode. |
| `CitationList.tsx` | Groups citations by `doc_id` (or `source_title` fallback). Renders CitationGroupCard for multi-passage sources, CitationCard for singles. |
| `CollapsibleCitations.tsx` | Pill-shaped "N sources cited" toggle with book icon + chevron. Collapsed by default. Wraps CitationList. |
| `NodeProgress.tsx` | Animated dots showing current LangGraph node ("Searching knowledge base..."). **Unused since Session 31** — both clients now use inline thinking bubble. |
| `AudioPlayer.tsx` | Play/pause button + clickable/seekable progress bar for voice responses. |
| `ReasoningTrace.tsx` | Collapsible "{N} pipeline steps" pill with vertical timeline. Shows per-node metrics (retrieval confidence, reranked flag, citation count, etc.). `TraceRecord` type from `types.ts`. Accumulated via ref in `useChat.ts`. Session 28. |
| `ErrorBoundary.tsx` | React class component catching render errors with "Try Again" button. |

### Pages (`ui/src/pages/`)

| File | Purpose |
|------|---------|
| `paragpt/Landing.tsx` | Profile card (avatar, name, bio, topic tags), 3 starter questions (corpus-aligned: ASEAN, infrastructure, + irrelevant hedge demo), sticky input bar |
| `paragpt/Chat.tsx` | Chat view — conversation-start intro (centered avatar+name, scrolls with messages), message list, collapsible citations, audio, thinking bubble (animated dots in glass bubble), input bar with 24px bottom spacing |
| `sacred-archive/Landing.tsx` | Tier selector (Devotee/Friend/Follower), "Continue to Archive" button |
| `sacred-archive/Chat.tsx` | Chat view — serif quotes with gold accents, provenance citations, thinking bubble, suggested topic pills, new conversation button |
| `review/Dashboard.tsx` | 3-column review queue (pending/approved/rejected). Edit mode (textarea + Save/Cancel), keyboard shortcuts (a/r/e + arrows), cited sources with `CollapsibleCitations`. Mobile: stacked columns. |
| `analytics/Dashboard.tsx` | Monitoring dashboard: stat cards (total queries, avg confidence, avg latency, silence rate), queries per day bar chart, top intent classes. Route: `/:slug/analytics`. |

### Other Files

| File | Purpose |
|------|---------|
| `App.tsx` | React Router, ErrorBoundary wrapper, ClonePage (loads profile, dispatches to landing/chat), styled 404 page, handleNewConversation |
| `main.tsx` | `createRoot` + `StrictMode` |
| `index.css` | Tailwind import, `@theme` color tokens (copper + gold), `.glass` / `.glass-sacred` utilities, `.hide-scrollbar` utility, `.markdown-body` styles, scrollbar styling |
| `themes/paragpt.ts` | Design token export (colors, fonts) |
| `themes/sacred-archive.ts` | Design token export (colors, fonts) |

---

## Design System

### ParaGPT Theme
- **Background:** `#0d0d0d` (near-black charcoal)
- **Accent:** `#d08050` (warm copper) / `#b06838` (copper dark, hover)
- **Cards:** Glass morphism — `rgba(30, 30, 30, 0.75)` + 16px blur, subtle `rgba(255,255,255,0.08)` border
- **User bubbles:** Copper gradient with `shadow-[0_2px_12px_rgba(208,128,80,0.3)]` glow
- **Text:** White primary, `#94a3b8` (slate) secondary, `text-gray-100` for assistant messages
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
- Blockquotes → copper left border
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
| **22** | Analytics dashboard page (stat cards, bar charts, intent breakdown). `AnalyticsSummary` type + `getAnalytics()` API function. Route `/:slug/analytics`. Vite proxy for `/analytics` and `/users`. |
| **27** | Complete UI/UX overhaul — citation grouping (CitationGroupCard, CitationList), collapsible citations (CollapsibleCitations), hidden scrollbar, wider layout (max-w-3xl), dark theme (#0d0d0d bg, #d08050 copper accent), header-less chat with conversation-start intro, thinking bubble, improved spacing |
| **28** | P1 SOW gaps: review EDIT action (textarea + Save/Cancel), keyboard shortcuts (a/r/e + arrows + `<kbd>` hints), cited sources in review (CollapsibleCitations), dynamic topic suggestions. Reasoning trace panel (ReasoningTrace.tsx + TraceRecord type + backend _extract_trace_data). 29 source files. |
| **30** | Landing page starter questions updated for demo corpus alignment ("What is the future of ASEAN?", "How does infrastructure shape global power?", "What is your best recipe for chocolate cake?" for hedge demo) |
| **31** | Frontend polish (9 fixes): suggested topic pills, Sacred Archive thinking bubble, consolidated node labels (types.ts), new conversation button, character counter (2000 limit), styled 404 page, copy-to-clipboard on responses, textarea multi-line input, audio seek bar |

---

## Known Issues / Future Work

- `websocket.ts` class exists but is unused — `useChat` handles WS directly
- Avatar hardcoded to Parag Khanna — should use `profile.avatar_url` once DB is updated
- Sacred Archive Chat.tsx doesn't use react-markdown (plain text + quotes is intentional for mirror_only mode)
- No inline superscript citations (citations are separate cards below message)
- Analytics dashboard has no real-time refresh — manual page reload needed
- ~~Reasoning trace panel not yet built~~ ✅ DONE Session 28
- ~~No suggested follow-up questions~~ ✅ DONE Session 28 (dynamic topic suggestions from passages)
- `NodeProgress.tsx` is now unused — both clients switched to inline thinking bubble (Session 31). Consider removing.
- `websocket.ts` class is also unused — `useChat` handles WS directly. Consider removing.
