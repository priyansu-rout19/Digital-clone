# Client 1: ParaGPT — Digital Clone for Personal Brand

**Prepared by:** Prem AI | **Date:** February 25, 2026 | **Version:** 1.0

---

## 1. Project Summary

Prem AI will build a **digital clone** that extends a thought leader's reach through AI-powered conversations. The clone answers questions by drawing on the person's published **books, essays, interviews, and talks** — always citing its sources. Responses are delivered in **text and in the person's cloned voice**, accessible via a dedicated web page.

**What is delivered:** A private deployment of the Digital Clone Engine, configured for the client's persona, hosted on Prem's sovereign infrastructure (PCCI). End users visit a web page, ask questions, and receive cited, in-voice responses that sound and reason like the thought leader.

**What is NOT in scope:** Self-service onboarding portal, video avatar, mobile app, public multi-tenant platform, or ongoing content curation services. Data gathering and corpus preparation are assumed complete prior to project start.

---

## 2. Scope & Deliverables

### Included in v1

| Deliverable | Description |
|---|---|
| **Clone Engine** | AI system that receives questions, retrieves relevant passages from the corpus, generates an in-persona response with citations, and verifies accuracy before responding. |
| **Voice Output** | Responses delivered in the thought leader's cloned voice, synthesized from provided audio samples (2-5 minutes of clean speech). |
| **Public Chat Page** | A clean, branded web page where anyone can have a conversation with the clone. Supports multi-turn dialogue within a session. |
| **Cross-Session Memory** | The clone remembers returning users and references prior conversations naturally. Users can request their data be forgotten. |
| **Citation on Every Response** | Every answer includes the source (book, essay, interview, date) so users can verify and explore further. |
| **Confidence-Aware Responses** | When the clone is uncertain, it says so — hedging honestly rather than fabricating an answer. |
| **Corpus Ingestion** | All provided materials (books, essays, transcripts, audio, video) processed, indexed, and made searchable by the clone. |
| **Persona Configuration** | System tuned to match the thought leader's vocabulary, frameworks, communication style, and topical boundaries. |
| **Monitoring Dashboard** | Internal view of query volume, response confidence distribution, and system health. |

### Excluded from v1

| Item | Rationale |
|---|---|
| Video avatar (talking head) | Deferred to v2 to focus v1 on response quality and voice fidelity. |
| Self-service admin panel | Corpus and configuration managed by Prem engineering in v1. Admin tooling planned for v2. |
| Multilingual voice cloning | English voice clone in v1. Multilingual voice in v2. Text responses support 100+ languages from day one. |
| Embeddable widget | Deferred to v2. The public chat page is the sole interface in v1. |
| Custom domain | The chat page runs on a Prem-provided URL in v1. |

---

## 3. User Experience

A visitor arrives at the chat page and sees the thought leader's **name, photo, and a brief description**. They type a question — or choose from suggested topics — and within **three seconds** receive a written response that sounds like the thought leader: using their frameworks, referencing their work, and citing specific sources. If they enable voice, the response plays back in the thought leader's actual voice. The conversation continues naturally; follow-up questions build on prior context.

If the clone doesn't know the answer — because the topic isn't covered in the corpus — it says so directly, and suggests related topics the thought leader has addressed.

---

## 4. Success Criteria

| Metric | Target |
|---|---|
| Citation accuracy | >90% of responses cite real, relevant sources |
| Persona fidelity | >85% (blind evaluation: "Does this sound like [person]?") |
| Response latency | <3 seconds for text, <6 seconds for voice |
| Honest uncertainty | Clone correctly hedges on >90% of out-of-corpus questions |
| Consistency | No contradictions across responses in evaluation suite |
| Stakeholder satisfaction | Thought leader or designated reviewer approves response quality |

---

## 5. Clone Profile Configuration

```yaml
clone_profile:
  slug: "paragpt-client"
  display_name: "Parag Khanna"
  bio: "Author, geopolitical strategist..."
  avatar_url: "/static/avatars/parag-khanna.jpg"

  generation_mode: "interpretive"      # Synthesizes and cites sources
  confidence_threshold: 0.80           # SOW spec; runtime DB override: 0.60 (Session 35)
  silence_behavior: "soft_hedge"       # Hedges honestly, doesn't go silent
  silence_message: "I don't have a specific teaching on that topic..."

  review_required: false               # Responses stream directly to user
  user_memory_enabled: true            # Mem0 cross-session tracking

  voice_mode: "ai_clone"              # AI-cloned voice output
  voice_model_ref: "voice_pk_v1"

  retrieval_tiers: ["vector"]          # Vector search only (fast)
  provenance_graph_enabled: false
  access_tiers: ["public"]
  deployment_mode: "standard"          # Standard PCCI (not air-gapped)
```

---

## 6. Key Differences from Client 2 (Sacred Archive)

| Aspect | ParaGPT | Sacred Archive |
|---|---|---|
| Generation mode | Interpretive (synthesizes, cites) | Mirror-only (direct quotes only) |
| Confidence threshold | 0.80 (factory; DB: 0.60) | 0.95 (much stricter) |
| Uncertainty handling | Soft hedge | Strict silence |
| Human review | None | 100% mandatory |
| User memory | Yes (Mem0) | No (privacy) |
| Voice | AI-cloned | Original recordings only |
| Retrieval | Vector only | Vector + tree search |
| Provenance graph | No | Yes |
| Access control | Public | Tiered |
| Deployment | Standard | Air-gapped |

---

*Summary of ParaGPT engagement. Final scope and terms subject to mutual agreement.*
