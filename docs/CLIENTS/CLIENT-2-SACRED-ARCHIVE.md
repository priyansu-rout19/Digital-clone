# Client 2: Sacred Archive — Mirror-Only Spiritual Teaching System

**Prepared by:** Prem AI | **Date:** February 25, 2026 | **Version:** 1.0

---

## 1. Project Summary

Prem AI will build a **mirror-only AI system** that serves the authentic teachings of a spiritual teacher. The system retrieves verified satsangs, published texts, and transcribed Q&A sessions — **quoting them directly** with full provenance (source, date, location, verifying reviewer). It **never interprets, never synthesizes, and never speculates**. When no verified teaching exists for a question, it stays silent with reverence. Every response passes through **mandatory human review** before reaching a seeker.

**What is delivered:** A private, **air-gapped** deployment of the Sacred Archive Engine on Prem's sovereign infrastructure. Seekers access it through an internal web interface. Responses are text-only, citing original recordings where available. All output is human-reviewed before serving.

**What is NOT in scope:** AI-generated voice or avatar, public internet access, self-service content management, mobile application, or automated approval of responses. Corpus curation is performed by BM Academy prior to and during the project.

---

## 2. Scope & Deliverables

### Included in v1

| Deliverable | Description |
|---|---|
| **Sacred Archive Engine** | AI system that receives questions, searches verified teachings through both semantic similarity and provenance relationships, assembles direct quotes with full source attribution, and verifies accuracy before queuing for review. |
| **Silence Mode** | When no verified teaching covers the seeker's question, the system responds with a reverent acknowledgment and suggests related teachings that have been covered. It does not guess. |
| **Provenance on Every Response** | Every quoted passage includes: source type (satsang, book, Q&A), date, location, event, and verifying reviewer. |
| **Mandatory Human Review** | Every AI-generated response enters a review queue. A trained reviewer approves, rejects, or edits the response before it is served to any seeker. No response bypasses this step. |
| **Access Tier System** | Three tiers of access — **devotee, friend, follower** — each seeing different subsets of the teaching corpus. |
| **Review Dashboard** | Web interface for reviewers to process queued responses. Shows question, proposed response, cited sources, and confidence score. Supports approve, reject, and edit actions with full audit logging. |
| **Seeker Chat Interface** | Clean web interface for seekers to ask questions and receive approved responses. Supports multi-turn conversation within a session. |
| **Corpus Ingestion** | All provided materials (satsang recordings, books, transcripts) processed with provenance metadata, indexed, and linked in a knowledge graph. |
| **Audit Trail** | Every query, response, review decision, and system action is logged with timestamps and identities. |

### Excluded from v1

| Item | Rationale |
|---|---|
| AI-synthesized voice | The Sacred Archive serves original recordings only. AI voice cloning is philosophically incompatible with the mirror-only principle. |
| AI-generated avatar | Same rationale as voice. Visual representation uses archival photos only. |
| Self-service admin panel | Corpus management handled by Prem engineering with BM Academy in v1. Admin tooling planned for v2. |
| Public internet access | v1 is air-gapped or controlled-access only. |
| Automated response approval | All responses require human review in v1. AI-assisted pre-screening may be introduced in v2. |

---

## 3. User Experience

### What Seekers Experience

A seeker opens the Sacred Archive on their approved device. They select their access tier and ask a question — for example, "What has Guruji taught about forgiveness?" Within a few seconds, they receive a response composed of **direct quotes from verified satsangs**, each with full provenance: the date, location, event, and verifying reviewer.

If the seeker asks about a topic that has never been explicitly addressed in the verified corpus, they see:

> *"With reverence and humility, I must remain silent on this matter. The specific teaching you seek has not been explicitly shared in the verified satsangs. I invite you to explore related teachings on [grace/devotion/surrender] which have been covered extensively."*

Seekers can ask follow-up questions, and the system maintains context within the session.

### What Reviewers Experience

A reviewer logs into the Review Dashboard and sees a queue of pending responses. For each item, they see:
- The seeker's question
- The AI's proposed response
- The actual source passages it cited
- A confidence score

The reviewer **approves** (response is cached and served), **rejects** (response is discarded), or **edits** the response before approving. Keyboard shortcuts enable processing **50+ responses per day**.

---

## 4. Success Criteria

| Metric | Target |
|---|---|
| Provenance traceability | 100% of responses include source, date, location, and verifier |
| Citation accuracy | >98% — every cited passage is real, relevant, and verified |
| Silence Mode precision | >95% — correctly stays silent on untaught topics |
| Silence Mode recall | >90% — correctly surfaces teachings that are in the corpus |
| Response consistency | >98% — no contradictions across responses |
| Review throughput | 50+ responses per reviewer per day |
| Air-gap integrity | Zero external network calls (validated monthly) |
| Seeker satisfaction | >90% in core devotee survey |

---

## 5. Clone Profile Configuration

```yaml
clone_profile:
  slug: "sacred-archive"
  display_name: "Sacred Teachings"
  bio: "Mirror of timeless wisdom, curated with reverence..."
  avatar_url: "/static/avatars/sacred-archive.jpg"

  generation_mode: "mirror_only"        # Direct quotes only, no synthesis
  confidence_threshold: 0.95            # Conservative — prefer silence over error
  silence_behavior: "strict_silence"    # Reverent silence on untaught topics
  silence_message: "With reverence and humility, I must remain silent..."

  review_required: true                 # 100% human review before serving
  user_memory_enabled: false            # No seeker tracking (privacy)

  voice_mode: "original_only"           # Original recordings only, no AI voice
  voice_model_ref: null

  retrieval_tiers: ["vector", "tree_search"]  # Both tiers for precision
  provenance_graph_enabled: true        # Cypher graph queries
  access_tiers: ["devotee", "friend", "follower"]
  deployment_mode: "air_gapped"         # Zero internet connectivity
```

---

## 6. Security & Data Handling

- **Air-gapped deployment:** Zero internet connectivity. All AI models, databases, and code run locally.
- **Disk encryption:** LUKS full-disk encryption on all storage volumes.
- **Role-based access:** Curator (ingests), Reviewer (approves), Seeker (asks). Each sees only what they need.
- **Audit logging:** Every query, response, review decision, and action logged with identity and timestamp.
- **No third-party services:** Every component runs on Prem's sovereign infrastructure.
- **Seeker privacy:** No cross-session tracking. No user memory stored.

---

## 7. Key Differences from Client 1 (ParaGPT)

| Aspect | ParaGPT | Sacred Archive |
|---|---|---|
| Generation mode | Interpretive | Mirror-only |
| Confidence threshold | 0.80 (factory; DB: 0.60) | 0.95 |
| Uncertainty handling | Soft hedge | Strict silence |
| Human review | None | 100% mandatory |
| User memory | Yes | No |
| Voice | AI-cloned | Original recordings |
| Retrieval | Vector only | Vector + tree search |
| Provenance graph | No | Yes |
| Access control | Public | Tiered |
| Deployment | Standard | Air-gapped |

---

*Summary of Sacred Archive engagement. Final scope and terms subject to mutual agreement.*
