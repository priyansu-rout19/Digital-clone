# Digital Clone Engine — UI/UX Design Reference

**Status:** MVP designs approved (March 5, 2026)
**Tool:** Variant (AI design tool)
**Inspiration:** Delphi.ai (profile card pattern, suggested questions) — own identity, not a copy

---

## Screens Designed

### 1. ParaGPT Chat Page (Landing)
- Centered profile card: avatar, name, bio, topic tags
- "Ask me about" starter question cards (3 cards in a row)
- Sticky input bar at bottom (mic + send)
- Color: Dark navy base with teal (#00d4aa) accents
- Glass-morphism cards with transparency effects
- **MVP Note:** Background will be refined to lighter glassmorphism in future iterations

### 2. Sacred Archive Seeker Chat (Landing)
- "SACRED ARCHIVE" title with sacred geometry icon
- Tagline: "Preserved Teachings · Verified Words · Living Wisdom"
- Italic serif description text
- Three tier selector cards: Devotee / Friend / Follower
- "CONTINUE TO ARCHIVE" button (gold accent)
- Suggested questions in italic below
- Input bar: "Ask from the teachings..."
- Color: Deep brown/charcoal with gold (#c4963c) accents
- Warm, scholarly, reverent feel

### 3. Sacred Archive Review Dashboard
- **Not yet designed** — will create after MVP chat pages are built
- Spec: 3-column layout (queue | detail | actions)
- See Prompt 3 in plan file for full spec

---

## Design System (Extracted from Mockups)

### ParaGPT
| Element | Value |
|---|---|
| Primary bg | Dark navy (#0a1628) |
| Accent | Teal (#00d4aa) |
| Card bg | Semi-transparent dark with glass blur |
| Text | White / light gray |
| Tags | Teal border pills |
| Send button | Solid teal circle |
| Font | Sans-serif (Inter / system) |
| Border radius | 16px cards, 20px input |

### Sacred Archive
| Element | Value |
|---|---|
| Primary bg | Deep brown/charcoal (#2c2c2c) |
| Accent | Muted gold/saffron (#c4963c) |
| Card bg | Dark charcoal with subtle border |
| Text | Gold headings, ivory body (#faf8f0) |
| Title font | Display serif (all-caps) |
| Body font | Italic serif for descriptions |
| Tier cards | Dark with gold/silver/simple borders |
| Send button | Gold circle |
| Border radius | 12px cards |

---

## Conversation State (To Design Next)

### ParaGPT Chat Active
- Profile collapses to compact glass top bar (avatar + name + online dot)
- User messages: solid teal gradient bubbles (right-aligned)
- Clone responses: glass-effect bubbles (left-aligned)
- Mini audio player: glass pill with waveform
- Citation cards: collapsible, glass, teal accent stripe
- Confidence pill: "92% confident" small badge

### Sacred Archive Chat Active
- Top bar: "Sacred Archive" + tier badge ("Viewing as: Devotee")
- User questions: right-aligned, minimal
- Teaching quotes: large decorative quotation marks, serif font
- Full provenance block under each quote
- "Listen to original teaching" button (if recording exists)
- Sacred silence state for uncovered topics

---

## Future Iterations (Post-MVP)

- [ ] Lighter glassmorphism background for ParaGPT (gradient orbs, frosted glass)
- [ ] Mobile responsive versions of both chat pages
- [ ] Dark mode toggle for review dashboard
- [ ] Loading/typing animation states
- [ ] Error states (server unavailable)
- [ ] "Welcome back" returning user banner (ParaGPT)
- [ ] Sacred silence state mockup (Sacred Archive)

---

## Variant Prompts

All prompts saved in: `/home/priyansurout/.claude/plans/magical-meandering-nygaard.md`
- Prompt 1: ParaGPT original (dark)
- Prompt 1B: ParaGPT glassmorphism landing (light, detailed)
- Prompt 1C: ParaGPT conversation state
- Prompt 2: Sacred Archive seeker chat
- Prompt 3: Sacred Archive review dashboard

---

## API Endpoints the Frontend Will Consume

| Endpoint | Method | Used By |
|---|---|---|
| `/health` | GET | Health check |
| `/clone/{slug}/profile` | GET | Profile card (name, bio, avatar, voice mode) |
| `/chat/{slug}` | POST | Sync chat (fallback) |
| `/chat/{slug}/ws` | WebSocket | Real-time streaming chat |
| `/review/{slug}` | GET | Review queue list |
| `/review/{slug}/{id}` | PATCH | Approve/reject/edit |
| `/ingest/{slug}` | POST | Document upload (admin) |
