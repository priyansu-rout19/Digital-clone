"""
Sacred Archive — 50-Query Evaluation Suite

Standalone script (not pytest). Runs 50 queries through the Sacred Archive
LangGraph pipeline, scoring each response for persona fidelity, citation
presence, silence behavior, forbidden-pattern violations, and latency.

Usage:
    python3 scripts/eval_suite_sacred_archive.py

Outputs:
    - Per-query table to stdout
    - Aggregate summary to stdout
    - JSON results to scripts/eval_results_sacred_archive.json
"""

import json
import sys
import time
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import psycopg
from core.db import psycopg_url
from core.models.clone_profile import CloneProfile, sacred_archive_profile
from core.langgraph.conversation_flow import build_graph
from core.evaluation.persona_scorer import score_persona_fidelity
from core.evaluation.consistency_checker import check_consistency

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORBIDDEN_PATTERNS = ["in my opinion", "I think", "perhaps"]

PERSONA_EVAL = sacred_archive_profile().persona_eval

# ---------------------------------------------------------------------------
# 50 Evaluation Queries
# ---------------------------------------------------------------------------
# Categories:
#   in_corpus     — topics the corpus covers; expect direct-quote responses
#   out_of_corpus — off-topic; should trigger strict silence
#   tier_test     — tests access-tier gating (devotee / friend / follower)
# ---------------------------------------------------------------------------

QUERIES: list[dict] = [
    # ── in_corpus: meditation (8) ──────────────────────────────────────────
    {"query": "What is the purpose of meditation?", "tier": "devotee", "category": "in_corpus"},
    {"query": "How should a beginner approach meditation?", "tier": "friend", "category": "in_corpus"},
    {"query": "What happens when the mind becomes still during meditation?", "tier": "devotee", "category": "in_corpus"},
    {"query": "Is there a correct posture for meditation?", "tier": "follower", "category": "in_corpus"},
    {"query": "How does meditation relate to daily life?", "tier": "friend", "category": "in_corpus"},
    {"query": "What are the obstacles to deep meditation?", "tier": "devotee", "category": "in_corpus"},
    {"query": "Can meditation be practiced while working?", "tier": "follower", "category": "in_corpus"},
    {"query": "What is the difference between concentration and meditation?", "tier": "devotee", "category": "in_corpus"},

    # ── in_corpus: silence (5) ─────────────────────────────────────────────
    {"query": "What is the teaching on inner silence?", "tier": "devotee", "category": "in_corpus"},
    {"query": "Why is silence considered sacred?", "tier": "friend", "category": "in_corpus"},
    {"query": "How does one enter the state of silence?", "tier": "devotee", "category": "in_corpus"},
    {"query": "What role does silence play in the teacher-student relationship?", "tier": "devotee", "category": "in_corpus"},
    {"query": "Is silence the same as emptiness?", "tier": "follower", "category": "in_corpus"},

    # ── in_corpus: devotion (4) ────────────────────────────────────────────
    {"query": "What is the nature of true devotion?", "tier": "devotee", "category": "in_corpus"},
    {"query": "How does devotion differ from blind faith?", "tier": "friend", "category": "in_corpus"},
    {"query": "What is the relationship between devotion and surrender?", "tier": "devotee", "category": "in_corpus"},
    {"query": "Can devotion exist without a teacher?", "tier": "follower", "category": "in_corpus"},

    # ── in_corpus: compassion (3) ──────────────────────────────────────────
    {"query": "What does the teaching say about compassion?", "tier": "devotee", "category": "in_corpus"},
    {"query": "How is compassion cultivated in daily practice?", "tier": "friend", "category": "in_corpus"},
    {"query": "Is compassion for others the same as compassion for oneself?", "tier": "follower", "category": "in_corpus"},

    # ── in_corpus: self-inquiry (3) ────────────────────────────────────────
    {"query": "What is self-inquiry and how is it practiced?", "tier": "devotee", "category": "in_corpus"},
    {"query": "What question should a seeker ask themselves?", "tier": "friend", "category": "in_corpus"},
    {"query": "How does self-inquiry lead to awareness?", "tier": "devotee", "category": "in_corpus"},

    # ── in_corpus: awareness (3) ───────────────────────────────────────────
    {"query": "What is awareness according to the teachings?", "tier": "devotee", "category": "in_corpus"},
    {"query": "How is awareness different from thinking?", "tier": "friend", "category": "in_corpus"},
    {"query": "Can awareness be lost or is it always present?", "tier": "follower", "category": "in_corpus"},

    # ── in_corpus: surrender (2) ───────────────────────────────────────────
    {"query": "What does surrender mean in spiritual practice?", "tier": "devotee", "category": "in_corpus"},
    {"query": "Is surrender a passive or active practice?", "tier": "friend", "category": "in_corpus"},

    # ── in_corpus: nature of mind (2) ──────────────────────────────────────
    {"query": "What is the nature of the mind according to the teachings?", "tier": "devotee", "category": "in_corpus"},
    {"query": "How does one go beyond the mind?", "tier": "friend", "category": "in_corpus"},

    # ── in_corpus: teacher-student (2) ─────────────────────────────────────
    {"query": "What is the role of a teacher on the spiritual path?", "tier": "devotee", "category": "in_corpus"},
    {"query": "How should a student approach the teacher?", "tier": "friend", "category": "in_corpus"},

    # ── in_corpus: daily practice (2) ──────────────────────────────────────
    {"query": "What daily practices are recommended for a seeker?", "tier": "devotee", "category": "in_corpus"},
    {"query": "How does one maintain spiritual practice amid worldly duties?", "tier": "follower", "category": "in_corpus"},

    # ── out_of_corpus (14) ─────────────────────────────────────────────────
    {"query": "What is the best stock to invest in right now?", "tier": "devotee", "category": "out_of_corpus"},
    {"query": "Can you write Python code to sort a list?", "tier": "devotee", "category": "out_of_corpus"},
    {"query": "Who won the 2024 US presidential election?", "tier": "friend", "category": "out_of_corpus"},
    {"query": "What is the recipe for chocolate cake?", "tier": "follower", "category": "out_of_corpus"},
    {"query": "Explain quantum computing in simple terms.", "tier": "devotee", "category": "out_of_corpus"},
    {"query": "What is your opinion on cryptocurrency?", "tier": "friend", "category": "out_of_corpus"},
    {"query": "Tell me a joke about programmers.", "tier": "follower", "category": "out_of_corpus"},
    {"query": "How do I fix a leaking faucet?", "tier": "devotee", "category": "out_of_corpus"},
    {"query": "What are the rules of basketball?", "tier": "friend", "category": "out_of_corpus"},
    {"query": "Translate this sentence to French: hello world.", "tier": "follower", "category": "out_of_corpus"},
    {"query": "What is the capital of Mongolia?", "tier": "devotee", "category": "out_of_corpus"},
    {"query": "How do neural networks learn?", "tier": "friend", "category": "out_of_corpus"},
    {"query": "Write a haiku about summer.", "tier": "follower", "category": "out_of_corpus"},
    {"query": "What is the GDP of Brazil?", "tier": "devotee", "category": "out_of_corpus"},

    # ── tier_test (2) ──────────────────────────────────────────────────────
    {"query": "What is the deepest secret teaching on silence?", "tier": "follower", "category": "tier_test"},
    {"query": "Share the most advanced meditation instruction.", "tier": "friend", "category": "tier_test"},
]

assert len(QUERIES) == 50, f"Expected 50 queries, got {len(QUERIES)}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_clone_id() -> str:
    """Fetch the Sacred Archive clone_id from the database."""
    url = psycopg_url()
    with psycopg.connect(url) as conn:
        row = conn.execute(
            "SELECT id FROM clones WHERE slug = 'sacred-archive'"
        ).fetchone()
    if not row:
        print("ERROR: No clone with slug='sacred-archive' found in the database.")
        print("       Run the seed script first.")
        sys.exit(1)
    return str(row[0])


def _get_profile() -> CloneProfile:
    """Load profile from DB, fall back to factory preset."""
    url = psycopg_url()
    with psycopg.connect(url) as conn:
        row = conn.execute(
            "SELECT profile FROM clones WHERE slug = 'sacred-archive'"
        ).fetchone()
    if row and row[0]:
        return CloneProfile(**row[0])
    return sacred_archive_profile()


def _build_initial_state(query: str, clone_id: str, tier: str) -> dict:
    """Build a fresh ConversationState dict for one query."""
    return {
        "query_text": query,
        "clone_id": clone_id,
        "user_id": "eval-runner",
        "sub_queries": [],
        "intent_class": "",
        "access_tier": tier,
        "token_budget": 2000,
        "response_tokens": 0,
        "model_override": "",
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
        "review_id": "",
        "voice_enabled": False,
    }


def _check_forbidden_patterns(response: str) -> list[str]:
    """Return list of forbidden patterns found in the response."""
    lower = response.lower()
    return [p for p in FORBIDDEN_PATTERNS if p.lower() in lower]


def _run_single_query(
    graph,
    query_spec: dict,
    clone_id: str,
    index: int,
) -> dict:
    """Run one query through the pipeline and collect all metrics."""
    query = query_spec["query"]
    tier = query_spec["tier"]
    category = query_spec["category"]

    result = {
        "index": index + 1,
        "query": query,
        "tier": tier,
        "category": category,
        "response": "",
        "silence_triggered": False,
        "final_confidence": 0.0,
        "has_citations": False,
        "persona_fidelity": 0.0,
        "forbidden_violations": [],
        "forbidden_pattern_check": True,  # True = PASS (no violations)
        "consistency_score": 1.0,
        "latency_ms": 0,
        "error": None,
    }

    try:
        state = _build_initial_state(query, clone_id, tier)
        t0 = time.perf_counter()
        final_state = graph.invoke(state)
        t1 = time.perf_counter()

        response = final_state.get("verified_response") or final_state.get("raw_response") or ""
        cited = final_state.get("cited_sources") or []

        result["response"] = response
        result["silence_triggered"] = bool(final_state.get("silence_triggered", False))
        result["final_confidence"] = round(final_state.get("final_confidence", 0.0), 4)
        result["has_citations"] = len(cited) > 0
        result["latency_ms"] = round((t1 - t0) * 1000)

        # Persona fidelity (only meaningful when there is a real response)
        if response and not result["silence_triggered"]:
            pf = score_persona_fidelity(response, PERSONA_EVAL, cited)
            result["persona_fidelity"] = pf["persona_fidelity"]
        else:
            result["persona_fidelity"] = None  # N/A for silence

        # Forbidden pattern check
        violations = _check_forbidden_patterns(response)
        result["forbidden_violations"] = violations
        result["forbidden_pattern_check"] = len(violations) == 0

        # Consistency (no history for single-shot eval, always 1.0)
        result["consistency_score"] = 1.0

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()

    return result


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_table(results: list[dict]) -> None:
    """Print a per-query results table."""
    header = (
        f"{'#':>3}  {'Category':<14} {'Tier':<10} "
        f"{'Silence':>7} {'Cites':>5} {'Conf':>6} {'Fidelity':>8} "
        f"{'Forbid':>6} {'ms':>6}  Query"
    )
    sep = "-" * min(len(header) + 40, 140)

    print("\n" + sep)
    print("SACRED ARCHIVE EVALUATION RESULTS — 50 Queries")
    print(sep)
    print(header)
    print(sep)

    for r in results:
        fidelity_str = f"{r['persona_fidelity']:.2f}" if r["persona_fidelity"] is not None else "  N/A"
        error_mark = " [ERR]" if r["error"] else ""
        forbid_str = "PASS" if r["forbidden_pattern_check"] else "FAIL"
        silence_str = "YES" if r["silence_triggered"] else "no"
        cites_str = "YES" if r["has_citations"] else "no"
        query_trunc = r["query"][:50] + ("..." if len(r["query"]) > 50 else "")

        print(
            f"{r['index']:>3}  {r['category']:<14} {r['tier']:<10} "
            f"{silence_str:>7} {cites_str:>5} {r['final_confidence']:>6.2f} {fidelity_str:>8} "
            f"{forbid_str:>6} {r['latency_ms']:>6}  {query_trunc}{error_mark}"
        )

    print(sep)


def _print_summary(results: list[dict]) -> None:
    """Print aggregate summary statistics."""
    total = len(results)
    errors = [r for r in results if r["error"]]
    successful = [r for r in results if not r["error"]]

    in_corpus = [r for r in successful if r["category"] == "in_corpus"]
    out_corpus = [r for r in successful if r["category"] == "out_of_corpus"]
    tier_tests = [r for r in successful if r["category"] == "tier_test"]

    # -- In-corpus metrics --
    ic_silence = sum(1 for r in in_corpus if r["silence_triggered"])
    ic_cited = sum(1 for r in in_corpus if r["has_citations"])
    ic_fidelities = [r["persona_fidelity"] for r in in_corpus if r["persona_fidelity"] is not None]
    ic_avg_fidelity = sum(ic_fidelities) / len(ic_fidelities) if ic_fidelities else 0.0
    ic_avg_conf = sum(r["final_confidence"] for r in in_corpus) / len(in_corpus) if in_corpus else 0.0

    # -- Out-of-corpus metrics --
    oc_silence = sum(1 for r in out_corpus if r["silence_triggered"])
    oc_silence_rate = oc_silence / len(out_corpus) if out_corpus else 0.0

    # -- Forbidden pattern check --
    forbid_pass = sum(1 for r in successful if r["forbidden_pattern_check"])
    forbid_fail = sum(1 for r in successful if not r["forbidden_pattern_check"])
    all_violations = []
    for r in successful:
        all_violations.extend(r["forbidden_violations"])

    # -- Latency --
    latencies = [r["latency_ms"] for r in successful]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0

    sep = "=" * 70
    print(f"\n{sep}")
    print("AGGREGATE SUMMARY")
    print(sep)
    print(f"  Total queries:        {total}")
    print(f"  Successful:           {len(successful)}")
    print(f"  Errors:               {len(errors)}")
    print()
    print("  IN-CORPUS ({} queries):".format(len(in_corpus)))
    print(f"    Silence triggered:  {ic_silence}/{len(in_corpus)} (want: 0 — response expected)")
    print(f"    Has citations:      {ic_cited}/{len(in_corpus)} (want: all)")
    print(f"    Avg persona fidelity: {ic_avg_fidelity:.4f}")
    print(f"    Avg confidence:     {ic_avg_conf:.4f}")
    print()
    print("  OUT-OF-CORPUS ({} queries):".format(len(out_corpus)))
    print(f"    Silence triggered:  {oc_silence}/{len(out_corpus)} (want: all — strict silence)")
    print(f"    Silence rate:       {oc_silence_rate:.1%}")
    print()
    print("  TIER TEST ({} queries):".format(len(tier_tests)))
    for r in tier_tests:
        print(f"    [{r['tier']}] silence={r['silence_triggered']} conf={r['final_confidence']:.2f} — {r['query'][:60]}")
    print()
    print("  FORBIDDEN PATTERN CHECK (mirror-only compliance):")
    print(f"    Pass: {forbid_pass}/{len(successful)}   Fail: {forbid_fail}/{len(successful)}")
    if all_violations:
        from collections import Counter
        counts = Counter(all_violations)
        for pat, cnt in counts.most_common():
            print(f"      \"{pat}\" found {cnt} time(s)")
    print()
    print(f"  LATENCY:")
    print(f"    Avg: {avg_latency:.0f} ms   Min: {min_latency} ms   Max: {max_latency} ms")
    print(sep)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Sacred Archive Evaluation Suite — 50 queries")
    print("Loading clone from database...")

    clone_id = _get_clone_id()
    profile = _get_profile()
    print(f"  clone_id: {clone_id}")
    print(f"  profile:  {profile.display_name} (mode={profile.generation_mode.value})")
    print(f"  confidence_threshold: {profile.confidence_threshold}")

    print("Building LangGraph pipeline...")
    graph = build_graph(profile)
    compiled = graph.compile()

    results: list[dict] = []
    print(f"\nRunning {len(QUERIES)} queries...\n")

    for i, q in enumerate(QUERIES):
        label = f"[{i+1:>2}/50]"
        print(f"  {label} {q['category']:<14} ({q['tier']:<9}) {q['query'][:55]}...", end="", flush=True)
        r = _run_single_query(compiled, q, clone_id, i)
        status = "ERR" if r["error"] else ("SILENCE" if r["silence_triggered"] else "OK")
        print(f"  -> {status} ({r['latency_ms']}ms)")
        results.append(r)

    # Display
    _print_table(results)
    _print_summary(results)

    # Save JSON
    output_path = Path(__file__).parent / "eval_results_sacred_archive.json"
    # Prepare serializable copy (strip long responses for readability)
    serializable = []
    for r in results:
        entry = dict(r)
        # Truncate response in JSON to keep file manageable
        if entry["response"] and len(entry["response"]) > 500:
            entry["response_truncated"] = entry["response"][:500] + "..."
            entry["response_full_length"] = len(entry["response"])
        serializable.append(entry)

    with open(output_path, "w") as f:
        json.dump(
            {
                "meta": {
                    "suite": "sacred_archive",
                    "queries": len(QUERIES),
                    "clone_id": clone_id,
                    "confidence_threshold": profile.confidence_threshold,
                    "generation_mode": profile.generation_mode.value,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                },
                "results": serializable,
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
