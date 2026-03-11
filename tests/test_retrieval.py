"""
Tests for retrieval nodes — CRAG evaluator.

Covers: core/langgraph/nodes/retrieval_nodes.py
"""

import pytest


# ===========================================================================
# CRAG evaluator — from test_session16
# ===========================================================================

class TestCRAGEvaluator:

    def test_no_passages_zero_confidence(self):
        """No passages should yield 0.0 confidence."""
        from core.langgraph.nodes.retrieval_nodes import crag_evaluator

        state = {"retrieved_passages": [], "retrieval_confidence": 0.9}
        result = crag_evaluator(state)
        assert result["retrieval_confidence"] == 0.0

    def test_few_passages_penalized(self):
        """1 passage with 0.9 confidence should be penalized to ~0.3."""
        from core.langgraph.nodes.retrieval_nodes import crag_evaluator

        state = {
            "retrieved_passages": [{"passage": "one"}],
            "retrieval_confidence": 0.9,
        }
        result = crag_evaluator(state)
        assert result["retrieval_confidence"] == pytest.approx(0.3, abs=0.01)

    def test_two_passages_penalized(self):
        """2 passages with 0.9 confidence should be penalized to ~0.6."""
        from core.langgraph.nodes.retrieval_nodes import crag_evaluator

        state = {
            "retrieved_passages": [{"passage": "one"}, {"passage": "two"}],
            "retrieval_confidence": 0.9,
        }
        result = crag_evaluator(state)
        assert result["retrieval_confidence"] == pytest.approx(0.6, abs=0.01)

    def test_many_passages_no_penalty(self):
        """3+ passages should not be penalized."""
        from core.langgraph.nodes.retrieval_nodes import crag_evaluator

        passages = [{"passage": f"p{i}"} for i in range(5)]
        state = {"retrieved_passages": passages, "retrieval_confidence": 0.9}
        result = crag_evaluator(state)
        assert result["retrieval_confidence"] == 0.9

    def test_confidence_clamped(self):
        """Confidence should be clamped to [0.0, 1.0]."""
        from core.langgraph.nodes.retrieval_nodes import crag_evaluator

        passages = [{"passage": f"p{i}"} for i in range(5)]
        state = {"retrieved_passages": passages, "retrieval_confidence": 1.5}
        result = crag_evaluator(state)
        assert result["retrieval_confidence"] == 1.0
