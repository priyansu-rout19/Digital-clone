"""
Sacred Archive Corpus Seeder — Digital Clone Engine

Seeds sample documents and chunks for the Sacred Archive clone
so that retrieval returns real passages for spiritual teaching queries.

Inserts:
  - 10 documents with provenance JSONB (title, date, location)
  - ~40 document_chunks with real Gemini embeddings (1024-dim, truncated from 3072)

All chunks use access_tier='devotee' (Sacred Archive's primary tier).

Idempotent: checks for existing rows before inserting.
Requires: GOOGLE_API_KEY and EMBEDDING_MODEL in .env

Run: python scripts/seed_sacred_archive_corpus.py
"""

import os
import sys
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Add project root to sys.path so core/ imports work
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import psycopg
from pgvector.psycopg import register_vector

from core.db.schema import Clone, Document
from core.db import psycopg_url
from core.rag.ingestion.embedder import get_embedder

# ---------------------------------------------------------------------------
# Database setup (same pattern as seed_paragpt_corpus.py)
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres@localhost/dce_dev")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# ---------------------------------------------------------------------------
# Sample corpus definition
# ---------------------------------------------------------------------------
# Each entry: (filename, source_type, mime_type, provenance_dict, list_of_passages)
#
# Passages are written in a timeless spiritual teaching style — direct, meditative,
# focused on themes like devotion, silence, meditation, compassion, surrender,
# and the nature of the self. These are SAMPLE passages for demo, NOT real quotes.
# ---------------------------------------------------------------------------

CORPUS = [
    {
        "filename": "on_silence_and_stillness.pdf",
        "source_type": "discourse",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "On Silence and Stillness",
            "date": "2023-03-12",
            "location": "Mountain Retreat Center",
        },
        "passages": [
            (
                "Silence is not the absence of sound. It is the presence of awareness "
                "before thought arises. When you sit in true silence, you do not push "
                "away the noise of the world — you simply cease to follow it. The mind "
                "becomes like still water, and in that stillness, everything is reflected "
                "without distortion."
            ),
            (
                "Most seekers confuse quietness with silence. You can be quiet and still "
                "be full of inner noise — planning, remembering, judging. True silence "
                "is when even the judge is silent. It is not something you achieve; it is "
                "what remains when you stop trying to achieve."
            ),
            (
                "Stillness is the doorway to the sacred. Not physical stillness alone, "
                "but the stillness of the one who observes. When the observer is still, "
                "there is no separation between you and what you observe. This is the "
                "beginning of real meditation — not a practice, but a dissolution."
            ),
            (
                "Do not seek silence as an escape from suffering. Silence is not a refuge "
                "— it is a revelation. In silence, everything you have avoided will surface. "
                "But if you remain still and do not react, those things lose their power "
                "over you. This is the alchemy of awareness."
            ),
        ],
    },
    {
        "filename": "the_path_of_devotion.pdf",
        "source_type": "discourse",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "The Path of Devotion",
            "date": "2023-07-15",
            "location": "Mountain Retreat Center",
        },
        "passages": [
            (
                "Devotion is not worship of something outside yourself. It is the "
                "recognition that the sacred lives within you and within all things. "
                "When you bow to the divine, you are bowing to the deepest truth of "
                "your own nature. This is why devotion brings tears — not of sadness, "
                "but of homecoming."
            ),
            (
                "The devoted heart does not ask for proof. It does not demand miracles "
                "or signs. It simply opens, the way a flower opens to the sun — not "
                "because the sun has commanded it, but because opening is its nature. "
                "Devotion is the natural state of a heart that has stopped defending itself."
            ),
            (
                "Surrender is the highest form of intelligence. The mind thinks surrender "
                "means defeat, but the heart knows it means freedom. When you surrender "
                "the need to control every outcome, you discover that life has an "
                "intelligence far greater than your plans."
            ),
            (
                "There are three stages of devotion. First, you love the divine because "
                "you want something. Then, you love the divine because you have received "
                "something. Finally, you love without reason — and this reasonless love "
                "is the only love that is real. Everything else is transaction."
            ),
        ],
    },
    {
        "filename": "teachings_on_compassion.pdf",
        "source_type": "discourse",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "Teachings on Compassion",
            "date": "2024-01-20",
            "location": "Riverside Ashram",
        },
        "passages": [
            (
                "Compassion is not pity. Pity looks down; compassion looks across. When "
                "you feel true compassion, there is no sense of being higher or more "
                "fortunate than the one who suffers. There is only the recognition: this "
                "suffering is also mine. This body of pain is also my body."
            ),
            (
                "You cannot practice compassion as a technique. If you are trying to be "
                "compassionate, you have already failed. Compassion arises naturally when "
                "the walls of the separate self become thin. When you stop defending your "
                "boundaries so fiercely, the suffering of others flows into you — and "
                "through you — without obstruction."
            ),
            (
                "The deepest compassion is not directed at the suffering of others but "
                "at the ignorance that causes suffering. When you see someone act from "
                "greed or hatred, the compassionate heart sees the confusion underneath. "
                "It does not excuse the action, but it understands the blindness."
            ),
        ],
    },
    {
        "filename": "on_meditation_and_awareness.pdf",
        "source_type": "discourse",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "On Meditation and Awareness",
            "date": "2023-11-08",
            "location": "Mountain Retreat Center",
        },
        "passages": [
            (
                "Meditation is not something you do. It is something you are. The moment "
                "you sit down to meditate with a goal — to calm the mind, to find peace, "
                "to become enlightened — you have turned meditation into another project "
                "of the ego. Real meditation begins when you give up all projects, "
                "including the project of meditating."
            ),
            (
                "Awareness is the one thing that cannot be practiced, because it is always "
                "already present. You do not need to create awareness — you need to notice "
                "that it is already here, underneath every thought, behind every sensation. "
                "The practice is not of building awareness but of removing what obscures it."
            ),
            (
                "The breath is the bridge between the body and the formless. When you "
                "follow the breath without trying to control it, the mind gradually "
                "settles — not because you have forced it, but because attention has "
                "found its natural home. The breath breathes itself; you need only witness."
            ),
            (
                "Do not fight your thoughts in meditation. Thoughts are not the enemy — "
                "identification with thoughts is. A thought arises, and you believe you "
                "are the thinker. But if you simply watch, you will see that thoughts "
                "come and go like clouds. You are the sky, not the weather."
            ),
        ],
    },
    {
        "filename": "questions_on_the_self.pdf",
        "source_type": "satsang",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "Questions on the Nature of the Self",
            "date": "2024-03-22",
            "location": "Riverside Ashram",
            "event": "Spring Satsang 2024",
        },
        "passages": [
            (
                "You ask, 'Who am I?' — but the question itself is the answer. The one "
                "who is searching is the one being searched for. When this is truly seen, "
                "the search ends — not because you have found something, but because you "
                "realize there was never anything lost."
            ),
            (
                "The ego is not something to be destroyed. It is something to be seen "
                "through. When you look closely at the one who says 'I,' you find no "
                "solid center — only a collection of memories, habits, and preferences. "
                "The self is not a thing but a process, and when the process is witnessed "
                "without attachment, freedom is already here."
            ),
            (
                "Liberation is not a distant goal. It is the recognition of what you "
                "already are, before the mind adds its commentary. Right now, in this "
                "moment, before you form your next thought — that is it. That bare "
                "awareness, that open space, that is your original face."
            ),
        ],
    },
    {
        "filename": "living_wisdom_retreat_2024.pdf",
        "source_type": "retreat_transcript",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "Living Wisdom Retreat — Closing Address",
            "date": "2024-07-16",
            "location": "Mountain Retreat Center",
            "event": "Living Wisdom Summer Retreat 2024",
        },
        "passages": [
            (
                "The spiritual path is not about becoming someone new. It is about "
                "unbecoming everything you are not. Layer by layer, you release the "
                "identities you have accumulated — the roles, the stories, the beliefs "
                "about who you should be — until only the essential remains."
            ),
            (
                "Grace is not a reward for good behavior. It is the natural movement "
                "of existence toward those who have made space for it. You cannot earn "
                "grace, but you can remove the obstacles — the arrogance, the busyness, "
                "the certainty that you already know. Grace flows into emptiness."
            ),
            (
                "A teacher does not give you something you lack. A true teacher is a "
                "mirror — showing you what you already carry but have forgotten. The "
                "teaching is not in the words but in the presence. When the student is "
                "truly ready, even silence teaches."
            ),
        ],
    },
    # -----------------------------------------------------------------------
    # New documents added in Session 39 (corpus expansion)
    # -----------------------------------------------------------------------
    {
        "filename": "meditation_practice_instructions.pdf",
        "source_type": "discourse",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "Instructions for Daily Practice",
            "date": "2024-05-10",
            "location": "Mountain Retreat Center",
            "event": "Spring Meditation Intensive",
            "verifier": "Senior Teacher Council",
            "access_tier": "devotee",
        },
        "passages": [
            (
                "Begin each sitting by doing nothing. Simply sit. Do not arrange your posture "
                "with military precision — find the balance between alertness and ease. The "
                "spine rises naturally, the hands rest where they fall, and the eyes close "
                "softly or remain half-open. The body knows how to sit; trust it."
            ),
            (
                "When thoughts arise, do not engage and do not resist. Imagine thoughts as "
                "visitors arriving at your door. You do not need to invite them in for tea, "
                "nor do you need to slam the door. Simply acknowledge their arrival and "
                "return your attention to the breath. This is the entire practice."
            ),
            (
                "The morning hours — between four and six — are the most conducive to deep "
                "meditation. The world is quiet, the mind has not yet accumulated the impressions "
                "of the day, and the boundary between waking and sleeping is thin. If you can "
                "establish a morning practice, it will transform everything that follows."
            ),
            (
                "Walking meditation is not a lesser practice than sitting. When you walk with "
                "full awareness — feeling each foot touch the earth, noticing the shift of "
                "weight, the swing of the arms — the body becomes the meditation. The ground "
                "teaches you grounding. The step teaches you presence."
            ),
            (
                "Do not measure your meditation by the experiences that arise within it. Visions, "
                "bliss, and unusual sensations are not signs of progress — they are weather. "
                "The real measure of meditation is what happens when you open your eyes: "
                "are you more patient, more present, more kind? That is the only test."
            ),
        ],
    },
    {
        "filename": "teacher_student_relationship.pdf",
        "source_type": "satsang",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "On the Teacher-Student Relationship",
            "date": "2024-08-03",
            "location": "Riverside Ashram",
            "event": "Monsoon Satsang Series",
            "verifier": "Senior Teacher Council",
            "access_tier": "devotee",
        },
        "passages": [
            (
                "The relationship between teacher and student is the oldest transmission "
                "in human culture. It predates books, institutions, and religions. One being "
                "who has seen something essential sits with another who is ready to see. "
                "Nothing needs to be taught — only transmitted. And the transmission happens "
                "through presence, not through words."
            ),
            (
                "A true teacher never creates dependency. The purpose of the teacher is to "
                "make themselves unnecessary. Every teaching is an invitation to stand on your "
                "own feet. If a teacher binds you closer and closer, that is not a teacher — "
                "that is a cage with a pleasant voice."
            ),
            (
                "The student's role is not passive obedience but active inquiry. Question "
                "everything — not from suspicion, but from a burning desire to understand. "
                "The teacher who welcomes your questions is trustworthy. The teacher who "
                "punishes your doubt has something to hide."
            ),
            (
                "Transmission happens in the spaces between words. When teacher and student "
                "sit together in silence, something passes that no lecture can convey. "
                "This is why the ancient traditions placed such emphasis on physical presence "
                "— not because the teacher is special, but because proximity allows resonance."
            ),
            (
                "The greatest danger in the spiritual path is confusing the finger pointing "
                "at the moon with the moon itself. The teacher's words, the scriptures, the "
                "practices — all are fingers pointing. When you mistake the teaching for the "
                "truth, you have turned wisdom into dogma. The truth is always beyond words."
            ),
        ],
    },
    {
        "filename": "nature_of_mind_discourse.pdf",
        "source_type": "discourse",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "The Nature of Mind — Morning Discourse",
            "date": "2024-10-15",
            "location": "Mountain Retreat Center",
            "event": "Autumn Silent Retreat",
            "verifier": "Senior Teacher Council",
            "access_tier": "devotee",
        },
        "passages": [
            (
                "The mind is not your enemy. It is an instrument — extraordinarily powerful, "
                "immensely creative, but dangerous when it runs without supervision. You "
                "would not let a sharp knife wield itself. The same care must be given to "
                "the mind: use it when needed, set it down when not."
            ),
            (
                "Thoughts have no substance. Close your eyes and try to find where a thought "
                "begins. You cannot. Try to find where it goes when it ends. You cannot. "
                "Thoughts are like drawings on water — vivid for a moment, then gone. "
                "The suffering comes not from thoughts but from believing they are real."
            ),
            (
                "The mind's nature is luminous. Beneath the constant chatter, beneath the "
                "anxiety and the planning, there is a clarity that has never been disturbed. "
                "It is like the sun behind clouds — the clouds come and go, but the sun "
                "has never moved. Your practice is to learn to see through the clouds."
            ),
            (
                "Memory creates the illusion of continuity. You believe you are the same "
                "person who woke up this morning, who existed last year, who was born decades "
                "ago. But look carefully: each moment you are new. The river is never the same "
                "water twice. You are a process, not a thing — and a process cannot be trapped."
            ),
            (
                "The difference between a wise person and a confused person is not the presence "
                "or absence of thoughts. Both have thoughts. The wise person sees the thought "
                "arise and lets it pass. The confused person sees the thought and calls it 'me.' "
                "This tiny difference — identification versus observation — is the entire "
                "distance between bondage and freedom."
            ),
        ],
    },
    {
        "filename": "daily_life_integration.pdf",
        "source_type": "discourse",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "Bringing Practice into Daily Life",
            "date": "2024-06-28",
            "location": "Riverside Ashram",
            "event": "Householder Retreat",
            "verifier": "Senior Teacher Council",
            "access_tier": "friend",
        },
        "passages": [
            (
                "Spirituality that exists only on the meditation cushion is incomplete. "
                "The real practice begins when you open your eyes — when you face the traffic, "
                "the difficult colleague, the crying child. Can you remain present in the "
                "marketplace? That is the test. The cushion is rehearsal; life is the performance."
            ),
            (
                "Every mundane task is an opportunity for awareness. Washing dishes, you feel "
                "the warmth of the water. Walking to work, you notice the texture of the ground. "
                "Listening to someone speak, you truly hear — not preparing your reply, not "
                "judging, just receiving. This is meditation in action."
            ),
            (
                "Relationships are the most powerful spiritual practice available. Every "
                "interaction is a mirror showing you where you are still attached, still "
                "reactive, still defending a self that does not need defending. The people "
                "who trigger you the most are your greatest teachers — they show you "
                "exactly where your work remains."
            ),
            (
                "Do not use spirituality to avoid difficult emotions. This is called spiritual "
                "bypassing — retreating into peace and equanimity as a way of not feeling "
                "grief, anger, or fear. The path does not ask you to transcend your humanity "
                "but to fully inhabit it. Feel everything. Just do not be carried away."
            ),
            (
                "Simplicity is a spiritual practice. The fewer things you accumulate — "
                "possessions, opinions, identities — the more space there is for awareness. "
                "This does not mean poverty or asceticism. It means choosing consciously: "
                "does this serve my awakening, or does it add weight to the dream?"
            ),
        ],
    },
]


def _generate_embeddings() -> list[list[float]]:
    """Generate real Gemini embeddings for all corpus passages.

    Collects all passages into a single list and embeds them in batches
    via get_embedder() (Gemini gemini-embedding-001, 3072→1024 truncated).
    """
    all_passages = [p for entry in CORPUS for p in entry["passages"]]
    print(f"  Generating Gemini embeddings for {len(all_passages)} passages...")
    embedder = get_embedder()
    embeddings = embedder.embed(all_passages)
    print(f"  Got {len(embeddings)} embeddings ({len(embeddings[0])} dims each)")
    return embeddings


def seed_documents(db, clone_id: uuid.UUID) -> list[tuple[uuid.UUID, dict]]:
    """Insert Document rows via SQLAlchemy ORM. Returns list of (doc_id, entry)."""
    inserted = []

    for entry in CORPUS:
        # Idempotency: check by filename + clone_id
        existing = (
            db.query(Document)
            .filter(Document.clone_id == clone_id, Document.filename == entry["filename"])
            .first()
        )
        if existing:
            print(f"  Document '{entry['provenance']['title']}' already exists — skipping")
            inserted.append((existing.id, entry))
            continue

        doc = Document(
            id=uuid.uuid4(),
            clone_id=clone_id,
            filename=entry["filename"],
            source_type=entry["source_type"],
            mime_type=entry["mime_type"],
            file_path=f"/data/sacred-archive/{entry['filename']}",
            provenance=entry["provenance"],
            chunk_count=len(entry["passages"]),
            status="indexed",
        )
        db.add(doc)
        db.flush()  # Assign the id before we reference it for chunks
        inserted.append((doc.id, entry))
        print(f"  Inserted document: {entry['provenance']['title']} ({len(entry['passages'])} chunks)")

    db.commit()
    return inserted


def seed_chunks(
    doc_list: list[tuple[uuid.UUID, dict]],
    clone_id: uuid.UUID,
    embeddings: list[list[float]],
):
    """Insert document_chunks via raw psycopg + pgvector (same pattern as indexer.py).

    Uses ON CONFLICT (chunk_id) DO UPDATE for idempotency — safe to re-run.
    Includes search_vector (tsvector) for BM25 hybrid search.
    All chunks use access_tier='devotee' (Sacred Archive's primary tier).
    """
    raw_url = psycopg_url()
    if not raw_url:
        print("  ERROR: DATABASE_URL not set — cannot insert chunks")
        return

    total_inserted = 0
    emb_idx = 0  # Index into the flat embeddings list

    with psycopg.connect(raw_url) as conn:
        register_vector(conn)

        for doc_id, entry in doc_list:
            rows = []
            for i, passage in enumerate(entry["passages"]):
                chunk_id = f"{doc_id}_{i:04d}"
                embedding = embeddings[emb_idx]
                emb_idx += 1
                rows.append((
                    str(doc_id),
                    str(clone_id),
                    i,                          # chunk_index
                    chunk_id,                   # chunk_id
                    passage,                    # passage
                    entry["source_type"],       # source_type
                    "devotee",                  # access_tier (Sacred Archive primary)
                    entry["provenance"].get("date"),  # date
                    embedding,                  # embedding (1024-dim vector)
                    passage,                    # repeated for to_tsvector('english', %s)
                ))

            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO document_chunks (
                        doc_id, clone_id, chunk_index, chunk_id, passage,
                        source_type, access_tier, date, embedding,
                        search_vector
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                        to_tsvector('english', %s))
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        passage = EXCLUDED.passage,
                        embedding = EXCLUDED.embedding,
                        search_vector = EXCLUDED.search_vector
                    """,
                    rows,
                )

            total_inserted += len(rows)

        conn.commit()

    print(f"  Inserted/updated {total_inserted} chunks across {len(doc_list)} documents")


def main():
    db = SessionLocal()
    try:
        print("=== Sacred Archive Corpus Seeder ===\n")

        # Step 1: Find the sacred-archive clone
        print("1. Looking up sacred-archive clone...")
        clone = db.query(Clone).filter(Clone.slug == "sacred-archive").first()
        if not clone:
            print("  ERROR: Clone 'sacred-archive' not found.")
            print("  Run 'python scripts/seed_db.py' first to create clone profiles.")
            return
        print(f"  Found clone: {clone.slug} (id={clone.id})")

        # Step 2: Generate real Gemini embeddings
        print("\n2. Generating embeddings via Gemini API...")
        embeddings = _generate_embeddings()

        # Step 3: Insert documents via ORM
        print("\n3. Seeding documents...")
        doc_list = seed_documents(db, clone.id)

        # Step 4: Insert chunks via raw psycopg (pgvector)
        print("\n4. Seeding document chunks (with Gemini embeddings + tsvector)...")
        seed_chunks(doc_list, clone.id, embeddings)

        # Summary
        total_passages = sum(len(e["passages"]) for e in CORPUS)
        print(f"\nDone. Seeded {len(CORPUS)} documents with {total_passages} chunks (real Gemini embeddings).")

    finally:
        db.close()


if __name__ == "__main__":
    main()
