"""
ParaGPT 50-Query Evaluation Suite — Digital Clone Engine

Standalone script (not pytest) that runs 50 queries through the full LangGraph
pipeline and measures persona fidelity, citation presence, confidence, silence
behavior, and latency.

Run:
    python3 tests/eval_suite_paragpt.py

Requires:
    - PostgreSQL with seeded ParaGPT clone + corpus
    - .env with DATABASE_URL, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, GOOGLE_API_KEY
"""

import copy
import json
import re
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow imports from project root
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from core.db.schema import Clone
from core.evaluation.persona_scorer import score_persona_fidelity
from core.evaluation.consistency_checker import check_consistency
from core.langgraph.conversation_flow import build_graph
from core.models.clone_profile import CloneProfile, paragpt_profile


# ---------------------------------------------------------------------------
# 50 evaluation queries
# ---------------------------------------------------------------------------
# Categories:
#   in_corpus      — topic is covered by seeded corpus, expect a substantive answer
#   out_of_corpus  — topic is outside Parag Khanna's domain, expect hedge/silence
#   multi_turn     — follow-up that relies on prior conversational context
# ---------------------------------------------------------------------------

QUERIES: list[dict] = [
    # ── ASEAN (4) ──────────────────────────────────────────────────────────
    {"id": 1,  "query": "How is ASEAN reshaping the global economic order?", "category": "in_corpus"},
    {"id": 2,  "query": "What role does ASEAN play in balancing US-China competition?", "category": "in_corpus"},
    {"id": 3,  "query": "Which ASEAN nations are leading in digital infrastructure investment?", "category": "in_corpus"},
    {"id": 4,  "query": "You mentioned ASEAN earlier — how does intra-ASEAN trade compare to EU integration?", "category": "multi_turn"},

    # ── Supply Chains (4) ──────────────────────────────────────────────────
    {"id": 5,  "query": "How are global supply chains being restructured after recent disruptions?", "category": "in_corpus"},
    {"id": 6,  "query": "What is the China-plus-one strategy and why does it matter?", "category": "in_corpus"},
    {"id": 7,  "query": "How does supply chain diversification affect emerging economies?", "category": "in_corpus"},
    {"id": 8,  "query": "Can you elaborate on the resilience aspect you just described?", "category": "multi_turn"},

    # ── Asia Future (4) ────────────────────────────────────────────────────
    {"id": 9,  "query": "Why do you argue that the future is Asian?", "category": "in_corpus"},
    {"id": 10, "query": "How will Asia's demographic trends shape its economic trajectory?", "category": "in_corpus"},
    {"id": 11, "query": "What distinguishes Asian capitalism from Western models?", "category": "in_corpus"},
    {"id": 12, "query": "Going back to your point about Asia — how does Japan fit into that picture?", "category": "multi_turn"},

    # ── Connectivity (4) ───────────────────────────────────────────────────
    {"id": 13, "query": "What is Connectography and why is it important?", "category": "in_corpus"},
    {"id": 14, "query": "How does infrastructure connectivity redefine national borders?", "category": "in_corpus"},
    {"id": 15, "query": "What are the key connectivity corridors shaping the 21st century?", "category": "in_corpus"},
    {"id": 16, "query": "You mentioned corridors — which ones are most at risk from geopolitical tensions?", "category": "multi_turn"},

    # ── Climate & Migration (4) ────────────────────────────────────────────
    {"id": 17, "query": "How will climate change drive mass migration in the coming decades?", "category": "in_corpus"},
    {"id": 18, "query": "What is climate alpha and how should nations pursue it?", "category": "in_corpus"},
    {"id": 19, "query": "Which regions will gain population due to climate migration?", "category": "in_corpus"},
    {"id": 20, "query": "Can you expand on the climate adaptation strategies you just mentioned?", "category": "multi_turn"},

    # ── Urbanization (3) ───────────────────────────────────────────────────
    {"id": 21, "query": "How is rapid urbanization transforming governance in developing countries?", "category": "in_corpus"},
    {"id": 22, "query": "What role do megacities play in the global economy?", "category": "in_corpus"},
    {"id": 23, "query": "How should cities plan for sustainable growth given population pressures?", "category": "in_corpus"},

    # ── Governance (3) ─────────────────────────────────────────────────────
    {"id": 24, "query": "What does functional geography mean for how we govern?", "category": "in_corpus"},
    {"id": 25, "query": "How can governance structures adapt to a hyper-connected world?", "category": "in_corpus"},
    {"id": 26, "query": "Is the nation-state model becoming obsolete?", "category": "in_corpus"},

    # ── Talent & Migration (3) ─────────────────────────────────────────────
    {"id": 27, "query": "How does global talent migration affect innovation hubs?", "category": "in_corpus"},
    {"id": 28, "query": "What does your MOVE framework say about where people should relocate?", "category": "in_corpus"},
    {"id": 29, "query": "Which countries are winning the global talent competition?", "category": "in_corpus"},

    # ── Middle East (3) ────────────────────────────────────────────────────
    {"id": 30, "query": "How is the Middle East repositioning itself in global connectivity networks?", "category": "in_corpus"},
    {"id": 31, "query": "What role does the Gulf play in Asia-Europe trade corridors?", "category": "in_corpus"},
    {"id": 32, "query": "How are Middle Eastern sovereign wealth funds shaping infrastructure investment?", "category": "in_corpus"},

    # ── India (2) ──────────────────────────────────────────────────────────
    {"id": 33, "query": "How does India fit into the shifting global supply chain landscape?", "category": "in_corpus"},
    {"id": 34, "query": "What are the key obstacles to India becoming a manufacturing hub?", "category": "in_corpus"},

    # ── Technology & Geopolitics (3) ───────────────────────────────────────
    {"id": 35, "query": "How does technology competition between the US and China affect global governance?", "category": "in_corpus"},
    {"id": 36, "query": "What is the geopolitics of semiconductor supply chains?", "category": "in_corpus"},
    {"id": 37, "query": "How should nations approach AI governance in a multipolar world?", "category": "in_corpus"},

    # ── Globalization Paradox (2) ──────────────────────────────────────────
    {"id": 38, "query": "Is globalization in retreat or just being reconfigured?", "category": "in_corpus"},
    {"id": 39, "query": "How do you reconcile rising nationalism with deeper economic integration?", "category": "in_corpus"},

    # ── US-China (2) ───────────────────────────────────────────────────────
    {"id": 40, "query": "What does the US-China rivalry mean for the rest of the world?", "category": "in_corpus"},
    {"id": 41, "query": "Is decoupling between the US and China realistic or a myth?", "category": "in_corpus"},

    # ── Out-of-Corpus (9) — should trigger hedge / silence ────────────────
    {"id": 42, "query": "What is the best recipe for chocolate cake?", "category": "out_of_corpus"},
    {"id": 43, "query": "Can you explain quantum entanglement in simple terms?", "category": "out_of_corpus"},
    {"id": 44, "query": "Who won the 2024 Super Bowl?", "category": "out_of_corpus"},
    {"id": 45, "query": "What is the plot of the movie Inception?", "category": "out_of_corpus"},
    {"id": 46, "query": "How do I train for a marathon?", "category": "out_of_corpus"},
    {"id": 47, "query": "What is the meaning of life according to Aristotle?", "category": "out_of_corpus"},
    {"id": 48, "query": "Can you write me a Python script to sort a list?", "category": "out_of_corpus"},
    {"id": 49, "query": "What is the capital of Burkina Faso?", "category": "out_of_corpus"},
    {"id": 50, "query": "Explain the rules of cricket.", "category": "out_of_corpus"},
]


# ---------------------------------------------------------------------------
# Initial state template
# ---------------------------------------------------------------------------

def make_initial_state(query: str, clone_id: str) -> dict:
    """Build a fresh ConversationState dict for the pipeline."""
    return {
        "query_text": query,
        "clone_id": clone_id,
        "user_id": "eval-runner",
        "sub_queries": [],
        "intent_class": "",
        "access_tier": "public",
        "token_budget": 2000,
        "response_tokens": 0,
        "retrieved_passages": [],
        "provenance_graph_results": [],
        "retrieval_confidence": 0.0,
        "retry_count": 0,
        "search_meta": {},
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


# ---------------------------------------------------------------------------
# DB helper — fetch clone_id for ParaGPT
# ---------------------------------------------------------------------------

def get_paragpt_clone_id() -> str:
    """Load the ParaGPT clone row from PostgreSQL and return its UUID as a string."""
    import os

    db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres@localhost/dce_dev")
    engine = sa.create_engine(db_url)

    with DbSession(engine) as session:
        clone = session.query(Clone).filter(Clone.slug == "paragpt-client").first()
        if clone is None:
            print("ERROR: No clone with slug 'paragpt-client' found in database.")
            print("       Run the seed script first: python3 scripts/seed_paragpt_corpus.py")
            sys.exit(1)
        return str(clone.id)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_evaluation() -> list[dict]:
    """Execute all 50 queries and collect results."""

    print("=" * 80)
    print("ParaGPT Evaluation Suite — 50 Queries")
    print("=" * 80)

    # Setup
    clone_id = get_paragpt_clone_id()
    profile = paragpt_profile()
    persona_eval = profile.persona_eval
    graph = build_graph(profile)

    print(f"Clone ID : {clone_id}")
    print(f"Model    : {profile.generation_mode.value}")
    print(f"Threshold: {profile.confidence_threshold}")
    print(f"Queries  : {len(QUERIES)}")
    print("-" * 80)

    results: list[dict] = []

    for entry in QUERIES:
        qid = entry["id"]
        query = entry["query"]
        category = entry["category"]

        print(f"\n[{qid:02d}/50] ({category:14s}) {query[:70]}...")

        state = make_initial_state(query, clone_id)

        try:
            t0 = time.time()
            final_state = graph.invoke(copy.deepcopy(state))
            latency_ms = int((time.time() - t0) * 1000)

            response = final_state.get("verified_response") or final_state.get("raw_response") or ""
            cited_sources = final_state.get("cited_sources", [])
            silence = final_state.get("silence_triggered", False)
            confidence = final_state.get("final_confidence", 0.0)

            # Persona fidelity
            fidelity_result = score_persona_fidelity(response, persona_eval, cited_sources)
            persona_fidelity = fidelity_result["persona_fidelity"]

            # Citation check — look for [N] markers in response
            has_citations = bool(re.search(r'\[\d+\]', response))

            # Consistency check (empty history for single-turn queries)
            consistency_result = check_consistency(response, [])

            result = {
                "id": qid,
                "query": query,
                "category": category,
                "persona_fidelity": persona_fidelity,
                "vocabulary_match": fidelity_result["vocabulary_match"],
                "framework_usage": fidelity_result["framework_usage"],
                "domain_relevance": fidelity_result["domain_relevance"],
                "style_adherence": fidelity_result["style_adherence"],
                "has_citations": has_citations,
                "silence_triggered": silence,
                "confidence": round(confidence, 4),
                "latency_ms": latency_ms,
                "response_length": len(response.split()),
                "consistency_score": consistency_result["consistency_score"],
                "error": None,
                "response_preview": (response[:200] + "...") if len(response) > 200 else response,
            }

            status = "SILENCE" if silence else "OK"
            print(f"         -> {status} | fidelity={persona_fidelity:.2f} conf={confidence:.2f} "
                  f"cite={has_citations} latency={latency_ms}ms words={result['response_length']}")

        except Exception as exc:
            latency_ms = int((time.time() - t0) * 1000) if "t0" in dir() else 0
            result = {
                "id": qid,
                "query": query,
                "category": category,
                "persona_fidelity": 0.0,
                "vocabulary_match": 0.0,
                "framework_usage": 0.0,
                "domain_relevance": 0.0,
                "style_adherence": 0.0,
                "has_citations": False,
                "silence_triggered": False,
                "confidence": 0.0,
                "latency_ms": latency_ms,
                "response_length": 0,
                "consistency_score": 1.0,
                "error": str(exc),
                "response_preview": "",
            }
            print(f"         -> ERROR: {exc}")

        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_results_table(results: list[dict]) -> None:
    """Print a formatted table of per-query results."""

    print("\n")
    print("=" * 120)
    print(f"{'ID':>3} {'Category':<14} {'Fidelity':>8} {'Conf':>6} {'Cite':>5} "
          f"{'Silence':>7} {'Words':>5} {'ms':>6} {'Err':>4}  Query")
    print("-" * 120)

    for r in results:
        err_flag = "ERR" if r["error"] else ""
        cite_flag = "Y" if r["has_citations"] else "N"
        sil_flag = "Y" if r["silence_triggered"] else "N"
        print(f"{r['id']:>3} {r['category']:<14} {r['persona_fidelity']:>8.3f} "
              f"{r['confidence']:>6.3f} {cite_flag:>5} {sil_flag:>7} "
              f"{r['response_length']:>5} {r['latency_ms']:>6} {err_flag:>4}  "
              f"{r['query'][:55]}")

    print("=" * 120)


def print_summary(results: list[dict]) -> None:
    """Print aggregate statistics grouped by category."""

    print("\n")
    print("=" * 80)
    print("AGGREGATE SUMMARY")
    print("=" * 80)

    categories = ["in_corpus", "out_of_corpus", "multi_turn"]

    for cat in categories:
        cat_results = [r for r in results if r["category"] == cat and r["error"] is None]
        cat_errors = [r for r in results if r["category"] == cat and r["error"] is not None]
        total = len(cat_results) + len(cat_errors)

        if not cat_results:
            print(f"\n  {cat.upper()} ({total} queries) — all errored")
            continue

        avg_fidelity = sum(r["persona_fidelity"] for r in cat_results) / len(cat_results)
        avg_confidence = sum(r["confidence"] for r in cat_results) / len(cat_results)
        avg_latency = sum(r["latency_ms"] for r in cat_results) / len(cat_results)
        citation_rate = sum(1 for r in cat_results if r["has_citations"]) / len(cat_results)
        silence_rate = sum(1 for r in cat_results if r["silence_triggered"]) / len(cat_results)
        avg_words = sum(r["response_length"] for r in cat_results) / len(cat_results)

        print(f"\n  {cat.upper()} ({len(cat_results)} successful / {total} total)")
        print(f"    Avg persona fidelity : {avg_fidelity:.3f}")
        print(f"    Avg confidence       : {avg_confidence:.3f}")
        print(f"    Citation rate        : {citation_rate:.1%}")
        print(f"    Silence rate         : {silence_rate:.1%}")
        print(f"    Avg response length  : {avg_words:.0f} words")
        print(f"    Avg latency          : {avg_latency:.0f} ms")
        if cat_errors:
            print(f"    Errors               : {len(cat_errors)}")

    # Overall
    successful = [r for r in results if r["error"] is None]
    errored = [r for r in results if r["error"] is not None]

    print(f"\n  OVERALL ({len(successful)} successful / {len(results)} total)")
    if successful:
        print(f"    Avg persona fidelity : {sum(r['persona_fidelity'] for r in successful) / len(successful):.3f}")
        print(f"    Avg confidence       : {sum(r['confidence'] for r in successful) / len(successful):.3f}")
        print(f"    Avg latency          : {sum(r['latency_ms'] for r in successful) / len(successful):.0f} ms")

    # Quality checks
    print("\n  QUALITY CHECKS:")
    in_corpus_ok = [r for r in successful if r["category"] == "in_corpus"]
    out_of_corpus_ok = [r for r in successful if r["category"] == "out_of_corpus"]

    if in_corpus_ok:
        high_fidelity = sum(1 for r in in_corpus_ok if r["persona_fidelity"] >= 0.4) / len(in_corpus_ok)
        print(f"    In-corpus fidelity >= 0.4  : {high_fidelity:.1%} ({sum(1 for r in in_corpus_ok if r['persona_fidelity'] >= 0.4)}/{len(in_corpus_ok)})")

    if out_of_corpus_ok:
        silence_correct = sum(1 for r in out_of_corpus_ok if r["silence_triggered"] or r["confidence"] < 0.8) / len(out_of_corpus_ok)
        print(f"    Out-of-corpus hedge/silence : {silence_correct:.1%} ({sum(1 for r in out_of_corpus_ok if r['silence_triggered'] or r['confidence'] < 0.8)}/{len(out_of_corpus_ok)})")

    if errored:
        print(f"    Pipeline errors            : {len(errored)}")
        for r in errored:
            print(f"      Q{r['id']:02d}: {r['error'][:80]}")

    print("=" * 80)


def save_json_report(results: list[dict], path: str) -> None:
    """Save full results to JSON for downstream analysis."""
    report = {
        "suite": "eval_suite_paragpt",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_queries": len(results),
        "successful": sum(1 for r in results if r["error"] is None),
        "errored": sum(1 for r in results if r["error"] is not None),
        "results": results,
    }

    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nJSON report saved to: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    results = run_evaluation()
    print_results_table(results)
    print_summary(results)

    output_path = str(Path(__file__).parent / "eval_results_paragpt.json")
    save_json_report(results, output_path)
