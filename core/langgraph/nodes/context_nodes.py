"""
Context Assembly Nodes (2 nodes)

Assemble retrieved passages into a context window, inject provenance metadata,
and optionally retrieve cross-session user memory.
"""

from typing import TypedDict


def context_assembler(state: TypedDict) -> TypedDict:
    """
    Assemble retrieved passages and provenance graph results into a context string.

    PARTIAL IMPLEMENTATION: No external dependencies. Assembles passages, respects
    token budget, injects provenance metadata (for Sacred Archive graph queries).

    Input: retrieved_passages, provenance_graph_results, token_budget
    Output: assembled_context
    """

    passages = state.get("retrieved_passages", [])
    provenance = state.get("provenance_graph_results", [])
    token_budget = state.get("token_budget", 2000)

    # Simple context assembly: concatenate passages with metadata
    context_lines = []

    if passages:
        context_lines.append("# Retrieved Context\n")
        for i, passage in enumerate(passages, 1):
            # Each passage is a dict: {doc_id, chunk_id, passage, source_type, date, access_tier}
            doc_id = passage.get("doc_id", "unknown")
            source = passage.get("source_type", "unknown")
            text = passage.get("passage", "")

            context_lines.append(f"[{i}] {source} (doc_id={doc_id}):")
            context_lines.append(text)
            context_lines.append("")

    if provenance:
        context_lines.append("# Related Teachings (Provenance Graph)\n")
        for edge in provenance:
            # Each edge is a dict: {teaching_id, related_teaching_id, path}
            teaching_id = edge.get("teaching_id", "unknown")
            related = edge.get("related_teaching_id", "unknown")
            path = edge.get("path", "unknown")

            context_lines.append(f"Connection: {teaching_id} → {related} ({path})")

    # Estimate tokens (very rough: ~1 token per word, ~5 chars per word)
    assembled = "\n".join(context_lines)
    estimated_tokens = len(assembled) // 5  # Very rough estimate

    if estimated_tokens > token_budget:
        # Truncate if over budget (simple approach; production would be smarter)
        assembled = assembled[: token_budget * 5]

    return {
        **state,
        "assembled_context": assembled,
    }


def memory_retrieval(state: TypedDict) -> TypedDict:
    """
    Retrieve cross-session user memory from Mem0 (ParaGPT only).

    Searches Mem0's pgvector backend for memories related to the user's query.
    Returns formatted memory string to inject into the system prompt for context.

    Input: user_id, query_text
    Output: user_memory (formatted string of relevant past memories, or empty if none)
    """
    from core.mem0_client import get_mem0_client

    user_id = state.get("user_id", "anonymous")
    query = state.get("query_text", "")

    if not query:
        return {**state, "user_memory": ""}

    try:
        mem = get_mem0_client()
        results = mem.search(query, user_id=user_id, limit=5)

        if results and results.get("results"):
            memories = [r.get("memory", "") for r in results["results"] if r.get("memory")]
            if memories:
                user_memory = "Past context about this user:\n" + "\n".join(
                    f"- {m}" for m in memories
                )
            else:
                user_memory = ""
        else:
            user_memory = ""

    except Exception as e:
        # Graceful fallback: if Mem0 unavailable, proceed without memories
        user_memory = ""

    return {**state, "user_memory": user_memory}


def memory_writer(state: TypedDict) -> TypedDict:
    """
    Write the conversation turn to Mem0 for cross-session memory.

    Called after response is generated and streamed to user. Mem0 extracts facts
    from the conversation and stores them in pgvector for future retrieval.

    Input: user_id, query_text, verified_response
    Output: state (unchanged) — this is a side-effect node
    """
    from core.mem0_client import get_mem0_client
    import logging

    logger = logging.getLogger(__name__)

    user_id = state.get("user_id", "anonymous")
    query = state.get("query_text", "")
    response = state.get("verified_response", "")

    if not query or not response:
        return state

    try:
        mem = get_mem0_client()
        messages = [
            {"role": "user", "content": query},
            {"role": "assistant", "content": response},
        ]
        mem.add(messages, user_id=user_id)

    except Exception as e:
        # Graceful fallback: if Mem0 write fails, log warning but continue
        logger.warning(f"Failed to save memory to Mem0: {str(e)}")

    return state


def conversation_history_node(state: TypedDict) -> TypedDict:
    """
    Retrieve recent conversation history from the messages table.

    Queries the last 5 message exchanges for this clone_id + user_id,
    ordered most-recent-first then reversed for chronological display.
    Enables multi-turn conversations: the LLM can see prior context
    and respond to follow-up questions like "tell me more about that."

    Input: clone_id, user_id
    Output: conversation_history (formatted string)
    """
    import psycopg
    from core.db import psycopg_url as _psycopg_url
    import logging

    logger = logging.getLogger(__name__)

    clone_id = state.get("clone_id", "")
    user_id = state.get("user_id", "anonymous")

    if not clone_id or not user_id:
        return {**state, "conversation_history": ""}

    db_url = _psycopg_url()
    if not db_url:
        return {**state, "conversation_history": ""}

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT query_text, response_text
                    FROM messages
                    WHERE clone_id = %s AND user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                    """,
                    (clone_id, user_id),
                )
                rows = cur.fetchall()

        if not rows:
            return {**state, "conversation_history": ""}

        # Format oldest-first for natural reading order
        lines = []
        for query_text, response_text in reversed(rows):
            lines.append(f"User: {query_text}")
            # Truncate long responses to keep context manageable (~1000 tokens max per response)
            truncated = response_text[:800] + "..." if len(response_text) > 800 else response_text
            lines.append(f"Assistant: {truncated}")

        history = "Previous conversation:\n" + "\n".join(lines)
        return {**state, "conversation_history": history}

    except Exception as e:
        logger.warning(f"conversation_history_node failed: {e}")
        return {**state, "conversation_history": ""}
