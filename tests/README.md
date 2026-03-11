# Tests — Digital Clone Engine

## Quick Reference

| File | Tests | What it covers |
|---|---|---|
| `test_api.py` | 34 | FastAPI endpoints (all routes) |
| `test_query_analysis.py` | 46 | Pre-filter, intent classification, token budgets, routing |
| `test_clone_profile.py` | 19 | Profile loading, markdown hydration, factory functions |
| `test_routing.py` | 14 | Review queue, voice pipeline, sentence splitting, confidence bypass |
| `test_chunker.py` | 10 | Document chunking |
| `test_generation.py` | 9 | Confidence scoring, context bleed, Mem0 injection, guardrails |
| `test_prompts.py` | 9 | Adaptive prompt templates, guardrails in prompts |
| `test_retrieval.py` | 5 | CRAG evaluator (passage count penalties, clamping) |
| `test_parser.py` | 5 | Audio parsing (Whisper), PDF fallback |
| `test_e2e.py` | 4 | Full pipeline end-to-end (mocked LLM + retrieval) |
| `test_mem0.py` | 3 | Mem0 provider selection (OpenRouter / Groq / missing keys) |
| `test_ws_integration.py` | 3 | WebSocket chat flow |
| **Total** | **161** | |

## Running

```bash
# All tests
python3 -m pytest tests/ -v

# Single file
python3 -m pytest tests/test_query_analysis.py -v

# Single class
python3 -m pytest tests/test_routing.py::TestVoicePipeline -v

# Collect only (no execution)
python3 -m pytest tests/ --collect-only -q
```

## Eval & Debug Scripts (in `scripts/`)

| Script | Purpose |
|---|---|
| `scripts/eval_suite_paragpt.py` | 50-query ParaGPT evaluation (needs live DB) |
| `scripts/eval_suite_sacred_archive.py` | 50-query Sacred Archive evaluation (needs live DB) |
| `scripts/show_pipeline.py` | Node-by-node pipeline visualizer (mocked or real) |
| `scripts/foundation_gate.py` | 30-query pass/fail gate (>90% citation, >80% persona) |
| `scripts/corpus_gap_report.py` | Clusters silenced queries to find corpus gaps |
