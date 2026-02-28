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

    STUB: Depends on Mem0 integration (not yet wired into the system).
    Returns empty string for mock invocation.

    Input: user_id, query_text (implicit: user_id not in state schema, would be added)
    Output: user_memory
    """

    # STUB: In production, this would:
    # 1. Query Mem0 for memories related to this user + query
    # 2. Mem0 uses pgvector backend (decided in Q3 research)
    # 3. Returns formatted memory string to inject into prompt

    return {
        **state,
        "user_memory": "",  # Empty for stub; would be formatted memory string
    }
