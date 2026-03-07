"""
Batch Evaluation Script — Digital Clone Engine

Runs persona fidelity + consistency checks against message history.

Usage:
  python scripts/evaluate_responses.py --clone-slug paragpt-client
  python scripts/evaluate_responses.py --clone-slug sacred-archive --limit 20

Output: Summary statistics printed to stdout.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.db.schema import Clone, Message
from core.models.clone_profile import CloneProfile
from core.evaluation.persona_scorer import score_persona_fidelity
from core.evaluation.consistency_checker import check_consistency

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres@localhost/dce_dev")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def main():
    parser = argparse.ArgumentParser(description="Evaluate clone response quality")
    parser.add_argument("--clone-slug", required=True, help="Clone slug (e.g. paragpt-client)")
    parser.add_argument("--limit", type=int, default=50, help="Max messages to evaluate")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # Load clone
        clone = db.query(Clone).filter(Clone.slug == args.clone_slug).first()
        if not clone:
            print(f"Clone '{args.clone_slug}' not found.")
            return

        profile = CloneProfile(**clone.profile)
        persona_eval = profile.persona_eval

        if not persona_eval or not persona_eval.get("key_vocabulary"):
            print(f"Warning: persona_eval not configured for '{args.clone_slug}'. Scores will be neutral.")

        # Load messages
        messages = (
            db.query(Message)
            .filter(Message.clone_id == clone.id, Message.role == "assistant")
            .order_by(Message.created_at.desc())
            .limit(args.limit)
            .all()
        )

        if not messages:
            print(f"No assistant messages found for '{args.clone_slug}'.")
            print("Run some queries first, then re-run this script.")
            return

        print(f"=== Evaluation Report: {args.clone_slug} ===")
        print(f"Messages evaluated: {len(messages)}")
        print(f"Persona eval configured: {'Yes' if persona_eval.get('key_vocabulary') else 'No'}")
        print()

        # Persona fidelity scores
        fidelity_scores = []
        for msg in messages:
            result = score_persona_fidelity(
                response=msg.response_text or "",
                persona_eval=persona_eval,
                cited_sources=msg.cited_sources if hasattr(msg, "cited_sources") else None,
            )
            fidelity_scores.append(result)

        avg_fidelity = sum(s["persona_fidelity"] for s in fidelity_scores) / len(fidelity_scores)
        avg_vocab = sum(s["vocabulary_match"] for s in fidelity_scores) / len(fidelity_scores)
        avg_framework = sum(s["framework_usage"] for s in fidelity_scores) / len(fidelity_scores)
        avg_domain = sum(s["domain_relevance"] for s in fidelity_scores) / len(fidelity_scores)
        avg_style = sum(s["style_adherence"] for s in fidelity_scores) / len(fidelity_scores)

        print("--- Persona Fidelity ---")
        print(f"  Overall:          {avg_fidelity:.1%}  {'PASS' if avg_fidelity >= 0.85 else 'BELOW TARGET (85%)'}")
        print(f"  Vocabulary match: {avg_vocab:.1%}")
        print(f"  Framework usage:  {avg_framework:.1%}")
        print(f"  Domain relevance: {avg_domain:.1%}")
        print(f"  Style adherence:  {avg_style:.1%}")
        print()

        # Consistency check (compare each message against its preceding history)
        consistency_scores = []
        for i, msg in enumerate(messages):
            # Build history from older messages (messages are desc-ordered)
            history = [
                {"query_text": m.query_text or "", "response_text": m.response_text or ""}
                for m in messages[i + 1:]
            ]
            result = check_consistency(
                current_response=msg.response_text or "",
                history=history[:10],  # compare against 10 most recent
            )
            consistency_scores.append(result)

        avg_consistency = sum(s["consistency_score"] for s in consistency_scores) / len(consistency_scores)
        total_contradictions = sum(len(s["contradictions"]) for s in consistency_scores)

        print("--- Consistency ---")
        print(f"  Overall score:    {avg_consistency:.1%}")
        print(f"  Contradictions:   {total_contradictions} found across {len(messages)} messages")

        if total_contradictions > 0:
            print("\n  Top contradictions:")
            all_contradictions = [c for s in consistency_scores for c in s["contradictions"]]
            for c in sorted(all_contradictions, key=lambda x: -x["confidence"])[:3]:
                print(f"    [{c['type']}] confidence={c['confidence']:.2f}")
                print(f"      Current: {c['current_claim'][:80]}...")
                print(f"      Previous: {c['previous_claim'][:80]}...")

        print()
        print("--- Summary ---")
        passed = avg_fidelity >= 0.85 and avg_consistency >= 0.90
        print(f"  Persona fidelity: {avg_fidelity:.1%} (target: 85%)")
        print(f"  Consistency:      {avg_consistency:.1%} (target: 90%)")
        print(f"  Overall:          {'PASS' if passed else 'NEEDS IMPROVEMENT'}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
