#!/usr/bin/env python3
"""
OSS Model Experiment Script

Tests an LLM model against 5 prompts that cover our Digital Clone Engine use cases.
Measures response quality and latency for model comparison.

Usage:
    # Test current default model (qwen/qwen3-32b)
    python3 scripts/test_model.py

    # Test a specific model via env var
    LLM_MODEL=llama-3.3-70b-versatile python3 scripts/test_model.py

    # Test with a different provider
    LLM_MODEL=glm-4.7 LLM_BASE_URL=http://localhost:8080/v1 LLM_API_KEY=none python3 scripts/test_model.py
"""

import sys
import time
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm import get_llm, LLM_MODEL, LLM_BASE_URL


# ── Test Prompts ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a digital clone of Parag Khanna, a leading global strategy advisor,
author of books like "The Future Is Asian" and "Connectography". You speak in first person
as Parag Khanna. When citing sources, use [N] markers (e.g., [1], [2]).
If you don't have enough information, say so honestly and suggest related topics."""

TEST_CASES = [
    {
        "name": "1. Factual (retrieval grounding)",
        "prompt": "What is the future of ASEAN according to your work?",
        "check": "Should reference ASEAN, cite sources with [N] markers",
    },
    {
        "name": "2. Synthesis (persona + creativity)",
        "prompt": "How do you see infrastructure reshaping global power dynamics in the next decade?",
        "check": "Should synthesize across multiple themes, sound like Parag Khanna",
    },
    {
        "name": "3. Out-of-corpus (hedging)",
        "prompt": "What is your best recipe for chocolate cake?",
        "check": "Should hedge — admit it's outside expertise, suggest related topics",
    },
    {
        "name": "4. Citation compliance",
        "prompt": "Compare the Belt and Road Initiative with Western infrastructure investment, citing specific sources.",
        "check": "Should include [1], [2] etc. citation markers in the response",
    },
    {
        "name": "5. Concise response",
        "prompt": "In one sentence, what is Connectography about?",
        "check": "Should be concise (1-2 sentences), not a multi-paragraph essay",
    },
]


def run_test(test_case: dict, llm) -> dict:
    """Run a single test and return results."""
    start = time.time()
    try:
        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": test_case["prompt"]},
        ])
        elapsed = time.time() - start
        content = response.content
        # Strip <think> tags if present (some models emit these)
        if "<think>" in content:
            import re
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return {
            "success": True,
            "response": content,
            "latency": elapsed,
            "tokens": len(content.split()),
        }
    except Exception as e:
        return {
            "success": False,
            "response": str(e),
            "latency": time.time() - start,
            "tokens": 0,
        }


def main():
    print(f"\n{'='*70}")
    print(f"  OSS Model Experiment")
    print(f"  Model:    {LLM_MODEL}")
    print(f"  Base URL: {LLM_BASE_URL}")
    print(f"{'='*70}\n")

    llm = get_llm(temperature=0.7, max_tokens=500)
    results = []

    for tc in TEST_CASES:
        print(f"── {tc['name']} ──")
        print(f"   Prompt: {tc['prompt']}")
        print(f"   Check:  {tc['check']}")

        result = run_test(tc, llm)
        results.append(result)

        if result["success"]:
            # Show first 300 chars of response
            preview = result["response"][:300]
            if len(result["response"]) > 300:
                preview += "..."
            print(f"   Response ({result['latency']:.1f}s, ~{result['tokens']} words):")
            for line in preview.split("\n"):
                print(f"     {line}")
        else:
            print(f"   ERROR: {result['response']}")
        print()

    # Summary table
    print(f"\n{'='*70}")
    print(f"  SUMMARY — {LLM_MODEL}")
    print(f"{'='*70}")
    print(f"  {'Test':<35} {'Status':<8} {'Latency':<10} {'Words':<8}")
    print(f"  {'-'*35} {'-'*8} {'-'*10} {'-'*8}")

    total_latency = 0
    successes = 0
    for tc, result in zip(TEST_CASES, results):
        status = "✅" if result["success"] else "❌"
        latency = f"{result['latency']:.1f}s"
        words = str(result["tokens"])
        print(f"  {tc['name']:<35} {status:<8} {latency:<10} {words:<8}")
        total_latency += result["latency"]
        if result["success"]:
            successes += 1

    print(f"\n  Total: {successes}/{len(TEST_CASES)} passed, {total_latency:.1f}s total latency")
    print(f"  Avg latency: {total_latency/len(TEST_CASES):.1f}s per prompt\n")


if __name__ == "__main__":
    main()
