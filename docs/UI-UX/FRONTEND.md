# ParaGPT Design System

> Reference document for building and auditing ParaGPT UI.
> Last updated: 2026-03-08 (Session 40 — research-validated, alphageo.ai audit + 2026 trend alignment)

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Colour Palette](#2-colour-palette)
3. [Typography](#3-typography)
4. [Spacing & Layout](#4-spacing--layout)
5. [Glass Morphism System](#5-glass-morphism-system)
6. [Component Patterns](#6-component-patterns)
7. [Animation & Motion](#7-animation--motion)
8. [Shadows](#8-shadows)
9. [Iconography](#9-iconography)
10. [Anti-Patterns](#10-anti-patterns)
11. [Accessibility](#11-accessibility)
12. [Reference Notes: alphageo.ai → ParaGPT](#12-reference-notes-alphageoai--paragpt)
13. [2026 AI Chat Interface Trends — Alignment Audit](#13-2026-ai-chat-interface-trends--alignment-audit)

---

## 1. Design Philosophy

### Brand Positioning

ParaGPT is the digital clone of a globally recognized thought leader. The interface must feel **intellectual, sovereign, and transparent** — never playful, never generic.

The core principle: **the persona is the product, not the interface.** Every visual decision serves one goal — get out of the way so the user engages with the mind behind the words, not the chrome around them.

### alphageo.ai Influence

Parag Khanna's alphageo.ai sets the brand direction: minimalist restraint, content-first layout, analytical positioning. alphageo.ai uses black/white/cyan. We keep the restraint but replace cyan with **copper** — warmth over cold tech.

Copper is a material metaphor: it's premium, ages beautifully, and signals warmth without sacrificing sophistication. Blue says "tech company." Copper says "singular mind you can trust."

### Design Tenets

1. **Content > Chrome** — if a UI element doesn't serve the conversation, remove it
2. **Restraint > Expression** — no decorative animation, no gradient flourishes, no emoji in chrome
3. **Transparency > Mystery** — show citations, show reasoning traces, show confidence hedging
4. **Intimacy > Scale** — tight content widths (640-768px), generous whitespace, one conversation at a time

---

## 2. Colour Palette

All tokens are defined in `ui/src/index.css` (`@theme` block) and `ui/src/themes/paragpt.ts`.

### Core Tokens

| Token | Value | Usage |
|---|---|---|
| `--color-para-navy` | `#0d0d0d` | Page background |
| `--color-para-teal` | `#d08050` | Primary accent — buttons, links, active borders |
| `--color-para-teal-dark` | `#b06838` | Hover/pressed states |
| `--color-para-card` | `rgba(28, 28, 28, 0.6)` | Glass card backgrounds |
| `--color-para-card-hover` | `rgba(38, 38, 38, 0.8)` | Card hover state |
| `--color-glass-border` | `rgba(255, 255, 255, 0.08)` | Subtle glass borders (`.glass` class uses 0.08; `@theme` declares 0.1 — prefer 0.08 in components) |

> **Note:** The CSS variable names use "teal" for historical reasons. The actual colour is copper (`#d08050`). Treat all `para-teal` references as "ParaGPT copper accent."

### Text Colours

| Role | Value | Usage |
|---|---|---|
| Primary | `#ffffff` | Headings, body text, strong emphasis |
| Secondary | `#cbd5e1` (slate-300) | Italic/emphasis in markdown |
| Muted | `#94a3b8` (slate-400) | Bios, captions, blockquotes |
| Dimmed | `#64748b` (slate-500) | Timestamps, placeholders, metadata |
| Subdued | `#475569` (slate-600) | Near-invisible metadata, inactive icons |

### Semantic Colours

| Role | Value | Usage |
|---|---|---|
| Success | `#22c55e` (green-500) | Approved citations, verified, active step dots |
| Warning | `#f59e0b` (amber-500) | Pending review, hedging indicator, star ratings |
| Error | `#ef4444` (red-500) | Rejected, failures, char-over-limit |
| Error surface | `red-900/90` | Error banner background |

### Proposed Additions

| Token | Value | Usage |
|---|---|---|
| `--color-para-copper-glow` | `rgba(208, 128, 80, 0.15)` | Subtle accent backgrounds (topic pills, suggested actions) |
| `--color-para-surface` | `#1a1a1a` | Elevated surfaces without blur (settings panels, sidebars) |

These are not yet in the codebase. Add them to the `@theme` block when needed.

---

## 3. Typography

### Font Stack

```css
font-family: 'Inter', system-ui, -apple-system, sans-serif;
```

Defined in `ui/src/index.css` on `body` and in `paragpt.ts` theme object.

**Why Inter:** Neutral, highly legible at small sizes (13-14px chat text), excellent across weights, pairs naturally with analytical/data-driven brands. No character — lets content speak.

### Type Scale

| Size | px | Usage |
|---|---|---|
| Display | 42 | — (reserved, not currently used) |
| H1 | 32 | — (reserved) |
| H2 | 24 | Profile name on landing (`text-2xl`) |
| H3 | 18 | Error titles (`text-lg`) |
| Body | 16 | Default body text |
| UI / Chat | 14 | Chat messages, input fields, menu items (`text-sm`) |
| Caption | 13 | Citations, node labels, pills (`text-xs` at 12px or custom 13px) |
| Micro | 12 | Timestamps, char counters, metadata (`text-xs`) |

### Weights

| Weight | Token | Usage |
|---|---|---|
| 400 | Regular | Body text, chat messages |
| 500 | Medium | Labels, citation titles, UI controls (`font-medium`) |
| 600 | Semibold | Strong emphasis in markdown, widget titles (`font-semibold`) |
| 700 | Bold | Profile name, markdown headings (`font-bold`) |

### Line Heights

| Context | Value | Reasoning |
|---|---|---|
| Headings | 1.2 | Tight, compact, authoritative |
| Body / UI | 1.5 | Standard readability |
| Chat messages | `leading-relaxed` (1.625) | Extra air for scan-reading long responses |
| Markdown paragraphs | 0.75rem bottom margin | Consistent block spacing |

### Letter Spacing

Normal everywhere. Inter's built-in metrics handle optical spacing — no manual tracking needed.

---

## 4. Spacing & Layout

### Base Unit

4px (Tailwind's default spacing scale). All spacing should be multiples of 4.

### Page Widths

| Context | Width | Tailwind |
|---|---|---|
| Landing page | 640px | `max-w-[640px]` |
| Chat messages | 768px | `max-w-3xl` |
| Input bar (landing) | 640px | `max-w-[640px]` |
| Input bar (chat) | 768px | `max-w-3xl` |

### Component Spacing

| Element | Value | Tailwind |
|---|---|---|
| Message gap | 16px | `mb-4` |
| Section gap | 32px | `mt-8` |
| Card padding | 24px | `p-6` (landing profile card) |
| Chat bubble padding | 16px × 12px | `px-4 py-3` |
| Input bar padding | 8px | `p-2` (inner), `p-4` (outer wrapper) |
| Pill padding | 12px × 4px | `px-3 py-1` |
| Button icon size | 40px × 40px | `w-10 h-10` |
| Avatar (landing) | 80px | `w-20 h-20` |
| Avatar (chat header) | 48px | `w-12 h-12` |
| Starter question grid gap | 12px | `gap-3` |
| Topic tag gap | 8px | `gap-2` |

### Responsive Behaviour

| Breakpoint | Behaviour |
|---|---|
| Mobile (< 640px) | Full-width, `px-4` page padding, single-column starter grid |
| SM (640px+) | 3-column starter grid, message max-width 80% |
| MD (768px+) | Message max-width 75% |

### Border Radius

| Element | Value | Tailwind |
|---|---|---|
| Cards / Profile | 16px | `rounded-[16px]` or `rounded-2xl` |
| Chat bubbles | 16px | `rounded-2xl` |
| Input bar | 20px | `rounded-[20px]` |
| Buttons (circle) | Full | `rounded-full` |
| Pills / Tags | Full | `rounded-full` |
| Dropdown menus | 12px | `rounded-xl` |

---

## 5. Glass Morphism System

### `.glass` Class (defined in `index.css`)

```css
.glass {
  background: rgba(30, 30, 30, 0.75);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}
```

### When to Use Glass

- **Yes:** Profile cards, input bars, AI message bubbles, model selector dropdowns, audio player, reasoning trace containers
- **No:** User message bubbles (use gradient instead), inline text elements, backgrounds behind backgrounds (double-blur kills performance), navigation bars

### Glass Rules

1. Never stack two `.glass` elements directly on top of each other — the blur compounds and looks muddy
2. Always pair with `rounded-2xl` or `rounded-[20px]` — sharp corners on glass look wrong
3. Glass elements should float over `#0d0d0d` background — they lose definition over lighter surfaces
4. On mobile, glass still works because `#0d0d0d` has no texture to blur through — the effect is purely about the translucent depth

---

## 6. Component Patterns

### 6.1 Message Bubble

**Source:** `ui/src/components/MessageBubble.tsx`

#### User Message (right-aligned)
- Alignment: `flex justify-end`
- Max width: 90% mobile, 80% SM, 75% MD
- Background: `bg-gradient-to-r from-para-teal to-para-teal-dark`
- Shadow: `0 2px 12px rgba(208, 128, 80, 0.3)` — warm copper glow
- Padding: `px-4 py-3`
- Radius: `rounded-2xl`
- Text: `text-white text-sm`

#### AI Message (left-aligned, full width)
- Alignment: `flex justify-start`, `w-full`
- Background: `.glass` class
- Padding: `px-4 py-3`
- Radius: `rounded-2xl`
- Text: `text-gray-100 text-sm leading-relaxed`
- Copy button: appears on hover (`opacity-0 group-hover:opacity-100`), top-right corner

#### Confidence Badge
- Position: inline after message
- Style: `text-xs px-2 py-0.5 rounded-full bg-para-teal/20 text-para-teal`

#### Typewriter Effect
- 12ms interval, +3 characters per tick
- Smooth character-by-character reveal for AI responses

#### Anti-patterns
- Never use coloured backgrounds for AI bubbles (glass only)
- Never show raw confidence scores — use verbal hedging in text

---

### 6.2 Chat Input

**Source:** `ui/src/components/ChatInput.tsx`

- Container: `.glass rounded-[20px] p-2`
- Textarea: transparent background, `px-4 py-3`, `text-sm`, max-height 120px (auto-grows)
- Send button: `w-10 h-10 rounded-full bg-para-teal`, white arrow icon
- Char counter: appears near limit, `text-xs`, red at 2000+
- Loading state: send button shows `animate-spin` border spinner
- IME-safe: composition guard + 50ms debounce for CJK input

---

### 6.3 Citation Card

**Source:** `ui/src/components/CitationCard.tsx`

- Left border: `border-l-2 border-para-teal`
- Padding: `pl-3 py-1`
- Title: `text-xs text-gray-400 font-medium`
- Expand/collapse: chevron icon, `transition-transform` (rotates 180deg)
- Expanded content: `text-xs text-gray-500` for chunk text
- Metadata: `text-xs text-gray-400 mt-1`

---

### 6.4 Citation Group Card

**Source:** `ui/src/components/CitationGroupCard.tsx`

- Same left border pattern as CitationCard
- Count badge: `text-xs px-1.5 py-0.5 rounded-full bg-para-teal/20 text-para-teal`
- Expanded list: `ml-2 border-l border-gray-700 pl-3` — nested indentation
- Contains CitationCard children in `passageOnly` mode

---

### 6.5 Audio Player

**Source:** `ui/src/components/AudioPlayer.tsx`

- Container: `inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass`
- Play button: `w-6 h-6 rounded-full bg-para-teal`, `w-3 h-3` icon
- Progress bar: `w-24 h-3` track (`bg-white/10`), copper fill bar
- Seekable via click on progress track
- Minimal chrome — no timestamps, no volume control

---

### 6.6 Topic Pills

**Source:** `ui/src/pages/paragpt/Landing.tsx` (tags) + `Chat.tsx` (suggested topics)

#### Landing Page Tags
- Style: `border border-para-teal/50 text-para-teal text-xs px-3 py-1 rounded-full`
- Hollow (border only, no fill) — restrained, doesn't compete with content

#### Chat Suggested Topics
- Style: `text-xs px-3 py-1 rounded-full bg-[#d08050]/15 text-[#d08050]`
- Subtle copper fill — slightly more prominent as they're actionable
- Hover: `bg-[#d08050]/25`
- Appear after AI responses as follow-up suggestions

---

### 6.7 Reasoning Trace

**Source:** `ui/src/components/ReasoningTrace.tsx`

- Trigger: pill button, `text-[#d08050] hover:bg-[#d08050]/10`, `text-xs rounded-full`
- Expanded: `ml-4 border-l border-gray-700 pl-3 space-y-1.5`
- Each step: colored dot (green for final, gray for others) + `text-xs text-gray-400` label
- Details: `text-xs text-gray-600 ml-2`
- Collapsible — collapsed by default

---

### 6.8 Model Selector

**Source:** `ui/src/components/ModelSelector.tsx`

- Trigger: pill, `px-3 py-1.5 rounded-full text-xs`, copper text colour
- Hover: copper at 15% opacity background
- Dropdown: `.glass rounded-xl`, portaled to body, `z-index: 9999`
- Menu items: `px-3 py-2 text-sm`, selected item highlighted with copper
- Truncated model name: `max-w-[120px]` with ellipsis

---

### 6.9 Empty State (Landing Page)

**Source:** `ui/src/pages/paragpt/Landing.tsx`

- Layout: centered column, `pt-12 pb-32`
- Profile card: `.glass rounded-[16px] max-w-[640px] p-6`, centered text
- Avatar: `w-20 h-20 rounded-full`
- Name: `text-white text-2xl font-bold`
- Bio: `text-slate-400 text-sm leading-relaxed max-w-md`
- Topic tags below bio
- Starter questions: 3-column grid (SM+), `.glass rounded-2xl p-4`
- Sticky input bar at bottom: `fixed bottom-0`, `.glass rounded-[20px]`

---

### 6.10 Loading State (Thinking Bubble)

**Source:** `ui/src/pages/paragpt/Chat.tsx`

- Container: `.glass rounded-2xl px-5 py-4 min-w-[80px]`
- Three dots: `w-2 h-2 bg-para-teal rounded-full animate-bounce`
- Staggered delay: 0ms, 150ms, 300ms
- Node label below: `text-xs text-gray-500 mt-2` — shows which pipeline node is active
- **Never** use spinning loaders or skeleton screens

---

### 6.11 Error State

**Source:** `ui/src/components/ErrorBoundary.tsx` + `Chat.tsx`

#### Fatal Error (ErrorBoundary)
- Full-screen centered on `bg-para-navy`
- Title: `text-red-400 text-lg`
- Message: `text-gray-500 text-sm`
- Retry button: `bg-para-teal text-white rounded-lg text-sm hover:bg-para-teal-dark`

#### Transient Error (Chat Banner)
- Position: `absolute top-4`, centered with `left-1/2 -translate-x-1/2`
- Style: `bg-red-900/90 text-red-200 px-4 py-2 rounded-xl text-sm`
- Auto-dismisses or shows retry

---

### 6.12 Feedback Widget

**Source:** `ui/src/components/FeedbackWidget.tsx`

- Card: `bg-gray-900 border border-gray-700 rounded-2xl p-6 max-w-sm`
- Star rating: `text-2xl`, amber-400 active / gray-600 inactive
- Comment area: `bg-gray-800 border border-gray-700 rounded-xl p-3 text-sm`
- Submit: `bg-amber-500 text-gray-900 font-semibold rounded-xl`
- Skip: `bg-gray-800 text-gray-400 rounded-xl`
- Success: `text-amber-400 text-lg font-semibold`

---

## 7. Animation & Motion

### Allowed Animations

| Animation | Duration | Easing | Usage |
|---|---|---|---|
| Message fade-in | 250ms | ease-out | `opacity 0→1 + translateY(8px→0)` on new messages |
| Citation expand | 200ms | ease | `max-height` transition on citation reveal |
| Hover colour shift | 100-150ms | ease | `transition-colors duration-150` on all interactive elements |
| Thinking dots | 1.4s | infinite bounce | Staggered `animate-bounce` (150ms offset per dot) |
| Opacity reveal | 150ms | ease | Copy buttons, hover overlays (`transition-opacity`) |
| Chevron rotation | 150ms | ease | `transition-transform` on expand/collapse toggles |
| Typewriter | 12ms/tick | linear | Character-by-character AI response reveal |

### Forbidden Animations

- Bounce effects (except thinking dots)
- Scale transforms on hover
- Spinning loaders (use thinking dots instead)
- Auto-play media
- Decorative particle effects
- Parallax scrolling
- Page transitions / route animations

---

## 8. Shadows

### Shadow Scale

| Level | Value | Usage |
|---|---|---|
| **Natural** | `0 4px 16px rgba(0, 0, 0, 0.3)` | Glass cards, input bars (built into `.glass`) |
| **Warm glow** | `0 2px 12px rgba(208, 128, 80, 0.3)` | User message bubbles only |
| **Elevated** | `0 8px 32px rgba(0, 0, 0, 0.4)` | Modals, portaled dropdowns |
| **Inset** | `inset 0 1px 2px rgba(0, 0, 0, 0.2)` | Input fields (when needed) |

### Shadow Rules

- No coloured shadows except the user bubble warm glow
- Dark backgrounds (`#0d0d0d`) absorb shadows — keep them subtle
- Never use Tailwind's default `shadow-lg` etc. — always use custom values to match the glass system

---

## 9. Iconography

### Icon System

- **Library:** Heroicons (outline style)
- **Default size:** 20px (`w-5 h-5`) for inline, 24px (`w-6 h-6`) for primary actions
- **Small:** 12-14px (`w-3 h-3` to `w-3.5 h-3.5`) for pills and indicators
- **Stroke width:** 1.5-2 (Heroicons default)
- **Colour:** inherits from parent text colour — never hardcode icon colours

### Icon Usage

| Icon | Context |
|---|---|
| Arrow up (solid) | Send button — the ONE exception to outline-only rule |
| Chevron down | Expand/collapse (citations, reasoning trace) |
| Play / Pause | Audio player |
| Clipboard | Copy message |
| Plus / Refresh | New conversation |
| Microphone | Voice input toggle |
| Book open | Citation pill indicator |
| CPU chip | Model selector trigger |
| Sparkles | Reasoning trace trigger |

### Icon Anti-patterns

- No filled icons except send button
- No emoji as icons
- No custom SVG illustrations in the chat interface
- No animated icons

---

## 10. Anti-Patterns

These are explicitly banned from the ParaGPT interface:

| Anti-pattern | Why | Do instead |
|---|---|---|
| Gradients on surfaces | Breaks flat/glass aesthetic | Use solid or glass backgrounds |
| Coloured AI bubble backgrounds | Competes with content | Use `.glass` class |
| Emoji in UI chrome | Unprofessional for analytical brand | Use Heroicons |
| Skeleton screens (pulsing rectangles) | Generic, overused | Use thinking dots |
| Percentage confidence bars | False precision, misleading | Use verbal hedging in response text |
| Decorative animations | Distracting, violates restraint principle | Static or functional animation only |
| Custom fonts beyond Inter | Inconsistency, load time | Inter covers all needs |
| Inline hex colours | Maintenance nightmare | Use CSS tokens (`para-teal`, `para-navy`) |
| Hardcoded test data | Leaks into production | Always use API data |
| Auto-playing audio/video | Hostile UX | Require explicit play action |
| Toast notifications | Interrupts conversation flow | Use inline banners |
| Multiple font families | Visual noise | Inter only |

---

## 11. Accessibility

### Colour Contrast

| Combination | Ratio | WCAG Level |
|---|---|---|
| White `#ffffff` on `#0d0d0d` | 19.3:1 | AAA |
| Copper `#d08050` on `#0d0d0d` | ~4.2:1 | AA (large text only) |
| Slate-400 `#94a3b8` on `#0d0d0d` | ~6.2:1 | AA |
| Slate-500 `#64748b` on `#0d0d0d` | ~4.0:1 | AA (large text only) |

**Guidelines:**
- Use copper for headings, buttons, and large text — not for body copy on dark backgrounds
- Muted text (`#94a3b8`) is safe for secondary content at standard sizes
- Dimmed text (`#64748b`) should only be used for non-essential metadata

### Keyboard Navigation

- All interactive elements are keyboard-accessible
- Tab order follows visual reading order
- Focus outlines visible on all focusable elements
- Enter/Space activates buttons and links
- Escape closes modals and dropdowns

### Screen Readers

- `aria-label` on all icon-only buttons (send, play, copy, new conversation)
- Meaningful alt text on avatar images
- Citation expand/collapse announces state change
- Chat messages are in a scrollable region with appropriate `role`

### Motion Sensitivity

- All animations are under 250ms (well under vestibular trigger thresholds)
- No parallax, no auto-scrolling, no zoom effects
- `prefers-reduced-motion` should disable thinking dot bounce (not yet implemented — track as enhancement)

---

## 12. Reference Notes: alphageo.ai → ParaGPT

> **Research date:** 2026-03-08. alphageo.ai is a WordPress/Elementor marketing site for Parag Khanna's geospatial analytics company (formerly "Climate Alpha"). It is NOT a web application — design tokens below come from WordPress presets, not a custom design system.

### alphageo.ai Actual Design Tokens

| Property | Value | Notes |
|---|---|---|
| **Background** | `#000000` (pure black) | WordPress default, not dark gray |
| **Text** | `#ffffff` | White on black throughout |
| **Primary accent** | `#0693e3` (vivid cyan-blue) | WordPress preset, used in gradients |
| **Secondary accent** | `#9b51e0` (vivid purple) | Gradient endpoint |
| **Brand gradient** | `linear-gradient(135deg, #0693e3 0%, #9b51e0 100%)` | Cyan-to-purple at 135° — the dominant brand expression |
| **Typography** | System font stack (no Google Fonts) | Browser default sans-serif |
| **Content width** | 800px (reading) / 1200px (wide) | WordPress `--wp--style--global--content-size` |
| **Glassmorphism** | None | No `backdrop-filter` anywhere on the site |
| **Shadows** | `6px 6px 9px rgba(0,0,0,0.2)` (offset style) | WordPress preset "natural" shadow |
| **Motion** | Particle effects (Elementor) | 160 white particles, repulse-on-hover — decorative background |
| **Spacing** | Modular 1.5× scale (7→11→16→24→36→54→81px) | WordPress preset spacing tokens |

### Comparison Table

| Aspect | alphageo.ai | ParaGPT | Reasoning |
|---|---|---|---|
| **Palette** | Black / White / Cyan-to-purple gradient | Near-black `#0d0d0d` / White / Copper | Gradient → single accent; warmth > cold tech |
| **Content width** | 800px | 640-768px | Tighter for intimate 1:1 chat |
| **Typography** | System fonts | Inter | We invest in a specific typeface for better small-size legibility |
| **Glassmorphism** | None | Core visual system | alphageo doesn't need depth layers; chat UI does |
| **Shadows** | Offset (6px 6px) | Diffuse (0 4px 16px) | Offset shadows feel 2020-era; diffuse shadows suit glass aesthetic |
| **Background** | Pure black `#000` | Near-black `#0d0d0d` | Pure black is too harsh for sustained reading (2026 consensus) |
| **Decorative motion** | Particle effects | None | Particles work for marketing; banned in conversation UI |
| **Layout** | Marketing page (sections, CTAs) | App shell (single conversation) | Entirely different interaction models |
| **Brand expression** | Data visualization + gradients | Persona voice + citations | Both express intelligence through content, not chrome |

### What We Borrowed

- **Minimalist confidence** — no "look at me" design, just substance
- **Dark background as canvas** — content floats, nothing competes
- **Analytical positioning** — the interface says "this is serious work"
- **Progressive disclosure** — information appears when needed, not all at once
- **Restraint principle** — alphageo avoids decorative flourishes in its core content; we apply this even more strictly

### What We Deliberately Changed

- **Cyan-purple gradient → Single copper accent** — alphageo uses a gradient because it's a tech platform selling analytics. ParaGPT needs warmth — copper signals a human voice, not a data product. Single accent is also simpler to maintain.
- **Pure black → Near-black (#0d0d0d)** — Pure `#000` creates excessive contrast for sustained chat reading. Near-black reduces eye strain while preserving the dark aesthetic.
- **No glass → Full glass system** — alphageo is a static marketing page; ParaGPT is an interactive chat app needing depth hierarchy (input bar, message bubbles, dropdowns). Glass provides that layering.
- **System fonts → Inter** — Chat messages need to be highly legible at 14px across thousands of words. Inter earns its load cost here.
- **Offset shadows → Diffuse shadows** — alphageo's 6px offset shadows look dated on a glass-based UI. Diffuse shadows (our `.glass` system) match modern depth conventions.
- **Particle effects → Zero decorative motion** — Background particles are acceptable on a marketing hero; they would be distracting in a conversation interface.

---

## 13. 2026 AI Chat Interface Trends — Alignment Audit

> **Research date:** 2026-03-08. Sources: Muzli, UX Planet, Medium (design bootcamp), Accessibility.com, ShapeofAI, IntuitionLabs, product analysis of ChatGPT / Claude / Gemini / Perplexity.

This section maps current industry trends against our design system. For each trend, we note whether ParaGPT already follows it, should adopt it, or intentionally diverges.

### 13.1 Dark Mode Conventions

| Trend | Industry Standard | ParaGPT Status | Action |
|---|---|---|---|
| Background: dark gray, not pure black | `#1a1a1a` to `#212121` | `#0d0d0d` (near-black) | **Already aligned.** Our value sits between pure black and dark gray — darker than ChatGPT but not `#000` |
| Text: off-white, not pure white | `#e0e0e0` to `#f0f0f0` | `#ffffff` with slate hierarchy | **Consider.** Body text at `#f0f0f0` would reduce glare. Currently fine — our slate-300/400 hierarchy already softens most secondary text |
| System preference detection | `prefers-color-scheme` | Not implemented (dark-only) | **Intentional divergence.** ParaGPT is a dark-mode-only product by design. Light mode would require a full second palette. Low priority |

### 13.2 Glassmorphism State of the Art

| Trend | Industry Standard | ParaGPT Status | Action |
|---|---|---|---|
| Frosted glass with `backdrop-filter: blur()` | 8-20px blur, 1px semi-transparent borders | `.glass` uses 16px blur + `rgba(255,255,255,0.08)` border | **Already aligned.** Our implementation matches 2026 best practice |
| Multi-layered depth (2-3 glass planes) | Different opacities per layer | Single `.glass` class, one opacity level | **Enhancement opportunity.** Could add `glass-elevated` (0.85 opacity, 20px blur) for modals/dropdowns. Low priority — current system works |
| Ambient gradient backgrounds behind glass | Deep purple/blue orbs behind UI layers | None — flat `#0d0d0d` background | **Intentional divergence.** Ambient gradients conflict with our restraint principle. Our glass reads well on flat dark backgrounds |
| Adaptive glass (dynamic blur based on context) | Emerging in 2026 | Not implemented | **Skip.** Over-engineering for a chat interface. Our static glass is sufficient |

### 13.3 Chat UI Conventions

| Trend | Industry Standard | ParaGPT Status | Action |
|---|---|---|---|
| AI responses: no bubble, flowing text | ChatGPT + Claude use minimal/no bubble for AI | AI uses `.glass` card | **Intentional divergence.** Glass bubbles provide visual grouping for citations + reasoning trace that "no bubble" can't. Our glass is subtle enough not to compete |
| Message width: 680-768px | Universal constraint | `max-w-3xl` (768px) | **Already aligned** |
| Expanding textarea input | Multi-line, grows vertically | Max-height 120px, auto-grows | **Already aligned** |
| Model selector near input | ChatGPT places mode toggle in input area | Model selector as header pill | **Already aligned.** Our placement in the header keeps the input bar clean. Either pattern is acceptable |
| Inline numbered citations | Perplexity: `[1][2][3]` with collapsible source panel | Grouped citation cards below response | **Enhancement opportunity.** Inline citation markers (clickable `[N]`) that scroll to source cards would improve scannability. Medium priority |
| Streaming with visible reasoning stages | "Searching... Thinking... Composing..." | Node labels below thinking dots | **Already aligned.** Our pipeline node labels serve the same purpose |

### 13.4 Typography

| Trend | Industry Standard | ParaGPT Status | Action |
|---|---|---|---|
| Sans-serif: Inter, Geist, system fonts | Inter is industry standard | Inter | **Already aligned** |
| Variable fonts for weight transitions | Emerging | Static Inter weights | **Skip.** Variable Inter exists but adds load cost for minimal benefit in our use case |
| 14-16px base for chat messages | Universal | 14px (`text-sm`) | **Already aligned** |
| Line height 1.5-1.7 for AI responses | Readability standard | `leading-relaxed` (1.625) | **Already aligned** |
| Monospace for code blocks | Fira Code / JetBrains Mono | Browser default monospace | **Enhancement opportunity.** Adding `font-family: 'JetBrains Mono', monospace` for code blocks would polish the markdown rendering. Low priority |

### 13.5 Colour Trends

| Trend | Industry Standard | ParaGPT Status | Action |
|---|---|---|---|
| Warm accents as premium differentiator | Claude copper, Grok orange — minority but distinctive | Copper `#d08050` | **Already aligned.** Most AI products use cool accents (green, blue, teal). Our warm copper stands out — same strategic choice Claude made |
| One strong accent + neutral foundation | Universal best practice | Single copper accent + gray/slate hierarchy | **Already aligned** |
| Cinematic gradients (subtle background) | Used for emotional depth | None — flat backgrounds | **Intentional divergence.** Flat aligns with our restraint principle |
| Pantone 2026: Cloud Dancer (soft white) | Trend toward warm whites in light mode | N/A (dark-only) | **Not applicable** |

### 13.6 Accessibility (2026 Requirements)

| Trend | Industry Standard | ParaGPT Status | Action |
|---|---|---|---|
| WCAG 2.1 AA compliance | Mandatory (April 2026 government deadline driving broad adoption) | Partial — contrast ratios documented, keyboard nav implemented | **Continue.** Our contrast audit (Section 11) is solid. Need to verify ARIA live regions for streaming responses |
| `prefers-reduced-motion` | Must disable non-essential animation | Not yet implemented | **Must implement.** Add `@media (prefers-reduced-motion: reduce)` to disable thinking dot bounce and message fade-in. High priority |
| Focus indicators on all interactive elements | Visible outline, logical tab order | Implemented but not audited | **Audit needed.** Verify all focusable elements have visible indicators |
| ARIA live regions for streaming text | Screen readers announce new content | Not explicitly implemented | **Enhancement opportunity.** Add `aria-live="polite"` to the message container for streaming responses. Medium priority |
| Voice input as first-class input | Microphone always visible | Microphone icon present | **Already aligned** |

### 13.7 What's Dated in 2026 (Anti-Pattern Check)

These patterns are considered outdated. We check ParaGPT against each:

| Dated Pattern | ParaGPT Status |
|---|---|
| Chat bubbles on BOTH sides with heavy colouring | User bubble has copper gradient; AI uses glass. **Acceptable** — user bubble is distinctive but not heavy |
| Pure black `#000` backgrounds | We use `#0d0d0d`. **Compliant** |
| Pure white `#fff` text everywhere | Primary text is white but hierarchy uses slate-300/400/500. **Acceptable** |
| Heavy drop shadows on message bubbles | User bubble has warm glow; AI bubble uses glass shadow. **Compliant** — both are subtle |
| Bouncy/playful animations | Thinking dots use `animate-bounce`. **Minor concern** — could switch to `animate-pulse` for more refined feel. Low priority |
| Full-width text without max-width | `max-w-3xl` enforced. **Compliant** |
| Neumorphism | Not used. **Compliant** |
| No streaming indicator | Thinking dots + node labels. **Compliant** |
| Hidden citations / no source attribution | Citations visible with expand/collapse. **Compliant** |
| Ignoring `prefers-reduced-motion` | **Not yet implemented — high priority fix** |

### 13.8 Emerging Patterns Worth Watching

These are trends gaining traction but not yet mandatory. Track for future iterations:

1. **Hybrid interfaces (chat + artifact pane)** — ChatGPT Canvas, Claude Artifacts. Side panel for rich outputs. Not relevant for ParaGPT today (pure conversation), but worth considering if document/analysis features are added.
2. **Real-time thought streaming** — Perplexity shows search/reasoning process inline. Our reasoning trace is collapsible (hidden by default). Could surface key stages inline for transparency.
3. **Adaptive colour systems** — Palettes that adjust contrast/saturation based on ambient light or accessibility settings. Over-engineered for our scope but technically interesting.
4. **Collapsible sidebar for conversation history** — Standard in ChatGPT/Claude/Gemini. ParaGPT currently has no conversation persistence UI. Would be needed if multi-session support is added.

### 13.9 Priority Actions from Trend Audit

| Priority | Action | Section |
|---|---|---|
| **High** | Implement `prefers-reduced-motion` media query | 13.6, 13.7 |
| **Medium** | Add ARIA live region for streaming responses | 13.6 |
| **Medium** | Explore inline citation markers `[N]` (Perplexity pattern) | 13.3 |
| **Low** | Add monospace font for code blocks | 13.4 |
| **Low** | Add `glass-elevated` variant for modals | 13.2 |
| **Low** | Switch thinking dots from bounce to pulse | 13.7 |

---

## Appendix: File Reference

| File | What it defines |
|---|---|
| `ui/src/index.css` | CSS tokens (`@theme`), `.glass` utility, scrollbar, markdown styles |
| `ui/src/themes/paragpt.ts` | JS theme object (bg, accent, text, radius, font) |
| `ui/src/components/MessageBubble.tsx` | User + AI message rendering |
| `ui/src/components/ChatInput.tsx` | Text input with send button |
| `ui/src/components/CitationCard.tsx` | Individual citation display |
| `ui/src/components/CitationGroupCard.tsx` | Grouped citations by source |
| `ui/src/components/AudioPlayer.tsx` | Voice playback controls |
| `ui/src/components/ReasoningTrace.tsx` | Pipeline step visualization |
| `ui/src/components/ModelSelector.tsx` | Model picker dropdown |
| `ui/src/components/ErrorBoundary.tsx` | Fatal error fallback |
| `ui/src/components/FeedbackWidget.tsx` | Post-conversation survey |
| `ui/src/pages/paragpt/Landing.tsx` | Landing page / empty state |
| `ui/src/pages/paragpt/Chat.tsx` | Chat page layout + thinking bubble |
