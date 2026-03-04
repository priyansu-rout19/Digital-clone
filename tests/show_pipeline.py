"""
Pipeline Visualizer — Digital Clone Engine

Run this script to see EXACTLY what happens at each node of the pipeline.
Shows input state, what changes at each node, and final output.

Usage:
    python3 tests/show_pipeline.py              # Mocked mode (default, no DB needed)
    python3 tests/show_pipeline.py --real        # Real mode (live DB + APIs)
    python3 tests/show_pipeline.py --real --clone sacred-archive --query "What is dharma?"

Output:
    - Console: node-by-node changes
    - Log file: logs/pipeline_run_YYYYMMDD_HHMMSS.log
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import 'core'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.models.clone_profile import paragpt_profile
from core.langgraph.conversation_flow import build_graph


# -- Set up logging -----------------------------------------------------------

os.makedirs("logs", exist_ok=True)
log_file = f"logs/pipeline_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# -- Sample data (same as test_e2e.py) ----------------------------------------

SAMPLE_PASSAGES = [
    {
        "doc_id": "doc-001",
        "chunk_id": "doc-001_0000",
        "passage": (
            "Connectivity is the defining mega-trend of the 21st century. "
            "Nations that control infrastructure — digital, physical, and financial — "
            "will shape global order for decades to come."
        ),
        "source_type": "book",
        "access_tier": "public",
        "date": "2016",
    },
    {
        "doc_id": "doc-002",
        "chunk_id": "doc-002_0001",
        "passage": (
            "The future belongs to agile civilizations that embrace networks over territories. "
            "Supply chain sovereignty and data sovereignty are now geopolitical imperatives."
        ),
        "source_type": "lecture",
        "access_tier": "public",
        "date": "2023",
    },
]

BASE_STATE = {
    "query_text": "What is the future of global connectivity?",
    "sub_queries": [],
    "intent_class": "",
    "access_tier": "public",
    "token_budget": 2000,
    "clone_id": "test-clone-uuid-001",
    "user_id": "test-user-uuid-001",
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
    "audio_base64": "",
    "audio_format": "",
}


# -- Utility functions ---------------------------------------------------------

def truncate(val, max_len=200):
    """Truncate long strings for readable logs."""
    s = str(val)
    if isinstance(val, list) and len(val) > 0:
        s = f"[{len(val)} items] {val[:100]}"
    elif isinstance(val, dict):
        s = f"{{...{len(val)} keys}}"
    else:
        s = str(val)
    return s[: max_len] + "..." if len(s) > max_len else s


def diff_states(before, after):
    """Return only keys that changed between two state dicts."""
    changed = {}
    all_keys = set(before.keys()) | set(after.keys())
    for k in all_keys:
        bv = before.get(k)
        av = after.get(k)
        if bv != av:
            changed[k] = {"before": bv, "after": av}
    return changed


def format_state_value(val):
    """Format state value for display."""
    if isinstance(val, str):
        if len(val) > 300:
            return f'"{val[:300]}..."'
        return f'"{val}"'
    elif isinstance(val, (list, dict)):
        s = str(val)
        if len(s) > 300:
            return f"{type(val).__name__} ({len(val)} items) ..."
        return s
    return str(val)


def _visualize_stream(graph, initial_state):
    """Shared visualization logic — streams graph and logs node-by-node changes.

    Returns the final merged state dict after all nodes have executed.
    """
    current_state = dict(initial_state)
    node_count = 0

    for chunk in graph.stream(dict(initial_state)):
        node_name = list(chunk.keys())[0]
        state_delta = list(chunk.values())[0]

        # Merge delta into current state
        new_state = {**current_state, **state_delta}

        # Find what changed
        changes = diff_states(current_state, new_state)

        node_count += 1
        log.info(f"NODE {node_count}: {node_name.upper()}")

        if changes:
            for key in sorted(changes.keys()):
                before = changes[key]["before"]
                after = changes[key]["after"]
                log.info(f"  {key}:")
                log.info(f"    <- {format_state_value(before)}")
                log.info(f"    -> {format_state_value(after)}")
        else:
            log.info("  (no changes — passthrough node)")

        log.info("")
        current_state = new_state

    return current_state


def _log_final_summary(current_state):
    """Shared final summary logging — used by both mocked and real modes."""
    log.info("=" * 80)
    log.info("FINAL STATE SUMMARY")
    log.info("=" * 80)
    log.info(f"  intent_class        : {current_state.get('intent_class')}")
    log.info(f"  retrieval_confidence: {current_state.get('retrieval_confidence'):.2f}")
    log.info(f"  retry_count         : {current_state.get('retry_count')}")
    log.info(f"  final_confidence    : {current_state.get('final_confidence'):.2f}")
    log.info(f"  cited_sources count : {len(current_state.get('cited_sources', []))}")
    log.info(f"  silence_triggered   : {current_state.get('silence_triggered')}")
    log.info(f"  voice_chunks count  : {len(current_state.get('voice_chunks', []))}")

    # Show the generated response
    response = current_state.get("verified_response", "")
    log.info(f"\n[GENERATED RESPONSE]")
    if response:
        log.info(response)
    else:
        log.info("  (empty response)")

    # Citations
    citations = current_state.get("cited_sources", [])
    log.info(f"\n[CITATIONS] {len(citations)} sources cited")
    for i, citation in enumerate(citations, 1):
        log.info(f"  [{i}] {citation.get('doc_id')} — {citation.get('source_type')}")

    log.info("\n" + "=" * 80)
    log.info(f"Pipeline complete. Log saved to: {log_file}")
    log.info("=" * 80)


# -- Main pipeline runner ------------------------------------------------------

def run_pipeline(args):
    """Run the full pipeline and log all node transitions."""

    log.info("=" * 80)
    log.info("DIGITAL CLONE ENGINE — PIPELINE VISUALIZER")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info(f"  Mode: {'REAL (live database + APIs)' if args.real else 'MOCKED (canned data)'}")
    log.info("=" * 80)

    if args.real:
        _run_real(args)
    else:
        _run_mocked(args)


def _run_mocked(args):
    """Mocked mode — uses canned SAMPLE_PASSAGES, no DB or live APIs needed."""

    # Log initial input
    log.info("\n[INITIAL INPUT STATE]")
    log.info(f"  query_text  : {BASE_STATE['query_text']}")
    log.info(f"  clone_id    : {BASE_STATE['clone_id']}")
    log.info(f"  user_id     : {BASE_STATE['user_id']}")
    log.info(f"  access_tier : {BASE_STATE['access_tier']}")
    log.info(f"  (All other fields empty/zero — pipeline fills them in)")

    # Log profile settings
    profile = paragpt_profile()
    log.info(f"\n[PROFILE CONFIG]")
    log.info(f"  Clone name          : {profile.display_name}")
    log.info(f"  Generation mode     : {profile.generation_mode}")
    log.info(f"  Confidence threshold: {profile.confidence_threshold}")
    log.info(f"  Memory enabled      : {profile.user_memory_enabled}")
    log.info(f"  Review required     : {profile.review_required}")
    log.info(f"  Silence behavior    : {profile.silence_behavior}")

    log.info(f"\n[SAMPLE PASSAGES (what the retriever will return)]")
    for i, p in enumerate(SAMPLE_PASSAGES, 1):
        log.info(f"  [{i}] {p['source_type']} — {p['doc_id']}")
        log.info(f"      {p['passage'][:100]}...")

    log.info(f"\n[MOCK SETUP]")
    log.info(f"  vector_search.search will return: 2 passages + confidence 0.85")
    log.info(f"  (0.85 is above ParaGPT threshold of 0.80 → no CRAG retry)")
    log.info(f"  get_mem0_client will return: empty results")

    # Build and run the graph
    log.info(f"\n[PIPELINE EXECUTION — 17 nodes, node-by-node transitions]")
    log.info("")

    profile = paragpt_profile()
    graph = build_graph(profile)

    with patch("core.rag.retrieval.vector_search.search") as mock_search, \
         patch("core.mem0_client.get_mem0_client") as mock_mem:

        # Setup mocks
        mock_search.return_value = (SAMPLE_PASSAGES, 0.85)

        mem_client = MagicMock()
        mem_client.search.return_value = {"results": []}
        mem_client.add.return_value = None
        mock_mem.return_value = mem_client

        # Run the pipeline with stream()
        current_state = _visualize_stream(graph, BASE_STATE)

    # Final summary
    _log_final_summary(current_state)


def _run_real(args):
    """Real mode — uses live database, real vector search, real Mem0, real LLM."""

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.db.schema import Clone
    from core.models.clone_profile import CloneProfile

    # Load clone from the database
    db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres@localhost/dce_dev")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    clone = db.query(Clone).filter(Clone.slug == args.clone).first()
    if not clone:
        log.error(f"Clone '{args.clone}' not found. Run: python scripts/seed_db.py")
        db.close()
        engine.dispose()
        return
    clone_id = str(clone.id)
    profile = CloneProfile(**clone.profile)
    db.close()
    engine.dispose()

    # Log real mode info
    log.info(f"\n[REAL MODE]")
    log.info(f"  Clone: {args.clone} (ID: {clone_id[:8]}...)")
    log.info(f"  Query: {args.query}")
    log.info(f"  Database: {db_url}")
    log.info(f"  Vector search: REAL (pgvector)")
    log.info(f"  Memory: REAL (Mem0 pgvector)")
    log.info(f"  LLM: REAL (Groq API)")

    # Log profile settings
    log.info(f"\n[PROFILE CONFIG]")
    log.info(f"  Clone name          : {profile.display_name}")
    log.info(f"  Generation mode     : {profile.generation_mode}")
    log.info(f"  Confidence threshold: {profile.confidence_threshold}")
    log.info(f"  Memory enabled      : {profile.user_memory_enabled}")
    log.info(f"  Review required     : {profile.review_required}")
    log.info(f"  Silence behavior    : {profile.silence_behavior}")

    # Build initial state
    access_tier = "devotee" if args.clone == "sacred-archive" else "public"
    initial_state = {
        "query_text": args.query,
        "sub_queries": [],
        "intent_class": "",
        "access_tier": access_tier,
        "token_budget": 2000,
        "clone_id": clone_id,
        "user_id": "visualizer-user-001",
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
        "audio_base64": "",
        "audio_format": "",
    }

    log.info(f"\n[INITIAL INPUT STATE]")
    log.info(f"  query_text  : {initial_state['query_text']}")
    log.info(f"  clone_id    : {clone_id[:8]}...")
    log.info(f"  user_id     : {initial_state['user_id']}")
    log.info(f"  access_tier : {initial_state['access_tier']}")

    # Build and run the graph — no mocks, everything is live
    log.info(f"\n[PIPELINE EXECUTION — REAL MODE, node-by-node transitions]")
    log.info("")

    graph = build_graph(profile)
    current_state = _visualize_stream(graph, initial_state)

    # Final summary
    _log_final_summary(current_state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Digital Clone Engine — Pipeline Visualizer")
    parser.add_argument("--real", action="store_true",
                        help="Use real database and APIs instead of mocked data")
    parser.add_argument("--clone", choices=["paragpt-client", "sacred-archive"],
                        default="paragpt-client", help="Clone to visualize (default: paragpt-client)")
    parser.add_argument("--query", type=str,
                        default="What is the future of global connectivity?",
                        help="Query to run through the pipeline")
    args = parser.parse_args()
    run_pipeline(args)
