#!/usr/bin/env python3
"""
Corpus Gap Report — Digital Clone Engine

Queries the query_analytics table for silence-triggered queries, extracts
keywords, and clusters them by frequency to identify uncovered topic gaps.

Output:
  - Terminal: formatted top-20 uncovered topics per clone + overall
  - JSON: scripts/corpus_gap_results.json
"""

import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

# Project root on sys.path so imports resolve
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import psycopg
from core.db import psycopg_url


# ---------------------------------------------------------------------------
# English stopwords (compact set — no NLTK dependency)
# ---------------------------------------------------------------------------
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "can", "could", "did",
    "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "get", "got", "had", "has", "have", "having", "he", "her",
    "here", "hers", "herself", "him", "himself", "his", "how", "i", "if",
    "in", "into", "is", "it", "its", "itself", "just", "let", "like", "ll",
    "me", "might", "more", "most", "must", "my", "myself", "no", "nor",
    "not", "now", "of", "off", "on", "once", "only", "or", "other", "our",
    "ours", "ourselves", "out", "over", "own", "re", "s", "same", "she",
    "should", "so", "some", "such", "t", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "ve", "very",
    "was", "we", "were", "what", "when", "where", "which", "while", "who",
    "whom", "why", "will", "with", "would", "you", "your", "yours",
    "yourself", "yourselves", "don", "doesn", "didn", "hasn", "haven",
    "isn", "wasn", "weren", "won", "wouldn", "shouldn", "couldn", "aren",
    # Additional common words unlikely to be topic-bearing
    "also", "tell", "please", "know", "think", "say", "said", "make",
    "go", "going", "much", "many", "well", "really", "way", "even",
    "want", "give", "good", "new", "use", "work", "take", "come",
    "question", "explain", "describe", "discuss", "help", "need",
}

# Minimum word length to consider as a keyword
MIN_WORD_LEN = 3


def extract_keywords(text: str) -> list[str]:
    """
    Extract topic-bearing keywords from a query string.

    Simple approach: lowercase, split on non-alpha, remove stopwords and
    short tokens. No external NLP dependencies needed.
    """
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if len(w) >= MIN_WORD_LEN and w not in STOPWORDS]


def fetch_silence_rows() -> list[dict]:
    """Fetch all silence-triggered rows from query_analytics."""
    db_url = psycopg_url()
    if not db_url:
        print("ERROR: DATABASE_URL not set or psycopg_url() returned empty.")
        sys.exit(1)

    rows = []
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    qa.clone_id,
                    c.slug,
                    qa.query_text,
                    qa.confidence_score,
                    qa.created_at
                FROM query_analytics qa
                LEFT JOIN clones c ON c.id = qa.clone_id
                WHERE qa.silence_triggered = true
                ORDER BY qa.created_at DESC
            """)
            for row in cur.fetchall():
                rows.append({
                    "clone_id": str(row[0]) if row[0] else "unknown",
                    "clone_slug": row[1] or "unknown",
                    "query_text": row[2] or "",
                    "confidence_score": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                })
    return rows


def build_report(rows: list[dict]) -> dict:
    """Analyze silence rows and build keyword frequency report."""

    # Global keyword counter
    global_keywords = Counter()
    # Per-clone keyword counter
    clone_keywords: dict[str, Counter] = defaultdict(Counter)
    # Per-clone query list
    clone_queries: dict[str, list[str]] = defaultdict(list)

    for row in rows:
        slug = row["clone_slug"]
        query = row["query_text"]
        keywords = extract_keywords(query)

        global_keywords.update(keywords)
        clone_keywords[slug].update(keywords)
        clone_queries[slug].append(query)

    # Top-20 overall
    top_global = global_keywords.most_common(20)

    # Top-20 per clone
    top_per_clone = {}
    for slug, counter in sorted(clone_keywords.items()):
        top_per_clone[slug] = counter.most_common(20)

    return {
        "total_silence_queries": len(rows),
        "clones": list(clone_keywords.keys()),
        "top_20_global": [{"keyword": kw, "count": cnt} for kw, cnt in top_global],
        "per_clone": {
            slug: {
                "query_count": len(clone_queries[slug]),
                "top_20_keywords": [{"keyword": kw, "count": cnt} for kw, cnt in topics],
                "sample_queries": clone_queries[slug][:10],  # first 10 as examples
            }
            for slug, topics in top_per_clone.items()
        },
    }


def print_report(report: dict):
    """Print formatted report to terminal."""
    print("=" * 70)
    print("  CORPUS GAP REPORT — Digital Clone Engine")
    print("=" * 70)
    print()
    print(f"  Total silence-triggered queries: {report['total_silence_queries']}")
    print(f"  Clones with gaps: {', '.join(report['clones']) or 'none'}")
    print()

    if not report["top_20_global"]:
        print("  No silence-triggered queries found. Corpus coverage looks good!")
        print("=" * 70)
        return

    # Global top-20
    print("  TOP-20 UNCOVERED TOPICS (all clones)")
    print("  " + "-" * 40)
    for i, item in enumerate(report["top_20_global"], 1):
        bar = "#" * min(item["count"], 40)
        print(f"  {i:>2}. {item['keyword']:<25} {item['count']:>4}  {bar}")
    print()

    # Per-clone breakdown
    for slug, data in report["per_clone"].items():
        print(f"  --- {slug.upper()} ({data['query_count']} silence queries) ---")
        for i, item in enumerate(data["top_20_keywords"][:10], 1):
            bar = "#" * min(item["count"], 30)
            print(f"    {i:>2}. {item['keyword']:<25} {item['count']:>4}  {bar}")

        if data["sample_queries"]:
            print()
            print(f"    Sample queries:")
            for q in data["sample_queries"][:5]:
                print(f"      - {q[:80]}")
        print()

    print("=" * 70)


def main():
    print("Fetching silence-triggered queries from query_analytics...")
    rows = fetch_silence_rows()
    print(f"  Found {len(rows)} rows.\n")

    report = build_report(rows)

    # Print to terminal
    print_report(report)

    # Save JSON
    report["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    output_path = Path(__file__).parent / "corpus_gap_results.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Report saved to: {output_path}")


if __name__ == "__main__":
    main()
