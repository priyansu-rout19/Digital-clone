#!/usr/bin/env python3
"""
Foundation Gate — 30-query pass/fail quality gate for Digital Clone Engine.

Runs 15 queries per client (ParaGPT + Sacred Archive) through the full
LangGraph pipeline and measures citation accuracy, persona fidelity,
and silence precision.

Gate thresholds:
  - Citation accuracy: >90% of in_corpus queries must have [N] citations
  - Persona fidelity:  mean >0.80 across all in_corpus responses
  - Silence precision:  >95% of out_of_corpus queries trigger silence/hedge

Exit code 0 = PASS, 1 = FAIL.
"""

import copy
import json
import re
import sys
import time
from pathlib import Path

# Project root on sys.path so imports resolve
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import psycopg
from core.db import psycopg_url
from core.db.schema import Clone
from core.models.clone_profile import CloneProfile, paragpt_profile, sacred_archive_profile
from core.langgraph.conversation_flow import build_graph
from core.evaluation.persona_scorer import score_persona_fidelity


# ---------------------------------------------------------------------------
# Test queries — each tagged as in_corpus (expect response) or out_of_corpus
# (expect silence/hedge).
# ---------------------------------------------------------------------------

PARAGPT_QUERIES = [
    # In-corpus (11): core Parag Khanna topics with seeded corpus
    {"query": "How is global connectivity reshaping geopolitics?", "in_corpus": True},
    {"query": "What is Connectography and why does it matter?", "in_corpus": True},
    {"query": "How are supply chains being restructured after COVID?", "in_corpus": True},
    {"query": "What role does ASEAN play in the future of Asia?", "in_corpus": True},
    {"query": "How does infrastructure investment drive economic growth?", "in_corpus": True},
    {"query": "What is the China-plus-one strategy?", "in_corpus": True},
    {"query": "How does climate change drive migration patterns?", "in_corpus": True},
    {"query": "What is functional geography?", "in_corpus": True},
    {"query": "How is urbanization transforming the developing world?", "in_corpus": True},
    {"query": "What are the key corridors of global trade?", "in_corpus": True},
    {"query": "How should countries approach AI governance?", "in_corpus": True},
    # Out-of-corpus (4): topics Parag Khanna would not cover
    {"query": "What is the best recipe for chocolate cake?", "in_corpus": False},
    {"query": "Explain quantum chromodynamics in detail.", "in_corpus": False},
    {"query": "Who will win the next Super Bowl?", "in_corpus": False},
    {"query": "How do I fix a leaking kitchen faucet?", "in_corpus": False},
]

SACRED_ARCHIVE_QUERIES = [
    # In-corpus (11): core spiritual teaching topics with seeded corpus
    {"query": "What is the role of silence in meditation?", "in_corpus": True},
    {"query": "How does one cultivate awareness in daily life?", "in_corpus": True},
    {"query": "What is the nature of devotion?", "in_corpus": True},
    {"query": "How does compassion relate to spiritual practice?", "in_corpus": True},
    {"query": "What is self-inquiry and how is it practiced?", "in_corpus": True},
    {"query": "What is the relationship between teacher and student?", "in_corpus": True},
    {"query": "How does one still the mind?", "in_corpus": True},
    {"query": "What teachings exist on surrender?", "in_corpus": True},
    {"query": "How is presence cultivated through practice?", "in_corpus": True},
    {"query": "What is the nature of the heart in spiritual traditions?", "in_corpus": True},
    {"query": "What does wisdom mean in the context of daily practice?", "in_corpus": True},
    # Out-of-corpus (4): topics the archive would not address
    {"query": "What is the current stock price of Tesla?", "in_corpus": False},
    {"query": "How do I configure a Kubernetes cluster?", "in_corpus": False},
    {"query": "What are the rules of American football?", "in_corpus": False},
    {"query": "Explain the Krebs cycle in biochemistry.", "in_corpus": False},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_clone_from_db(slug: str) -> tuple[str, CloneProfile]:
    """Load a clone row from DB and return (clone_id, CloneProfile)."""
    db_url = psycopg_url()
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, profile FROM clones WHERE slug = %s", (slug,)
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Clone '{slug}' not found in database")
            clone_id = str(row[0])
            profile = CloneProfile(**row[1])
            return clone_id, profile


def build_initial_state(query: str, clone_id: str) -> dict:
    """Build initial ConversationState matching chat.py's build_initial_state."""
    return {
        "query_text": query,
        "clone_id": clone_id,
        "user_id": "foundation-gate",
        "sub_queries": [],
        "intent_class": "",
        "access_tier": "public",
        "token_budget": 2000,
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
        "model_override": "",
        "review_id": "",
        "voice_enabled": False,
    }


def has_citation(response: str) -> bool:
    """Check if response contains at least one [N] citation marker."""
    return bool(re.search(r"\[\d+\]", response))


def run_query(graph, clone_id: str, query: str) -> dict:
    """Run a single query through the pipeline and return the final state."""
    state = build_initial_state(query, clone_id)
    final_state = graph.invoke(copy.deepcopy(state))
    return final_state


# ---------------------------------------------------------------------------
# Main gate logic
# ---------------------------------------------------------------------------

def run_gate():
    print("=" * 70)
    print("  FOUNDATION GATE — Digital Clone Engine")
    print("=" * 70)
    print()

    results = {"paragpt": [], "sacred_archive": []}
    all_ok = True

    for client_key, slug, queries, fallback_profile in [
        ("paragpt", "paragpt-client", PARAGPT_QUERIES, paragpt_profile),
        ("sacred_archive", "sacred-archive", SACRED_ARCHIVE_QUERIES, sacred_archive_profile),
    ]:
        print(f"--- {client_key.upper()} ({slug}) ---")

        # Load clone from DB; fall back to preset profile if not found
        try:
            clone_id, profile = load_clone_from_db(slug)
            print(f"  Loaded clone from DB: {clone_id}")
        except Exception as e:
            print(f"  DB lookup failed ({e}), using preset profile")
            profile = fallback_profile()
            clone_id = "00000000-0000-0000-0000-000000000000"

        graph = build_graph(profile)
        persona_eval = profile.persona_eval

        for i, q in enumerate(queries, 1):
            query_text = q["query"]
            in_corpus = q["in_corpus"]
            label = "IN_CORPUS" if in_corpus else "OUT_OF_CORPUS"

            print(f"  [{i:02d}/{len(queries)}] ({label}) {query_text[:60]}...", end=" ", flush=True)
            t0 = time.time()

            try:
                final_state = run_query(graph, clone_id, query_text)
                elapsed = time.time() - t0

                response = final_state.get("verified_response", "") or final_state.get("raw_response", "")
                silence = final_state.get("silence_triggered", False)
                cited = final_state.get("cited_sources", [])
                confidence = final_state.get("final_confidence", 0.0)

                # Measure citation presence
                citation_present = has_citation(response)

                # Measure persona fidelity (only meaningful for in_corpus)
                fidelity_result = score_persona_fidelity(response, persona_eval, cited)
                persona_fidelity = fidelity_result["persona_fidelity"]

                # Silence correctness
                if in_corpus:
                    # In-corpus: silence should NOT trigger
                    silence_correct = not silence
                else:
                    # Out-of-corpus: silence SHOULD trigger (or response should be a hedge)
                    silence_correct = silence

                result = {
                    "client": client_key,
                    "query": query_text,
                    "in_corpus": in_corpus,
                    "response_preview": response[:200],
                    "citation_present": citation_present,
                    "persona_fidelity": persona_fidelity,
                    "fidelity_details": fidelity_result["details"],
                    "silence_triggered": silence,
                    "silence_correct": silence_correct,
                    "final_confidence": confidence,
                    "elapsed_s": round(elapsed, 2),
                    "error": None,
                }

                status = "OK" if (silence_correct and (not in_corpus or citation_present)) else "WARN"
                print(f"{status} ({elapsed:.1f}s, conf={confidence:.2f}, fidelity={persona_fidelity:.2f})")

            except Exception as e:
                elapsed = time.time() - t0
                result = {
                    "client": client_key,
                    "query": query_text,
                    "in_corpus": in_corpus,
                    "response_preview": "",
                    "citation_present": False,
                    "persona_fidelity": 0.0,
                    "fidelity_details": {},
                    "silence_triggered": False,
                    "silence_correct": False,
                    "final_confidence": 0.0,
                    "elapsed_s": round(elapsed, 2),
                    "error": str(e),
                }
                print(f"ERROR ({elapsed:.1f}s): {e}")

            results[client_key].append(result)

        print()

    # -----------------------------------------------------------------------
    # Compute gate metrics
    # -----------------------------------------------------------------------
    all_results = results["paragpt"] + results["sacred_archive"]

    in_corpus_results = [r for r in all_results if r["in_corpus"] and not r["error"]]
    out_of_corpus_results = [r for r in all_results if not r["in_corpus"] and not r["error"]]

    # Citation accuracy: % of in_corpus queries with [N] markers
    if in_corpus_results:
        citation_hits = sum(1 for r in in_corpus_results if r["citation_present"])
        citation_accuracy = citation_hits / len(in_corpus_results)
    else:
        citation_accuracy = 0.0

    # Persona fidelity: mean across in_corpus responses
    if in_corpus_results:
        fidelity_scores = [r["persona_fidelity"] for r in in_corpus_results]
        mean_fidelity = sum(fidelity_scores) / len(fidelity_scores)
    else:
        mean_fidelity = 0.0

    # Silence precision: % of out_of_corpus queries that triggered silence
    if out_of_corpus_results:
        silence_hits = sum(1 for r in out_of_corpus_results if r["silence_correct"])
        silence_precision = silence_hits / len(out_of_corpus_results)
    else:
        silence_precision = 0.0

    # -----------------------------------------------------------------------
    # Gate thresholds
    # -----------------------------------------------------------------------
    CITATION_THRESHOLD = 0.90
    FIDELITY_THRESHOLD = 0.80
    SILENCE_THRESHOLD = 0.95

    citation_pass = citation_accuracy >= CITATION_THRESHOLD
    fidelity_pass = mean_fidelity >= FIDELITY_THRESHOLD
    silence_pass = silence_precision >= SILENCE_THRESHOLD
    overall_pass = citation_pass and fidelity_pass and silence_pass

    # -----------------------------------------------------------------------
    # Terminal output
    # -----------------------------------------------------------------------
    print("=" * 70)
    print("  GATE RESULTS")
    print("=" * 70)
    print()
    print(f"  Citation Accuracy:  {citation_accuracy:.1%}  "
          f"(threshold: {CITATION_THRESHOLD:.0%})  "
          f"{'PASS' if citation_pass else 'FAIL'}")
    print(f"  Persona Fidelity:   {mean_fidelity:.4f}  "
          f"(threshold: {FIDELITY_THRESHOLD:.2f})  "
          f"{'PASS' if fidelity_pass else 'FAIL'}")
    print(f"  Silence Precision:  {silence_precision:.1%}  "
          f"(threshold: {SILENCE_THRESHOLD:.0%})  "
          f"{'PASS' if silence_pass else 'FAIL'}")
    print()
    print(f"  Queries run:       {len(all_results)}")
    print(f"    In-corpus:       {len(in_corpus_results)}")
    print(f"    Out-of-corpus:   {len(out_of_corpus_results)}")
    errors = [r for r in all_results if r["error"]]
    if errors:
        print(f"    Errors:          {len(errors)}")
    print()
    print(f"  OVERALL GATE:  {'PASS' if overall_pass else 'FAIL'}")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # JSON report
    # -----------------------------------------------------------------------
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gate_result": "PASS" if overall_pass else "FAIL",
        "metrics": {
            "citation_accuracy": round(citation_accuracy, 4),
            "citation_threshold": CITATION_THRESHOLD,
            "citation_pass": citation_pass,
            "persona_fidelity_mean": round(mean_fidelity, 4),
            "fidelity_threshold": FIDELITY_THRESHOLD,
            "fidelity_pass": fidelity_pass,
            "silence_precision": round(silence_precision, 4),
            "silence_threshold": SILENCE_THRESHOLD,
            "silence_pass": silence_pass,
        },
        "summary": {
            "total_queries": len(all_results),
            "in_corpus": len(in_corpus_results),
            "out_of_corpus": len(out_of_corpus_results),
            "errors": len(errors),
        },
        "results": all_results,
    }

    output_path = Path(__file__).parent / "foundation_gate_results.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Report saved to: {output_path}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(run_gate())
