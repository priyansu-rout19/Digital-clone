"""
CLI Query Script — Digital Clone Engine

Query a clone directly from the command line. Uses the full LangGraph pipeline
with real database, real vector search, real Mem0, and real Groq LLM.

Usage:
    python scripts/ask_clone.py "What is connectivity?"
    python scripts/ask_clone.py --clone sacred-archive "What is compassion?"
    python scripts/ask_clone.py -v "Tell me about supply chains"

Requires: .env with GROQ_API_KEY, GOOGLE_API_KEY, DATABASE_URL
          Database seeded (run seed_db.py + ingest_samples.py first)
"""

import os
import sys
import argparse
import time
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
            "clone_id": clone_id,
            "user_id": args.user_id,
            "retrieved_passages": [],
            "provenance_graph_results": [],
            "retrieval_confidence": 0.0,
            "retry_count": 0,
            "assembled_context": "",
            "user_memory": "",
            "raw_response": "",
            "verified_response": "",
            "final_confidence": 0.0,
            "cited_sources": [],
            "silence_triggered": False,
            "voice_chunks": [],
        }

        # --- Run the pipeline ---
        print(f'\nAsking {profile.display_name}: "{args.query}"\n')

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

        # --- Output ---
        print("=" * 60)
        print(response)
        print("=" * 60)

        if args.verbose:
            print("\n--- Pipeline Details ---")
            print(f"  Intent:       {result.get('intent_class', 'unknown')}")
            print(f"  Confidence:   {result.get('final_confidence', 0.0):.2f}")
            print(f"  Retrieval:    {result.get('retrieval_confidence', 0.0):.2f}")
            print(f"  Passages:     {len(result.get('retrieved_passages', []))}")
            print(f"  Citations:    {len(citations)}")
            print(f"  CRAG retries: {result.get('retry_count', 0)}")
            print(f"  Silence:      {result.get('silence_triggered', False)}")
            print(f"  Memory:       {'Yes' if result.get('user_memory') else 'No'}")
            print(f"  Time:         {elapsed:.1f}s")

            if citations:
                print("\n--- Citations ---")
                for i, cite in enumerate(citations, 1):
                    source_type = cite.get("source_type", "unknown")
                    doc_id = cite.get("doc_id", "?")
                    passage = cite.get("passage", "")
                    # Truncate long passages for readability
                    preview = passage[:80] + "..." if len(passage) > 80 else passage
                    print(f'  [{i}] {source_type} — {doc_id[:8]}...')
                    print(f'      "{preview}"')
        else:
            print(f"\nConfidence: {result.get('final_confidence', 0.0):.2f}"
                  f" | Citations: {len(citations)}"
                  f" | Time: {elapsed:.1f}s")

    finally:
        db.close()


if __name__ == "__main__":
    main()
