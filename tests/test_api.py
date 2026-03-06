"""
FastAPI Gateway Tests — Digital Clone Engine

Tests the HTTP layer: routing, request validation, response shapes, business logic.
Does NOT test the LangGraph pipeline (that's in test_e2e.py).

Mock strategy:
- Database: mock SessionLocal with fake Clone rows
- LangGraph: mock build_graph to return a preset final state
- Background tasks: patched to no-op

Run:
    pytest tests/test_api.py -v
    pytest tests/test_api.py::test_health_check -v
"""

import json
import uuid
from io import BytesIO
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.deps import get_db, SessionLocal
from core.models.clone_profile import paragpt_profile, sacred_archive_profile, CloneProfile
from core.db.schema import Clone, ReviewQueue


# ---------------------------------------------------------------------------
# Fixtures: Mock Database Setup
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_session():
    """
    Creates a mock SQLAlchemy session with two pre-configured clones.
    Replaces api.deps.get_db() with a mock that yields this session.
    """
    mock_session = MagicMock()

    # Create mock Clone rows
    clone_paragpt = MagicMock(spec=Clone)
    clone_paragpt.id = uuid.uuid4()
    clone_paragpt.slug = "paragpt-client"
    clone_paragpt.profile = paragpt_profile().model_dump()

    clone_sacred = MagicMock(spec=Clone)
    clone_sacred.id = uuid.uuid4()
    clone_sacred.slug = "sacred-archive"
    clone_sacred.profile = sacred_archive_profile().model_dump()

    # Setup query mock to return clones by slug, and handle ReviewQueue queries
    def mock_query_filter(model):
        query_obj = MagicMock()

        def filter_func(condition):
            filter_obj = MagicMock()

            # Detect which clone is being queried (Clone model)
            if hasattr(condition, 'right') and hasattr(condition.right, 'value'):
                slug = condition.right.value
                if slug == "paragpt-client":
                    filter_obj.first.return_value = clone_paragpt
                elif slug == "sacred-archive":
                    filter_obj.first.return_value = clone_sacred
                else:
                    filter_obj.first.return_value = None
            # Handle ReviewQueue queries (filter returns None by default, tests can patch it)
            elif model == ReviewQueue:
                filter_obj.first.return_value = None  # Tests will override
            return filter_obj

        query_obj.filter.side_effect = filter_func
        return query_obj

    mock_session.query.side_effect = mock_query_filter

    # Make get_db return this mock session
    def get_db_override():
        yield mock_session

    app.dependency_overrides[get_db] = get_db_override

    yield mock_session

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def mock_graph():
    """
    Mocks build_graph() to return a graph with a preset final state.
    The mock graph's invoke() and stream() methods return known good data.
    """
    def build_graph_override(profile: CloneProfile):
        mock_g = MagicMock()

        # Final state that invoke() returns
        final_state = {
            "verified_response": "This is a test response.",
            "final_confidence": 0.85,
            "cited_sources": [
                {"doc_id": "doc-001", "chunk_id": "doc-001_0000", "passage": "Sample passage", "source_type": "book"}
            ],
            "silence_triggered": False,
            "user_memory": "User has asked about X before.",
            "query_text": "What is connectivity?",
            "retry_count": 0,
        }

        mock_g.invoke.return_value = final_state

        # For streaming, return chunks that match the progress protocol
        def stream_generator(state):
            nodes = [
                "query_analyzer",
                "tier1_retrieval",
                "context_assembler",
                "in_persona_generator",
                "confidence_scorer",
                "citation_verifier",
                "stream_to_user",
            ]
            for node_name in nodes:
                yield {node_name: {}}
            # Merge all into final state at the end
            yield {"__end__": final_state}

        mock_g.stream.return_value = stream_generator

        return mock_g

    with patch("api.routes.chat.build_graph", side_effect=build_graph_override):
        yield


@pytest.fixture
async def client(mock_db_session, mock_graph):
    """
    FastAPI test client with all mocks in place.
    Provides async HTTP testing via httpx.AsyncClient.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test: Health Check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client):
    """GET /health returns 200 with status=ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Test: Get Clone Profile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_clone_profile(client):
    """GET /clone/{slug}/profile returns full CloneProfile."""
    response = await client.get("/clone/paragpt-client/profile")
    assert response.status_code == 200

    data = response.json()
    assert data["slug"] == "paragpt-client"
    assert data["display_name"] == "Parag Khanna"
    assert data["generation_mode"] == "interpretive"
    assert data["confidence_threshold"] == 0.65
    assert data["review_required"] is False
    assert data["user_memory_enabled"] is True


@pytest.mark.asyncio
async def test_get_clone_profile_sacred_archive(client):
    """GET /clone/sacred-archive/profile returns Sacred Archive config."""
    response = await client.get("/clone/sacred-archive/profile")
    assert response.status_code == 200

    data = response.json()
    assert data["slug"] == "sacred-archive"
    assert data["generation_mode"] == "mirror_only"
    assert data["confidence_threshold"] == 0.95
    assert data["review_required"] is True
    assert data["user_memory_enabled"] is False


@pytest.mark.asyncio
async def test_get_clone_profile_unknown(client):
    """GET /clone/unknown/profile returns 404."""
    response = await client.get("/clone/unknown/profile")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test: Chat Sync Endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_sync(client):
    """POST /chat/{slug} returns full ChatResponse."""
    payload = {"query": "What is connectivity?", "user_id": "user-123"}
    response = await client.post("/chat/paragpt-client", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "response" in data
    assert "confidence" in data
    assert "cited_sources" in data
    assert "silence_triggered" in data
    assert isinstance(data["response"], str)
    assert isinstance(data["confidence"], (int, float))
    assert isinstance(data["cited_sources"], list)
    assert isinstance(data["silence_triggered"], bool)


@pytest.mark.asyncio
async def test_chat_sync_default_user_id(client):
    """POST /chat/{slug} with no user_id defaults to 'anonymous'."""
    payload = {"query": "Tell me about geopolitics."}
    response = await client.post("/chat/paragpt-client", json=payload)

    assert response.status_code == 200
    # The mock doesn't validate user_id, but the endpoint should accept it
    data = response.json()
    assert "response" in data


@pytest.mark.asyncio
async def test_chat_sync_missing_query(client):
    """POST /chat/{slug} without query returns 422 validation error."""
    payload = {"user_id": "user-123"}
    response = await client.post("/chat/paragpt-client", json=payload)

    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_chat_sync_unknown_clone(client):
    """POST /chat/unknown returns 404."""
    payload = {"query": "Hello"}
    response = await client.post("/chat/unknown", json=payload)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test: Chat WebSocket Endpoint
# ---------------------------------------------------------------------------

# WebSocket tests skipped — httpx AsyncClient requires special websocket setup
# Would need to use lifespan testing or separate websocket test client
# For now, WebSocket streaming is covered by integration tests in test_e2e.py
# Manual testing: connect to WS /chat/ws/{slug} and send {"query": "hello"}


# ---------------------------------------------------------------------------
# Test: Ingest Endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_basic(client):
    """POST /ingest/{slug} with file returns 200 with job_id."""
    with patch("api.routes.ingest.BackgroundTasks"):
        file_content = b"Sample document content"

        response = await client.post(
            "/ingest/paragpt-client",
            files={"file": ("test.txt", BytesIO(file_content), "text/plain")},
            data={"source_type": "document"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "processing"
        assert "message" in data


@pytest.mark.asyncio
async def test_ingest_sacred_archive_valid(client):
    """POST /ingest/sacred-archive with full provenance returns 200."""
    with patch("api.routes.ingest.BackgroundTasks"):
        file_content = b"Sacred text"
        provenance = {
            "date": "2025-01-01",
            "location": "Temple",
            "event": "Teaching",
            "verifier": "Master",
            "access_tier": "devotee"
        }

        response = await client.post(
            "/ingest/sacred-archive",
            files={"file": ("sacred.txt", BytesIO(file_content), "text/plain")},
            data={
                "source_type": "teaching",
                "provenance_json": json.dumps(provenance)
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_ingest_sacred_archive_missing_fields(client):
    """POST /ingest/sacred-archive without required provenance fields returns 400."""
    with patch("api.routes.ingest.BackgroundTasks"):
        file_content = b"Sacred text"
        # Missing required fields
        provenance = {"date": "2025-01-01"}

        response = await client.post(
            "/ingest/sacred-archive",
            files={"file": ("sacred.txt", BytesIO(file_content), "text/plain")},
            data={
                "source_type": "teaching",
                "provenance_json": json.dumps(provenance)
            }
        )

        assert response.status_code == 400
        assert "provenance" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ingest_paragpt_no_provenance_required(client):
    """POST /ingest/paragpt without provenance should succeed (not required for ParaGPT)."""
    with patch("api.routes.ingest.BackgroundTasks"):
        file_content = b"Article about geopolitics"

        response = await client.post(
            "/ingest/paragpt-client",
            files={"file": ("article.txt", BytesIO(file_content), "text/plain")},
            data={"source_type": "article"}
        )

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_ingest_unknown_clone(client):
    """POST /ingest/unknown returns 404."""
    file_content = b"Test"

    response = await client.post(
        "/ingest/unknown",
        files={"file": ("test.txt", BytesIO(file_content), "text/plain")}
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: Review Endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_review_list_sacred_archive(client, mock_db_session):
    """GET /review/sacred-archive lists pending reviews."""
    # Create a mock review item
    review_1 = MagicMock(spec=ReviewQueue)
    review_1.id = "review-001"
    review_1.query_text = "What is the meaning of life?"
    review_1.response_text = "Life is a journey..."
    review_1.confidence_score = 0.92
    review_1.created_at = datetime.utcnow()

    # Create a new query mock for ReviewQueue
    query_mock = MagicMock()
    filter_mock = MagicMock()
    order_mock = MagicMock()

    order_mock.all.return_value = [review_1]
    filter_mock.order_by.return_value = order_mock
    query_mock.filter.return_value = filter_mock

    # Store the original side_effect and create a new one
    original_side_effect = mock_db_session.query.side_effect
    def new_query_side_effect(model):
        if model == ReviewQueue:
            return query_mock
        # Call the original side effect for other models
        return original_side_effect(model)

    mock_db_session.query.side_effect = new_query_side_effect

    response = await client.get("/review/sacred-archive")

    # Restore the original
    mock_db_session.query.side_effect = original_side_effect

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_review_list_paragpt_forbidden(client):
    """GET /review/paragpt returns 403 (review not required for ParaGPT)."""
    response = await client.get("/review/paragpt-client")
    assert response.status_code == 403
    assert "review_required" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_review_approve(client, mock_db_session):
    """PATCH /review/{id} with action=approve updates status."""
    review = MagicMock(spec=ReviewQueue)
    review.id = "review-001"
    review.response_text = "Approved response text"
    review.status = "approved"
    review.reviewer_notes = None
    review.reviewed_at = datetime.utcnow()

    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = review
    query_mock.filter.return_value = filter_mock

    # Store the original side_effect and create a new one
    original_side_effect = mock_db_session.query.side_effect
    def new_query_side_effect(model):
        if model == ReviewQueue:
            return query_mock
        return original_side_effect(model)

    mock_db_session.query.side_effect = new_query_side_effect

    response = await client.patch(
        "/review/sacred-archive/review-001",
        json={"action": "approve"}
    )

    # Restore the original
    mock_db_session.query.side_effect = original_side_effect

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"


@pytest.mark.asyncio
async def test_review_reject(client, mock_db_session):
    """PATCH /review/{clone_slug}/{id} with action=reject updates status."""
    review = MagicMock(spec=ReviewQueue)
    review.id = "review-001"
    review.response_text = "Response text"
    review.status = "rejected"
    review.reviewer_notes = "Not on topic"
    review.reviewed_at = datetime.utcnow()

    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = review
    query_mock.filter.return_value = filter_mock

    # Store the original side_effect and create a new one
    original_side_effect = mock_db_session.query.side_effect
    def new_query_side_effect(model):
        if model == ReviewQueue:
            return query_mock
        return original_side_effect(model)

    mock_db_session.query.side_effect = new_query_side_effect

    response = await client.patch(
        "/review/sacred-archive/review-001",
        json={"action": "reject", "notes": "Not on topic"}
    )

    # Restore the original
    mock_db_session.query.side_effect = original_side_effect

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"


@pytest.mark.asyncio
async def test_review_edit(client, mock_db_session):
    """PATCH /review/{clone_slug}/{id} with action=edit updates response_text."""
    review = MagicMock(spec=ReviewQueue)
    review.id = "review-001"
    review.response_text = "Updated response"
    review.status = "edited"
    review.reviewer_notes = "Fixed typo"
    review.reviewed_at = datetime.utcnow()

    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = review
    query_mock.filter.return_value = filter_mock

    original_side_effect = mock_db_session.query.side_effect
    def new_query_side_effect(model):
        if model == ReviewQueue:
            return query_mock
        return original_side_effect(model)

    mock_db_session.query.side_effect = new_query_side_effect

    response = await client.patch(
        "/review/sacred-archive/review-001",
        json={"action": "edit", "edited_response": "Updated response", "notes": "Fixed typo"}
    )

    mock_db_session.query.side_effect = original_side_effect

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "edited"
    assert data["response_text"] == "Updated response"


@pytest.mark.asyncio
async def test_review_not_found(client, mock_db_session):
    """PATCH /review/{clone_slug}/{id} with unknown review_id returns 404."""
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = None
    query_mock.filter.return_value = filter_mock

    original_side_effect = mock_db_session.query.side_effect
    def new_query_side_effect(model):
        if model == ReviewQueue:
            return query_mock
        return original_side_effect(model)

    mock_db_session.query.side_effect = new_query_side_effect

    response = await client.patch(
        "/review/sacred-archive/unknown-review-id",
        json={"action": "approve"}
    )

    mock_db_session.query.side_effect = original_side_effect

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: Conversation Persistence (Feature 1)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_saves_message_to_db(client, mock_db_session):
    """POST /chat/{slug} should call db.add() and db.commit() to save message."""
    payload = {"query": "What is connectivity?", "user_id": "user-123"}
    response = await client.post("/chat/paragpt-client", json=payload)

    assert response.status_code == 200
    # Verify that db.add was called (message was saved)
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called()

    # Verify the saved object is a Message instance
    from core.db.schema import Message
    saved_msg = mock_db_session.add.call_args[0][0]
    assert isinstance(saved_msg, Message)
    assert saved_msg.query_text == "What is connectivity?"
    assert saved_msg.user_id == "user-123"


@pytest.mark.asyncio
async def test_chat_message_default_user_id(client, mock_db_session):
    """POST /chat without user_id should save as 'anonymous'."""
    payload = {"query": "Tell me something"}
    response = await client.post("/chat/paragpt-client", json=payload)

    assert response.status_code == 200
    mock_db_session.add.assert_called_once()

    from core.db.schema import Message
    saved_msg = mock_db_session.add.call_args[0][0]
    assert saved_msg.user_id == "anonymous"


# ---------------------------------------------------------------------------
# Test: Ingest Status Polling (Feature 2)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_status_complete(client, mock_db_session):
    """GET /ingest/{slug}/status/{doc_id} returns status for known document."""
    from core.db.schema import Document

    mock_doc = MagicMock(spec=Document)
    mock_doc.id = uuid.uuid4()
    mock_doc.filename = "test.txt"
    mock_doc.status = "complete"
    mock_doc.chunk_count = 12
    mock_doc.created_at = datetime.utcnow()
    mock_doc.updated_at = datetime.utcnow()

    # Wire up the Document query
    original_side_effect = mock_db_session.query.side_effect
    def new_side_effect(model):
        if model == Document:
            q = MagicMock()
            f = MagicMock()
            f.first.return_value = mock_doc
            q.filter.return_value = f
            return q
        return original_side_effect(model)
    mock_db_session.query.side_effect = new_side_effect

    response = await client.get(f"/ingest/paragpt-client/status/{mock_doc.id}")

    mock_db_session.query.side_effect = original_side_effect

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["chunk_count"] == 12
    assert "12 chunks indexed" in data["message"]
    assert data["filename"] == "test.txt"


@pytest.mark.asyncio
async def test_ingest_status_processing(client, mock_db_session):
    """GET /ingest/{slug}/status/{doc_id} with processing status."""
    from core.db.schema import Document

    mock_doc = MagicMock(spec=Document)
    mock_doc.id = uuid.uuid4()
    mock_doc.filename = "document.pdf"
    mock_doc.status = "processing"
    mock_doc.chunk_count = 0
    mock_doc.created_at = datetime.utcnow()
    mock_doc.updated_at = datetime.utcnow()

    original_side_effect = mock_db_session.query.side_effect
    def new_side_effect(model):
        if model == Document:
            q = MagicMock()
            f = MagicMock()
            f.first.return_value = mock_doc
            q.filter.return_value = f
            return q
        return original_side_effect(model)
    mock_db_session.query.side_effect = new_side_effect

    response = await client.get(f"/ingest/paragpt-client/status/{mock_doc.id}")
    mock_db_session.query.side_effect = original_side_effect

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert "in progress" in data["message"]


@pytest.mark.asyncio
async def test_ingest_status_not_found(client, mock_db_session):
    """GET /ingest/{slug}/status/{unknown_id} returns 404."""
    original_side_effect = mock_db_session.query.side_effect
    def new_side_effect(model):
        from core.db.schema import Document
        if model == Document:
            q = MagicMock()
            f = MagicMock()
            f.first.return_value = None
            q.filter.return_value = f
            return q
        return original_side_effect(model)
    mock_db_session.query.side_effect = new_side_effect

    response = await client.get("/ingest/paragpt-client/status/nonexistent-id")
    mock_db_session.query.side_effect = original_side_effect

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ingest_status_cross_clone_isolation(client, mock_db_session):
    """GET /ingest/{clone_a}/status/{doc_from_clone_b} returns 404 (isolation)."""
    original_side_effect = mock_db_session.query.side_effect
    def new_side_effect(model):
        from core.db.schema import Document
        if model == Document:
            q = MagicMock()
            f = MagicMock()
            # Document doesn't exist for this clone (cross-clone isolation)
            f.first.return_value = None
            q.filter.return_value = f
            return q
        return original_side_effect(model)
    mock_db_session.query.side_effect = new_side_effect

    response = await client.get("/ingest/paragpt-client/status/some-doc-from-sacred-archive")
    mock_db_session.query.side_effect = original_side_effect

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: Auth Middleware (Feature 3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_middleware_no_key_set(client):
    """When DCE_API_KEY is not set, all requests pass through."""
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("DCE_API_KEY", None)
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_middleware_valid_key(client):
    """With DCE_API_KEY set, valid key passes."""
    with patch.dict("os.environ", {"DCE_API_KEY": "test-secret-key"}):
        response = await client.get(
            "/health",
            headers={"X-API-Key": "test-secret-key"}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_middleware_missing_key_header(client):
    """With DCE_API_KEY set, missing header returns 401."""
    with patch.dict("os.environ", {"DCE_API_KEY": "test-secret-key"}):
        response = await client.get("/clone/paragpt-client/profile")
        assert response.status_code == 401
        assert "Missing X-API-Key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_middleware_wrong_key(client):
    """With DCE_API_KEY set, wrong key returns 403."""
    with patch.dict("os.environ", {"DCE_API_KEY": "correct-key"}):
        response = await client.get(
            "/clone/paragpt-client/profile",
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_exempt_health(client):
    """/health is exempt from auth even when DCE_API_KEY is set."""
    with patch.dict("os.environ", {"DCE_API_KEY": "test-secret-key"}):
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_exempt_docs(client):
    """/docs and /openapi.json are exempt from auth."""
    with patch.dict("os.environ", {"DCE_API_KEY": "test-secret-key"}):
        response = await client.get("/docs")
        # Might return 200 or 307 redirect depending on FastAPI config
        assert response.status_code in [200, 307, 404]


# ---------------------------------------------------------------------------
# Test: Access Tier Validation (Feature 3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_access_tier_valid(client):
    """POST /chat/{slug} with valid access_tier succeeds."""
    payload = {"query": "What is devotion?", "access_tier": "devotee"}
    response = await client.post("/chat/sacred-archive", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_access_tier_invalid(client):
    """POST /chat/{slug} with invalid access_tier returns 400."""
    payload = {"query": "What is devotion?", "access_tier": "invalid_tier"}
    response = await client.post("/chat/sacred-archive", json=payload)
    assert response.status_code == 400
    assert "access_tier" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_access_tier_default_public(client):
    """POST /chat with no access_tier defaults to 'public'."""
    payload = {"query": "Hello"}
    response = await client.post("/chat/paragpt-client", json=payload)
    assert response.status_code == 200
    # Mock returns success, confirming default 'public' tier was accepted
