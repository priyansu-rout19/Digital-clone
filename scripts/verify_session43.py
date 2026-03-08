#!/usr/bin/env python3
"""
Session 43 Live Verification — Diverse Queries + Mem0

Runs 15+ queries through the full LangGraph pipeline (real LLM, real DB, real Mem0)
to verify Session 43 fixes work in practice:

  Part 1: Diverse query tests (greetings, self-ref, domain, hybrid, opinion)
  Part 2: Mem0 memory persistence across turns
  Part 3: Multi-turn context bleed check

Exit code 0 = all pass, 1 = any fail.

Usage:
    python3 scripts/verify_session43.py
    python3 scripts/verify_session43.py --verbose
    python3 scripts/verify_session43.py --skip-mem0 --skip-bleed
    python3 scripts/verify_session43.py --clone sacred-archive
"""

import argparse
import copy
import re
import sys
import time
from pathlib import Path

# Project root on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import psycopg
from core.db import psycopg_url
from core.models.clone_profile import CloneProfile
from core.langgraph.conversation_flow import build_graph


# ==========================================================================
# Test queries — 5 categories
# ==========================================================================

DIVERSE_QUERIES = [
    # Category A: Greetings (expect conversational, no citations, budget=0)
    {"cat": "A-Greeting", "query": "hii i am Priyansu from india",
     "expect_conversational": True},
    {"cat": "A-Greeting", "query": "good morning",
     "expect_conversational": True},
    {"cat": "A-Greeting", "query": "thanks",
     "expect_conversational": True},
    {"cat": "A-Greeting", "query": "hello",
     "expect_conversational": True},

    # Category B: Self-referential (expect conversational — deterministic gate)
    {"cat": "B-SelfRef", "query": "What is my name?",
     "expect_conversational": True},
    {"cat": "B-SelfRef", "query": "Where am I from?",
     "expect_conversational": True},
    {"cat": "B-SelfRef", "query": "Do you remember me?",
     "expect_conversational": True},

    # Category C: Domain (expect factual/synthesis, citations, confidence > 0)
    {"cat": "C-Domain", "query": "How does infrastructure shape global power?",
     "expect_conversational": False, "expect_citations": True},
    {"cat": "C-Domain", "query": "What role does urbanization play in climate adaptation?",
     "expect_conversational": False, "expect_citations": True},

    # Category D: Hybrid (NOT conversational — has knowledge words after greeting)
    {"cat": "D-Hybrid", "query": "Hey, love your work. What's your take on supply chains?",
     "expect_conversational": False},
    {"cat": "D-Hybrid", "query": "I'm from Vietnam, how do you see its future?",
     "expect_conversational": False},

    # Category E: Opinion (factual/synthesis/opinion, budget > 0)
    {"cat": "E-Opinion", "query": "What do you think about India's infrastructure boom?",
     "expect_conversational": False},
    {"cat": "E-Opinion", "query": "Compare ASEAN and EU integration models",
     "expect_conversational": False},
]


# ==========================================================================
# Helpers
# ==========================================================================

def load_clone_from_db(slug: str) -> tuple[str, CloneProfile]:
    """Load clone from DB, return (clone_id, CloneProfile)."""
    db_url = psycopg_url()
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, profile FROM clones WHERE slug = %s", (slug,)
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(
                    f"Clone '{slug}' not found in database. "
                    f"Run: python3 scripts/seed_db.py"
                )
            return str(row[0]), CloneProfile(**row[1])


def build_initial_state(query: str, clone_id: str, user_id: str = "verify-s43") -> dict:
    """Build ConversationState matching chat.py's build_initial_state (28 keys)."""
    return {
        "query_text": query,
        "clone_id": clone_id,
        "user_id": user_id,
        "sub_queries": [],
        "intent_class": "",
        "access_tier": "public",
        "token_budget": 2000,
        "response_tokens": 500,
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


def save_message(clone_id: str, user_id: str, query: str, response: str,
                 confidence: float, cited_sources: list):
    """Insert a message row (enables conversation_history for next turn)."""
    import json as _json
    import uuid as _uuid
    db_url = psycopg_url()
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (id, clone_id, user_id, query_text, response_text,
                                      confidence, silence_triggered, cited_sources)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (str(_uuid.uuid4()), clone_id, user_id, query, response,
                 confidence, False, _json.dumps(cited_sources)),
            )
            conn.commit()


def cleanup_messages(clone_id: str, user_id: str):
    """Delete test user's messages."""
    db_url = psycopg_url()
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM messages WHERE clone_id = %s AND user_id = %s",
                (clone_id, user_id),
            )
            conn.commit()


def cleanup_mem0(user_id: str):
    """Best-effort Mem0 memory deletion for test user."""
    try:
        from core.mem0_client import get_mem0_client
        mem = get_mem0_client()
        mem.delete_all(user_id=user_id)
    except Exception:
        pass  # Best-effort — don't fail the script


def has_citation_markers(text: str) -> bool:
    """Check if response contains [N] citation markers."""
    return bool(re.search(r"\[\d+\]", text))


def get_response(result: dict) -> str:
    """Extract best available response text from pipeline result."""
    return (
        result.get("verified_response")
        or result.get("raw_response")
        or "(no response)"
    )


# ==========================================================================
# Result tracking
# ==========================================================================

class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warned = 0
        self.checks = []

    def check(self, label: str, passed: bool, warn_only: bool = False):
        """Record a check result. Returns passed for chaining."""
        if passed:
            self.passed += 1
            self.checks.append(("PASS", label))
        elif warn_only:
            self.warned += 1
            self.checks.append(("WARN", label))
        else:
            self.failed += 1
            self.checks.append(("FAIL", label))
        return passed

    @property
    def total(self):
        return self.passed + self.failed + self.warned


# ==========================================================================
# Part 1: Diverse Query Tests
# ==========================================================================

def run_part1(graph, clone_id: str, verbose: bool) -> Results:
    results = Results()

    print("\n[Part 1] Diverse Query Tests")
    print("-" * 40)

    for q in DIVERSE_QUERIES:
        cat = q["cat"]
        query = q["query"]
        expect_conv = q["expect_conversational"]
        expect_citations = q.get("expect_citations", False)

        label = f'{cat:12s} "{query[:50]}"'
        print(f"  {label}")

        t0 = time.time()
        try:
            state = build_initial_state(query, clone_id)
            result = graph.invoke(copy.deepcopy(state))
            elapsed = time.time() - t0
        except Exception as e:
            elapsed = time.time() - t0
            print(f"    ✗ ERROR: {e} ({elapsed:.1f}s)")
            results.check(f"{cat} error", False)
            continue

        intent = result.get("intent_class", "")
        budget = result.get("token_budget", -1)
        cited = result.get("cited_sources", [])
        confidence = result.get("retrieval_confidence", 0.0)
        response = get_response(result)

        checks_line = []

        if expect_conv:
            # Categories A, B: conversational, no citations, budget=0, no [N] markers
            ok_intent = results.check(
                f"{cat} intent=conversational",
                intent == "conversational",
            )
            checks_line.append(
                f"{'✓' if ok_intent else '✗'} intent={intent}"
            )

            ok_cites = results.check(
                f"{cat} no_citations",
                len(cited) == 0,
            )
            checks_line.append(
                f"{'✓' if ok_cites else '✗'} no_citations"
            )

            ok_budget = results.check(
                f"{cat} budget=0",
                budget == 0,
            )
            checks_line.append(
                f"{'✓' if ok_budget else '✗'} budget={budget}"
            )

            ok_markers = results.check(
                f"{cat} no_markers",
                not has_citation_markers(response),
            )
            checks_line.append(
                f"{'✓' if ok_markers else '✗'} no_markers"
            )

        elif expect_citations:
            # Category C: not conversational, has citations (WARN if empty — corpus gap)
            ok_intent = results.check(
                f"{cat} intent!=conversational",
                intent != "conversational",
            )
            checks_line.append(
                f"{'✓' if ok_intent else '✗'} intent={intent}"
            )

            ok_conf = results.check(
                f"{cat} confidence>0",
                confidence > 0,
                warn_only=True,  # Corpus gap = WARN, not FAIL
            )
            checks_line.append(
                f"{'✓' if ok_conf else '⚠'} conf={confidence:.2f}"
            )

            ok_cites = results.check(
                f"{cat} has_citations",
                len(cited) > 0,
                warn_only=True,  # Corpus gap = WARN
            )
            checks_line.append(
                f"{'✓' if ok_cites else '⚠'} citations={len(cited)}"
            )

        else:
            # Categories D, E: NOT conversational, budget > 0
            ok_intent = results.check(
                f"{cat} intent!=conversational",
                intent != "conversational",
            )
            checks_line.append(
                f"{'✓' if ok_intent else '✗'} intent={intent}"
            )

            ok_budget = results.check(
                f"{cat} budget>0",
                budget > 0,
            )
            checks_line.append(
                f"{'✓' if ok_budget else '✗'} budget={budget}"
            )

        print(f"    {' '.join(checks_line)}  ({elapsed:.1f}s)")

        if verbose:
            print(f"    Response: {response[:120]}...")
            print()

    return results


# ==========================================================================
# Part 2: Mem0 Memory Verification
# ==========================================================================

def run_part2(graph, clone_id: str, verbose: bool) -> Results:
    results = Results()

    ts = int(time.time())
    user_id = f"verify-s43-mem0-{ts}"

    print("\n[Part 2] Mem0 Memory")
    print("-" * 40)

    try:
        # Turn 1: introduce yourself
        turn1_query = "Hi, I'm Priyansu from India and I work in AI"
        print(f'  Turn 1: "{turn1_query}"')

        state1 = build_initial_state(turn1_query, clone_id, user_id)
        t0 = time.time()
        result1 = graph.invoke(copy.deepcopy(state1))
        e1 = time.time() - t0

        intent1 = result1.get("intent_class", "")
        response1 = get_response(result1)

        ok = results.check("mem0 turn1 conversational", intent1 == "conversational")
        print(f"    {'✓' if ok else '✗'} intent={intent1} ({e1:.1f}s)")

        # Save turn 1 to messages (enables conversation_history for turn 2)
        save_message(clone_id, user_id, turn1_query, response1,
                     result1.get("final_confidence", 0.0),
                     result1.get("cited_sources", []))
        print("    ✓ saved to messages")

        if verbose:
            print(f"    Response: {response1[:120]}...")

        # Wait for Mem0 pgvector commit
        print("  Waiting 3s for Mem0 commit...")
        time.sleep(3)

        # Turn 2: ask what the clone remembers
        turn2_query = "What do you remember about me?"
        print(f'  Turn 2: "{turn2_query}"')

        state2 = build_initial_state(turn2_query, clone_id, user_id)
        t0 = time.time()
        result2 = graph.invoke(copy.deepcopy(state2))
        e2 = time.time() - t0

        user_memory = result2.get("user_memory", "")
        response2 = get_response(result2)

        # Check: user_memory field should be non-empty (Mem0 recalled facts)
        ok_mem = results.check("mem0 memory_loaded", bool(user_memory))
        print(f"    {'✓' if ok_mem else '✗'} memory_loaded={'yes' if user_memory else 'NO'} ({e2:.1f}s)")

        # Check: response mentions at least one of the user's facts
        mentions = [kw for kw in ["Priyansu", "India", "AI"]
                    if kw.lower() in response2.lower()]
        ok_mention = results.check(
            "mem0 mentions_user",
            len(mentions) > 0,
            warn_only=True,  # LLM phrasing varies
        )
        print(f"    {'✓' if ok_mention else '⚠'} mentions: {mentions or 'none'}")

        if verbose:
            print(f"    Memory: {user_memory[:200]}")
            print(f"    Response: {response2[:120]}...")

    except Exception as e:
        print(f"    ✗ ERROR: {e}")
        results.check("mem0 error", False)

    finally:
        # Cleanup
        cleanup_messages(clone_id, user_id)
        cleanup_mem0(user_id)
        print("  Cleanup done")

    return results


# ==========================================================================
# Part 3: Multi-turn Context Bleed Check
# ==========================================================================

def run_part3(graph, clone_id: str, verbose: bool) -> Results:
    results = Results()

    ts = int(time.time())
    user_id = f"verify-s43-bleed-{ts}"

    print("\n[Part 3] Context Bleed")
    print("-" * 40)

    try:
        # Turn 1: personal greeting
        turn1_query = "hii i am Priyansu from india"
        print(f'  Turn 1: "{turn1_query}"')

        state1 = build_initial_state(turn1_query, clone_id, user_id)
        t0 = time.time()
        result1 = graph.invoke(copy.deepcopy(state1))
        e1 = time.time() - t0

        response1 = get_response(result1)
        save_message(clone_id, user_id, turn1_query, response1,
                     result1.get("final_confidence", 0.0),
                     result1.get("cited_sources", []))
        print(f"    ✓ greeting saved ({e1:.1f}s)")

        # Turn 2: domain question — should NOT leak personal info
        turn2_query = "How does infrastructure shape global power?"
        print(f'  Turn 2: "{turn2_query}"')

        state2 = build_initial_state(turn2_query, clone_id, user_id)
        t0 = time.time()
        result2 = graph.invoke(copy.deepcopy(state2))
        e2 = time.time() - t0

        response2 = get_response(result2)

        # Check: response should NOT contain location-tracking language
        bleed_phrases = ["gps location", "real-time", "your location",
                         "track your", "locate you"]
        found_bleed = [p for p in bleed_phrases if p in response2.lower()]
        ok_bleed = results.check("bleed no_location_leak", len(found_bleed) == 0)
        print(f"    {'✓' if ok_bleed else '✗'} no_bleed ({e2:.1f}s)")

        if found_bleed:
            print(f"    ✗ Found context bleed phrases: {found_bleed}")

        # Check: response should be about infrastructure/power
        domain_words = ["infrastructure", "power", "connectivity", "geopolit",
                        "trade", "economic", "nation", "global", "corridor"]
        mentions = [w for w in domain_words if w in response2.lower()]
        ok_topic = results.check(
            "bleed on_topic",
            len(mentions) > 0,
            warn_only=True,  # LLM phrasing varies
        )
        print(f"    {'✓' if ok_topic else '⚠'} domain_words: {mentions[:5]}")

        if verbose:
            print(f"    Response: {response2[:200]}...")

    except Exception as e:
        print(f"    ✗ ERROR: {e}")
        results.check("bleed error", False)

    finally:
        cleanup_messages(clone_id, user_id)
        print("  Cleanup done")

    return results


# ==========================================================================
# Main
# ==========================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Session 43 Live Verification")
    parser.add_argument("--clone", default="paragpt-client",
                        help="Clone slug (default: paragpt-client)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show full response text")
    parser.add_argument("--skip-mem0", action="store_true",
                        help="Skip Part 2 (Mem0 memory test)")
    parser.add_argument("--skip-bleed", action="store_true",
                        help="Skip Part 3 (context bleed test)")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 64)
    print("  SESSION 43 LIVE VERIFICATION")
    print("=" * 64)

    # Load clone from DB
    try:
        clone_id, profile = load_clone_from_db(args.clone)
        print(f"  Clone: {profile.display_name} ({args.clone})")
        print(f"  Clone ID: {clone_id}")
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    # Build graph once — reuse for all queries
    graph = build_graph(profile)
    print(f"  Graph built: {profile.generation_mode} mode")

    # --- Part 1: Diverse queries ---
    r1 = run_part1(graph, clone_id, args.verbose)

    # --- Part 2: Mem0 memory ---
    if args.skip_mem0:
        print("\n[Part 2] Mem0 Memory — SKIPPED")
        r2 = Results()
    else:
        try:
            r2 = run_part2(graph, clone_id, args.verbose)
        except Exception as e:
            print(f"\n[Part 2] Mem0 Memory — SKIPPED (error: {e})")
            r2 = Results()

    # --- Part 3: Context bleed ---
    if args.skip_bleed:
        print("\n[Part 3] Context Bleed — SKIPPED")
        r3 = Results()
    else:
        r3 = run_part3(graph, clone_id, args.verbose)

    # --- Summary ---
    total_pass = r1.passed + r2.passed + r3.passed
    total_fail = r1.failed + r2.failed + r3.failed
    total_warn = r1.warned + r2.warned + r3.warned
    total = r1.total + r2.total + r3.total

    print()
    print("=" * 64)
    status = "ALL PASS" if total_fail == 0 else "FAIL"
    warn_str = f", {total_warn} WARN" if total_warn else ""
    print(f"  RESULTS: {total_pass}/{total} PASS, {total_fail} FAIL{warn_str}")
    print("=" * 64)

    if total_fail > 0:
        print("\nFailed checks:")
        for r in [r1, r2, r3]:
            for status_str, label in r.checks:
                if status_str == "FAIL":
                    print(f"  ✗ {label}")

    return 1 if total_fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
