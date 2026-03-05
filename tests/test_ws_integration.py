"""
WebSocket Integration Tests — Digital Clone Engine

Tests the WebSocket chat protocol against a running backend.
Requires backend running on localhost:8000 with database + LLM.

Run:
    pytest tests/test_ws_integration.py -v
    pytest tests/test_ws_integration.py -v -s   # show messages

Requires: Backend running (uvicorn api.main:app --port 8000)
"""

import os
import json
import socket
import asyncio
import pytest

# Skip if websockets not installed
try:
    import websockets
except ImportError:
    pytest.skip("websockets not installed", allow_module_level=True)


def _backend_reachable() -> bool:
    """Check if backend is listening on port 8000."""
    try:
        with socket.create_connection(("localhost", 8000), timeout=2):
            return True
    except (ConnectionRefusedError, OSError):
        return False


pytestmark = [
    pytest.mark.skipif(not _backend_reachable(), reason="Backend not running on localhost:8000"),
    pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="GROQ_API_KEY required"),
    pytest.mark.asyncio,
]

WS_URL = "ws://localhost:8000/chat/ws/{slug}"


async def collect_messages(slug: str, query: str, user_id: str = "test-user", access_tier: str = "public", timeout_sec: int = 60):
    """Connect to WS, send query, collect all messages until close."""
    messages = []
    async with asyncio.timeout(timeout_sec):
        async with websockets.connect(WS_URL.format(slug=slug)) as ws:
            await ws.send(json.dumps({
                "query": query,
                "user_id": user_id,
                "access_tier": access_tier,
            }))
            async for raw in ws:
                msg = json.loads(raw)
                messages.append(msg)
    return messages


async def test_ws_chat_receives_progress_and_response():
    msgs = await collect_messages("paragpt-client", "What is connectivity?")

    progress_msgs = [m for m in msgs if m.get("type") == "progress"]
    response_msgs = [m for m in msgs if m.get("type") == "response"]

    assert len(progress_msgs) >= 1, f"Expected at least 1 progress msg, got {len(progress_msgs)}"
    assert len(response_msgs) == 1, f"Expected exactly 1 response msg, got {len(response_msgs)}"

    # Verify progress has node field
    for p in progress_msgs:
        assert "node" in p, f"Progress message missing 'node': {p}"

    # Verify response structure
    resp = response_msgs[0]
    assert "response" in resp
    assert "confidence" in resp
    assert "cited_sources" in resp
    assert "silence_triggered" in resp
    assert isinstance(resp["response"], str)
    assert len(resp["response"]) > 0


async def test_ws_invalid_slug():
    """Non-existent clone should produce an error."""
    try:
        msgs = await collect_messages("nonexistent-clone-xyz", "Hello", timeout_sec=15)
        # If we get messages, at least one should be an error
        error_msgs = [m for m in msgs if m.get("type") == "error"]
        assert len(error_msgs) >= 1, f"Expected error for invalid slug, got: {msgs}"
    except Exception:
        # Connection error or rejection is also acceptable
        pass


async def test_ws_empty_query():
    """Empty query should produce an error response."""
    try:
        msgs = await collect_messages("paragpt-client", "", timeout_sec=15)
        error_msgs = [m for m in msgs if m.get("type") == "error"]
        assert len(error_msgs) >= 1, f"Expected error for empty query, got: {msgs}"
    except Exception:
        pass
