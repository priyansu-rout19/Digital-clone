"""
CLI Query Script — Digital Clone Engine

Query a clone directly from the command line. Uses the full LangGraph pipeline
with real database, real vector search, real Mem0, and real Groq LLM.

Saves response text + MP3 audio to output/ folder automatically.

Usage:
    python scripts/ask_clone.py "What is connectivity?"
    python scripts/ask_clone.py --clone sacred-archive "What is compassion?"
    python scripts/ask_clone.py -v "Tell me about supply chains"
    python scripts/ask_clone.py --no-save "Quick test question"

Requires: .env with GROQ_API_KEY, GOOGLE_API_KEY, DATABASE_URL
          Database seeded (run seed_db.py + ingest_samples.py first)
"""

import os
import sys
import argparse
import base64
import time
from datetime import datetime
from pathlib import Path

# Add project root to sys.path so core/ imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.db.schema import Clone
from core.models.clone_profile import CloneProfile
from core.langgraph.conversation_flow import build_graph


def parse_args():
    parser = argparse.ArgumentParser(
        description="Query a Digital Clone from the command line"
    )
    parser.add_argument("query", help="The question to ask the clone")
    parser.add_argument(
        "--clone", default="paragpt-client",
        help="Clone slug (default: paragpt-client)"
    )
    parser.add_argument(
        "--user-id", default="cli-user",
        help="User ID for memory scoping (default: cli-user)"
    )
    parser.add_argument(
        "--access-tier", default="public",
        help="Access tier: public/devotee/friend/follower (default: public)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show detailed pipeline info"
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Don't save output files (audio + text)"
    )
    parser.add_argument(
        "--model", default="",
        help="Override LLM model (e.g. llama-3.3-70b-versatile). Default: env var LLM_MODEL"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # --- Database connection ---
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set. Add it to your .env file.")
        sys.exit(1)

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # --- Look up clone ---
        clone = db.query(Clone).filter(Clone.slug == args.clone).first()
        if not clone:
            print(f"ERROR: Clone '{args.clone}' not found.")
            print("Run: python scripts/seed_db.py")
            sys.exit(1)

        clone_id = str(clone.id)
        profile = CloneProfile(**clone.profile)

        # --- Build initial state ---
        initial_state = {
            "query_text": args.query,
            "sub_queries": [],
            "intent_class": "",
            "access_tier": args.access_tier,
            "token_budget": 2000,
            "response_tokens": 500,
            "clone_id": clone_id,
            "user_id": args.user_id,
            "retrieved_passages": [],
            "provenance_graph_results": [],
            "retrieval_confidence": 0.0,
            "retry_count": 0,
            "assembled_context": "",
            "user_memory": "",
            "conversation_history": "",
            "raw_response": "",
            "verified_response": "",
            "final_confidence": 0.0,
            "cited_sources": [],
            "silence_triggered": False,
            "suggested_topics": [],
            "voice_chunks": [],
            "audio_base64": "",
            "audio_format": "",
            "model_override": args.model,
        }

        # --- Run the pipeline ---
        from core.llm import LLM_MODEL
        effective_model = args.model or LLM_MODEL
        print(f'\nAsking {profile.display_name}: "{args.query}"')
        print(f'Model: {effective_model}\n')

        start = time.time()
        graph = build_graph(profile)
        result = graph.invoke(initial_state)
        elapsed = time.time() - start

        # --- Pick the best available response text ---
        response = (
            result.get("verified_response")
            or result.get("raw_response")
            or "(no response generated)"
        )

        citations = result.get("cited_sources", [])

        # --- Save to messages table (enables multi-turn conversation history) ---
        from core.db.schema import Message
        msg = Message(
            clone_id=clone_id,
            user_id=args.user_id,
            query_text=args.query,
            response_text=response,
            confidence=result.get("final_confidence", 0.0),
            silence_triggered=result.get("silence_triggered", False),
            cited_sources=citations,
        )
        db.add(msg)
        db.commit()

        # --- Output ---
        print("=" * 60)
        print(response)
        print("=" * 60)

        if args.verbose:
            print("\n--- Pipeline Details ---")
            print(f"  Intent:        {result.get('intent_class', 'unknown')}")
            print(f"  Token budget:  {result.get('token_budget', '?')}")
            print(f"  Resp tokens:   {result.get('response_tokens', '?')}")
            print(f"  Confidence:    {result.get('final_confidence', 0.0):.2f}")
            print(f"  Retrieval:     {result.get('retrieval_confidence', 0.0):.2f}")
            print(f"  Passages:      {len(result.get('retrieved_passages', []))}")
            print(f"  Citations:     {len(citations)}")
            print(f"  CRAG retries:  {result.get('retry_count', 0)}")
            print(f"  Silence:       {result.get('silence_triggered', False)}")
            print(f"  Memory:        {'Yes' if result.get('user_memory') else 'No'}")
            print(f"  Time:          {elapsed:.1f}s")

            # Session 16: voice chunks & audio
            voice_chunks = result.get("voice_chunks", [])
            audio_b64 = result.get("audio_base64", "")
            audio_fmt = result.get("audio_format", "")
            print(f"\n--- Voice / TTS ---")
            print(f"  Voice chunks:  {len(voice_chunks)}")
            if voice_chunks:
                for i, chunk in enumerate(voice_chunks[:5], 1):
                    preview = chunk[:80] + "..." if len(chunk) > 80 else chunk
                    print(f"    [{i}] {preview}")
                if len(voice_chunks) > 5:
                    print(f"    ... and {len(voice_chunks) - 5} more")
            print(f"  Audio format:  {audio_fmt or 'none'}")
            print(f"  Audio size:    {len(audio_b64) * 3 // 4 // 1024} KB" if audio_b64 else "  Audio size:    0 (no audio)")

            if citations:
                print("\n--- Citations ---")
                for i, cite in enumerate(citations, 1):
                    source_type = cite.get("source_type", "unknown")
                    doc_id = cite.get("doc_id", "?")
                    passage = cite.get("passage", "")
                    preview = passage[:80] + "..." if len(passage) > 80 else passage
                    print(f'  [{i}] {source_type} — {doc_id[:8]}...')
                    print(f'      "{preview}"')
        else:
            print(f"\nConfidence: {result.get('final_confidence', 0.0):.2f}"
                  f" | Citations: {len(citations)}"
                  f" | Time: {elapsed:.1f}s")

        # --- Save output files ---
        if not args.no_save:
            _save_output(args, result, response, citations, elapsed)

    finally:
        db.close()


def _save_output(args, result, response, citations, elapsed):
    """Save response text and audio MP3 to output/ folder."""
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Timestamp-based filename: 2026-03-05_14-30-22_paragpt-client
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    slug = args.clone.replace("/", "-")
    base_name = f"{ts}_{slug}"

    # --- Save text response ---
    text_path = output_dir / f"{base_name}.txt"
    with open(text_path, "w") as f:
        f.write(f"Query: {args.query}\n")
        f.write(f"Clone: {args.clone}\n")
        f.write(f"Time: {elapsed:.1f}s\n")
        f.write(f"Confidence: {result.get('final_confidence', 0.0):.2f}\n")
        f.write(f"Intent: {result.get('intent_class', 'unknown')}\n")
        f.write(f"Token Budget: {result.get('token_budget', '?')}\n")
        f.write(f"Silence: {result.get('silence_triggered', False)}\n")
        f.write(f"\n{'=' * 60}\nRESPONSE\n{'=' * 60}\n\n")
        f.write(response)
        f.write("\n")

        # Voice chunks
        voice_chunks = result.get("voice_chunks", [])
        if voice_chunks:
            f.write(f"\n{'=' * 60}\nVOICE CHUNKS ({len(voice_chunks)})\n{'=' * 60}\n\n")
            for i, chunk in enumerate(voice_chunks, 1):
                f.write(f"[{i}] {chunk}\n")

        # Citations
        if citations:
            f.write(f"\n{'=' * 60}\nCITATIONS ({len(citations)})\n{'=' * 60}\n\n")
            for i, cite in enumerate(citations, 1):
                f.write(f"[{i}] {cite.get('source_type', 'unknown')} — {cite.get('doc_id', '?')}\n")
                f.write(f"    {cite.get('passage', '')[:200]}\n\n")

    print(f"\n  Saved text:  {text_path}")

    # --- Save audio MP3 (if generated) ---
    audio_b64 = result.get("audio_base64", "")
    audio_fmt = result.get("audio_format", "mp3")
    if audio_b64:
        audio_path = output_dir / f"{base_name}.{audio_fmt}"
        audio_bytes = base64.b64decode(audio_b64)
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        size_kb = len(audio_bytes) / 1024
        print(f"  Saved audio: {audio_path} ({size_kb:.0f} KB)")
    else:
        print("  No audio generated (text_only mode or TTS skipped)")


if __name__ == "__main__":
    main()
