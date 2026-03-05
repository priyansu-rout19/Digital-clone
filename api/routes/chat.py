import json
import copy
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_clone, get_db
from core.models.clone_profile import CloneProfile
from core.langgraph.conversation_flow import build_graph


router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = "anonymous"
    access_tier: Optional[str] = "public"


class ChatResponse(BaseModel):
    response: str
    confidence: float
    cited_sources: list[dict]
    silence_triggered: bool
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = None


def build_initial_state(query: str, clone_id: str, user_id: str, access_tier: str = "public") -> dict:
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


@router.post("/{clone_slug}")
async def chat_sync(
    clone_slug: str,
    request: ChatRequest,
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
    if request.access_tier not in valid_tiers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid access_tier '{request.access_tier}'. Valid tiers: {sorted(valid_tiers)}",
        )

    # Build initial state with access_tier
    initial_state = build_initial_state(request.query, clone_id, request.user_id, request.access_tier)

    # Build and invoke graph
    graph = build_graph(profile)
    final_state = graph.invoke(copy.deepcopy(initial_state))

    # Save the exchange to messages table (fire-and-forget within request)
    from core.db.schema import Message
    msg = Message(
        clone_id=clone_id,
        user_id=request.user_id or "anonymous",
        query_text=request.query,
        response_text=final_state.get("verified_response") or final_state.get("raw_response", ""),
        confidence=final_state.get("final_confidence", 0.0),
        silence_triggered=final_state.get("silence_triggered", False),
        cited_sources=final_state.get("cited_sources", []),
    )
    db.add(msg)
    db.commit()

    # Extract response fields (user_memory excluded — internal pipeline use only)
    return ChatResponse(
        response=final_state.get("verified_response", ""),
        confidence=final_state.get("final_confidence", 0.0),
        cited_sources=final_state.get("cited_sources", []),
        silence_triggered=final_state.get("silence_triggered", False),
        audio_base64=final_state.get("audio_base64") or None,
        audio_format=final_state.get("audio_format") or None,
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

        if not query:
            await websocket.send_json({"type": "error", "message": "query is required"})
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

            # Build initial state with access_tier
            initial_state = build_initial_state(query, clone_id, user_id, access_tier)

            # Build graph and stream
            graph = build_graph(profile)

            # Stream each node completion and capture final state
            final_state = copy.deepcopy(initial_state)
            for chunk in graph.stream(copy.deepcopy(initial_state)):
                # chunk is {node_name: node_output_dict}
                node_names = list(chunk.keys())
                if node_names:
                    node_name = node_names[0]
                    # Update final_state with the latest node output
                    final_state.update(chunk[node_name])
                    await websocket.send_json({"type": "progress", "node": node_name})

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

            # Send final response after all nodes complete and message saved
            await websocket.send_json(
                {
                    "type": "response",
                    "response": final_state.get("verified_response", ""),
                    "confidence": final_state.get("final_confidence", 0.0),
                    "cited_sources": final_state.get("cited_sources", []),
                    "silence_triggered": final_state.get("silence_triggered", False),
                    "audio_base64": final_state.get("audio_base64") or None,
                    "audio_format": final_state.get("audio_format") or None,
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
