import json
import copy
import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import psycopg
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.deps import get_clone, get_db
from core.audit import write_audit, extract_actor
from core.db import psycopg_url as _psycopg_url
from core.db.schema import AuditDetails
from core.models.clone_profile import CloneProfile
from core.langgraph.conversation_flow import build_graph
from core.llm import LLM_MODEL

limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)


router = APIRouter()


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[str] = "anonymous"
    access_tier: Optional[str] = "public"
    model: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    confidence: float
    cited_sources: list[dict]
    silence_triggered: bool
    suggested_topics: list[str] = []
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = None
    model: Optional[str] = None
    review_id: Optional[str] = None


def build_initial_state(query: str, clone_id: str, user_id: str,
                        access_tier: str = "public", model: str = "",
                        voice_enabled: bool = True) -> dict:
    """Build the initial ConversationState dict for the graph."""
    return {
        "query_text": query,
        "clone_id": clone_id,
        "user_id": user_id,
        "sub_queries": [],
        "intent_class": "",
        "access_tier": access_tier,
        "token_budget": 2000,
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
        "model_override": model,
        "review_id": "",
        "voice_enabled": voice_enabled,
    }


def _write_analytics(clone_id: str, user_id: str, query_text: str,
                     final_state: dict, latency_ms: int) -> None:
    """Write a row to query_analytics table. Fails silently — never crashes the response."""
    db_url = _psycopg_url()
    if not db_url:
        return

    # "anonymous" is not a valid UUID — set to None
    user_id_val = None
    if user_id and user_id != "anonymous":
        try:
            uuid.UUID(user_id)
            user_id_val = user_id
        except ValueError:
            user_id_val = None

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO query_analytics
                        (clone_id, user_id, query_text, intent_class,
                         confidence_score, latency_ms, tier_used, silence_triggered)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        clone_id,
                        user_id_val,
                        query_text[:500],  # truncate long queries for analytics
                        final_state.get("intent_class", ""),
                        final_state.get("final_confidence", 0.0),
                        latency_ms,
                        final_state.get("access_tier", "public"),
                        final_state.get("silence_triggered", False),
                    ),
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Analytics write failed: {e}")


def _extract_trace_data(node_name: str, node_output: dict) -> dict:
    """
    Extract curated metrics from a node's output for the reasoning trace.
    Returns a small dict with only the relevant data points for each node.
    Never includes full passages or assembled context (too large for WS).
    """
    trace: dict = {"node": node_name}

    if node_name == "query_analysis":
        trace["intent"] = node_output.get("intent_class", "")
        trace["sub_query_count"] = len(node_output.get("sub_queries", []))
        trace["response_tokens"] = node_output.get("response_tokens", 0)
    elif node_name == "tier1_retrieval":
        passages = node_output.get("retrieved_passages", [])
        trace["passage_count"] = len(passages)
        trace["confidence"] = round(node_output.get("retrieval_confidence", 0.0), 3)
        # Show which search methods produced results (vector, BM25, or both)
        meta = node_output.get("search_meta", {})
        trace["vector_count"] = meta.get("vector_count", 0)
        trace["bm25_count"] = meta.get("bm25_count", 0)
        # Show if reranking was used (rerank_score present on passages)
        if passages and passages[0].get("rerank_score") is not None:
            trace["reranked"] = True
            trace["top_rerank_score"] = passages[0].get("rerank_score", 0.0)
    elif node_name == "tier2_tree_search":
        trace["passage_count"] = len(node_output.get("retrieved_passages", []))
    elif node_name == "crag_evaluator":
        trace["confidence"] = round(node_output.get("retrieval_confidence", 0.0), 3)
    elif node_name == "query_reformulator":
        trace["retry_count"] = node_output.get("retry_count", 0)
        trace["new_queries"] = len(node_output.get("sub_queries", []))
    elif node_name == "context_assembler":
        ctx = node_output.get("assembled_context", "")
        trace["context_chars"] = len(ctx)
    elif node_name == "conversation_history":
        trace["has_history"] = bool(node_output.get("conversation_history", ""))
    elif node_name == "memory_retrieval":
        trace["has_memory"] = bool(node_output.get("user_memory", ""))
    elif node_name == "in_persona_generator":
        trace["generated"] = True
    elif node_name == "citation_verifier":
        trace["citation_count"] = len(node_output.get("cited_sources", []))
    elif node_name == "confidence_scorer":
        trace["final_confidence"] = round(node_output.get("final_confidence", 0.0), 3)
    elif node_name in ("soft_hedge_router", "strict_silence_router"):
        trace["silence_triggered"] = True
    elif node_name == "voice_pipeline":
        trace["has_audio"] = bool(node_output.get("audio_base64", ""))

    return trace


@router.post("/{clone_slug}")
@limiter.limit("60/minute")
async def chat_sync(
    request: Request,
    clone_slug: str,
    chat_request: ChatRequest,
    clone_info: tuple[str, CloneProfile] = Depends(get_clone),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Synchronous chat endpoint.
    Accepts a query, runs the full LangGraph pipeline, and returns the complete response.
    Saves conversation exchange to messages table.
    """
    clone_id, profile = clone_info

    # Validate access_tier (format check against AccessTier enum)
    from core.models.clone_profile import AccessTier
    valid_tiers = {t.value for t in AccessTier}
    if chat_request.access_tier not in valid_tiers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid access_tier '{chat_request.access_tier}'. Valid tiers: {sorted(valid_tiers)}",
        )

    # Build initial state with access_tier and model override
    initial_state = build_initial_state(
        chat_request.query, clone_id, chat_request.user_id,
        chat_request.access_tier, chat_request.model or "",
    )

    # Build and invoke graph (with latency tracking)
    graph = build_graph(profile)
    t0 = time.time()
    final_state = graph.invoke(copy.deepcopy(initial_state))
    latency_ms = int((time.time() - t0) * 1000)

    # Save the exchange to messages table (fire-and-forget within request)
    from core.db.schema import Message
    msg = Message(
        clone_id=clone_id,
        user_id=chat_request.user_id or "anonymous",
        query_text=chat_request.query,
        response_text=final_state.get("verified_response") or final_state.get("raw_response", ""),
        confidence=final_state.get("final_confidence", 0.0),
        silence_triggered=final_state.get("silence_triggered", False),
        cited_sources=final_state.get("cited_sources", []),
    )
    db.add(msg)
    db.commit()

    # Write analytics (non-blocking, fails silently)
    _write_analytics(clone_id, chat_request.user_id, chat_request.query, final_state, latency_ms)

    # Audit log — every query logged per SOW
    actor_id, actor_role = extract_actor(request)
    write_audit(
        db,
        clone_id=clone_id,
        action="chat.query",
        actor_id=actor_id or chat_request.user_id,
        actor_role=actor_role or "user",
        details=AuditDetails(
            query_text=chat_request.query[:500],
            confidence=final_state.get("final_confidence", 0.0),
            silence_triggered=final_state.get("silence_triggered", False),
        ),
    )

    # Extract response fields (user_memory excluded — internal pipeline use only)
    return ChatResponse(
        response=final_state.get("verified_response", ""),
        confidence=final_state.get("final_confidence", 0.0),
        cited_sources=final_state.get("cited_sources", []),
        silence_triggered=final_state.get("silence_triggered", False),
        suggested_topics=final_state.get("suggested_topics", []),
        audio_base64=final_state.get("audio_base64") or None,
        audio_format=final_state.get("audio_format") or None,
        model=final_state.get("model_override") or LLM_MODEL,
        review_id=final_state.get("review_id") or None,
    )


@router.websocket("/ws/{clone_slug}")
async def chat_ws(
    websocket: WebSocket,
    clone_slug: str,
):
    """
    WebSocket chat endpoint with streaming response.
    Streams progress events (one per node) then final response.

    Protocol:
    - Client sends: { "query": str, "user_id": str? }
    - Server sends progress: { "type": "progress", "node": "node_name" }
    - Server sends final: { "type": "response", "response": str, "confidence": float, ... }
    """
    await websocket.accept()

    try:
        # Receive initial message
        data = await websocket.receive_json()
        query = data.get("query")
        user_id = data.get("user_id", "anonymous")
        access_tier = data.get("access_tier", "public")
        model = data.get("model", "")
        voice_enabled = data.get("voice_enabled", True)

        if not query:
            await websocket.send_json({"type": "error", "message": "query is required"})
            await websocket.close()
            return

        if len(query) > 2000:
            await websocket.send_json({"type": "error", "message": "query must be 2000 characters or less"})
            await websocket.close()
            return

        # Validate access_tier (format check)
        from core.models.clone_profile import AccessTier
        valid_tiers = {t.value for t in AccessTier}
        if access_tier not in valid_tiers:
            await websocket.send_json(
                {"type": "error", "message": f"Invalid access_tier. Valid: {sorted(valid_tiers)}"}
            )
            await websocket.close()
            return

        # Load clone and keep db session open for message save
        from api.deps import SessionLocal

        db = SessionLocal()
        try:
            from core.db.schema import Clone
            clone_row = db.query(Clone).filter(Clone.slug == clone_slug).first()
            if not clone_row:
                await websocket.send_json(
                    {"type": "error", "message": f"Clone '{clone_slug}' not found"}
                )
                await websocket.close()
                return

            from core.models.clone_profile import CloneProfile as CP

            profile = CP(**clone_row.profile)
            clone_id = str(clone_row.id)

            # Build initial state with access_tier and model override
            initial_state = build_initial_state(query, clone_id, user_id, access_tier, model, voice_enabled)

            # Build graph and stream (with latency tracking)
            graph = build_graph(profile)
            t0 = time.time()

            # Stream each node completion and capture final state
            final_state = copy.deepcopy(initial_state)
            for chunk in graph.stream(copy.deepcopy(initial_state)):
                # chunk is {node_name: node_output_dict}
                node_names = list(chunk.keys())
                if node_names:
                    node_name = node_names[0]
                    node_output = chunk[node_name]
                    # Update final_state with the latest node output
                    final_state.update(node_output)
                    trace = _extract_trace_data(node_name, node_output)
                    await websocket.send_json({"type": "progress", "node": node_name, "trace": trace})

            latency_ms = int((time.time() - t0) * 1000)

            # Save the exchange to messages table before sending final response
            from core.db.schema import Message
            msg = Message(
                clone_id=clone_id,
                user_id=user_id or "anonymous",
                query_text=query,
                response_text=final_state.get("verified_response") or final_state.get("raw_response", ""),
                confidence=final_state.get("final_confidence", 0.0),
                silence_triggered=final_state.get("silence_triggered", False),
                cited_sources=final_state.get("cited_sources", []),
            )
            db.add(msg)
            db.commit()

            # Write analytics (non-blocking, fails silently)
            _write_analytics(clone_id, user_id, query, final_state, latency_ms)

            # Audit log — every query logged per SOW
            write_audit(
                db,
                clone_id=clone_id,
                action="chat.query",
                actor_id=user_id if user_id != "anonymous" else None,
                actor_role="user",
                details=AuditDetails(
                    query_text=query[:500],
                    confidence=final_state.get("final_confidence", 0.0),
                    silence_triggered=final_state.get("silence_triggered", False),
                ),
            )

            # Send final response after all nodes complete and message saved
            await websocket.send_json(
                {
                    "type": "response",
                    "response": final_state.get("verified_response", ""),
                    "confidence": final_state.get("final_confidence", 0.0),
                    "cited_sources": final_state.get("cited_sources", []),
                    "silence_triggered": final_state.get("silence_triggered", False),
                    "suggested_topics": final_state.get("suggested_topics", []),
                    "audio_base64": final_state.get("audio_base64") or None,
                    "audio_format": final_state.get("audio_format") or None,
                    "model": final_state.get("model_override") or LLM_MODEL,
                    "review_id": final_state.get("review_id") or None,
                }
            )
        finally:
            db.close()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
