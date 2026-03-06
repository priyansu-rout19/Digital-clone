"""
LangGraph Conversation Flow (Component 04)

One unified StateGraph serving both ParaGPT and Sacred Archive. Feature flags
from CloneProfile determine which nodes activate, not at graph definition time,
but at runtime via conditional routing logic.

Graph structure:
- 7 always-active nodes: query_analysis, tier1_retrieval, crag_evaluator,
  context_assembler, in_persona_generator, citation_verifier, confidence_scorer
- 9 conditional nodes: provenance_graph_query, tier2_tree_search, query_reformulator,
  memory_retrieval, memory_writer, review_queue_writer, soft_hedge_router, strict_silence_router,
  voice_pipeline
- 1 output node: stream_to_user (can route from multiple paths)

All state passed via typed ConversationState dict. All conditional logic driven
by CloneProfile field values (captured in closures at graph build time).
"""

from typing import TypedDict, Union
from langgraph.graph import StateGraph

from core.models.clone_profile import CloneProfile, VoiceMode, SilenceBehavior, RetrievalTier
from core.langgraph.nodes.query_analysis_node import query_analysis
from core.langgraph.nodes.retrieval_nodes import (
    provenance_graph_query,
    tier1_retrieval,
    crag_evaluator,
    query_reformulator,
    tier2_tree_search,
)
from core.langgraph.nodes.context_nodes import context_assembler, memory_retrieval, memory_writer, conversation_history_node
from core.langgraph.nodes.generation_nodes import make_in_persona_generator, citation_verifier, confidence_scorer
from core.langgraph.nodes.routing_nodes import (
    make_soft_hedge_router,
    make_strict_silence_router,
    review_queue_writer,
    stream_to_user,
    make_voice_pipeline,
)


# ============================================================================
# STATE SCHEMA
# ============================================================================

class ConversationState(TypedDict):
    """
    Typed state dict for all conversation context passed between nodes.
    24 keys: query, retrieval, context, generation, routing.
    """

    # Query & Analysis (set by query_analysis)
    query_text: str
    sub_queries: list[str]
    intent_class: str  # factual | synthesis | opinion | temporal | exploratory
    access_tier: str  # public | devotee | friend | follower
    token_budget: int
    response_tokens: int  # max output tokens for response generation (LLM-estimated)

    # Retrieval (scope queries to one clone; set by tier1/tier2, crag_evaluator, query_reformulator)
    clone_id: str  # UUID of the clone making the query
    user_id: str  # UUID of the user (for Mem0 scoping). Defaults to "anonymous" if not authenticated.
    retrieved_passages: list[dict]  # [{doc_id, chunk_id, passage, source_type, date, access_tier}]
    provenance_graph_results: list[dict]  # [{teaching_id, related_teaching_id, path}]
    retrieval_confidence: float  # 0.0-1.0
    retry_count: int

    # Context & Memory (set by context_assembler, memory_retrieval, conversation_history)
    assembled_context: str
    user_memory: str  # cross-session memory from Mem0 (if enabled)
    conversation_history: str  # formatted last N messages for multi-turn context

    # Generation & Verification (set by in_persona_generator, citation_verifier, confidence_scorer)
    raw_response: str
    verified_response: str
    final_confidence: float  # 0.0-1.0
    cited_sources: list[dict]  # [{doc_id, chunk_id, passage, provenance}]

    # Output Routing (set by routing nodes)
    silence_triggered: bool
    suggested_topics: list[str]  # topic suggestions for silence messages (extracted from passages)
    voice_chunks: list[str]  # text chunks for TTS
    audio_base64: str  # base64-encoded MP3 audio from TTS (empty if text_only)
    audio_format: str  # "mp3" or "" (set by voice_pipeline)


# ============================================================================
# CONDITIONAL ROUTING FUNCTIONS
# ============================================================================

def build_graph(profile: CloneProfile):
    """
    Build a LangGraph StateGraph configured for the given clone profile.

    Profile is captured in closures by routing functions so that behavior
    (which nodes activate, thresholds, silence behavior) is determined at
    graph build time, not at node execution time.

    Args:
        profile: CloneProfile instance (ParaGPT or Sacred Archive)

    Returns:
        Compiled LangGraph graph ready to invoke
    """

    # Create graph
    graph = StateGraph(ConversationState)

    # ========================================================================
    # ADD ALL NODES (7 always + 9 conditional + 1 output)
    # ========================================================================

    # Always active (7)
    graph.add_node("query_analysis", query_analysis)
    graph.add_node("tier1_retrieval", tier1_retrieval)
    graph.add_node("crag_evaluator", crag_evaluator)
    graph.add_node("context_assembler", context_assembler)
    graph.add_node("conversation_history", conversation_history_node)
    graph.add_node("in_persona_generator", make_in_persona_generator(profile))  # Factory: captures profile
    graph.add_node("citation_verifier", citation_verifier)
    graph.add_node("confidence_scorer", confidence_scorer)

    # Conditional (9)
    graph.add_node("provenance_graph_query", provenance_graph_query)
    graph.add_node("tier2_tree_search", tier2_tree_search)
    graph.add_node("query_reformulator", query_reformulator)
    graph.add_node("memory_retrieval", memory_retrieval)
    graph.add_node("memory_writer", memory_writer)  # New: writes turn to Mem0 after streaming
    graph.add_node("review_queue_writer", review_queue_writer)
    graph.add_node("soft_hedge_router", make_soft_hedge_router(profile))  # Factory: captures profile
    graph.add_node("strict_silence_router", make_strict_silence_router(profile))  # Factory: captures profile
    graph.add_node("voice_pipeline", make_voice_pipeline(profile))

    # Output (1)
    graph.add_node("stream_to_user", stream_to_user)

    # ========================================================================
    # SET ENTRY POINT
    # ========================================================================

    graph.set_entry_point("query_analysis")

    # ========================================================================
    # ADD EDGES WITH CONDITIONAL ROUTING
    # ========================================================================

    # After query_analysis: provenance graph (if enabled) or direct to tier1_retrieval
    def after_query_analysis(state: ConversationState) -> str:
        if profile.provenance_graph_enabled:
            return "provenance_graph_query"
        return "tier1_retrieval"

    graph.add_conditional_edges(
        "query_analysis",
        after_query_analysis,
        {
            "provenance_graph_query": "provenance_graph_query",
            "tier1_retrieval": "tier1_retrieval",
        },
    )

    # provenance_graph_query → tier1_retrieval (always)
    graph.add_edge("provenance_graph_query", "tier1_retrieval")

    # tier1_retrieval → tier2_tree_search or crag_evaluator (conditional on profile)
    def after_tier1(state: ConversationState) -> str:
        if RetrievalTier.tree_search in profile.retrieval_tiers:
            return "tier2_tree_search"
        return "crag_evaluator"

    graph.add_conditional_edges(
        "tier1_retrieval",
        after_tier1,
        {
            "tier2_tree_search": "tier2_tree_search",
            "crag_evaluator": "crag_evaluator",
        },
    )

    # crag_evaluator: retry or proceed (tree_search now runs before CRAG)
    def after_crag(state: ConversationState) -> str:
        confidence = state.get("retrieval_confidence", 0.0)
        retry_count = state.get("retry_count", 0)
        max_retries = 3

        # Should we retry? (Tier 2 already ran before CRAG if applicable)
        if confidence < profile.confidence_threshold and retry_count < max_retries:
            return "query_reformulator"

        # Proceed to context assembly
        return "context_assembler"

    graph.add_conditional_edges(
        "crag_evaluator",
        after_crag,
        {
            "query_reformulator": "query_reformulator",
            "context_assembler": "context_assembler",
        },
    )

    # query_reformulator → tier1_retrieval (loop back for retry)
    graph.add_edge("query_reformulator", "tier1_retrieval")

    # tier2_tree_search → crag_evaluator (augmented passages evaluated for confidence)
    graph.add_edge("tier2_tree_search", "crag_evaluator")

    # context_assembler → conversation_history (always — both clients need multi-turn)
    graph.add_edge("context_assembler", "conversation_history")

    # conversation_history: memory retrieval (if enabled) or direct to generation
    def after_history(state: ConversationState) -> str:
        if profile.user_memory_enabled:
            return "memory_retrieval"
        return "in_persona_generator"

    graph.add_conditional_edges(
        "conversation_history",
        after_history,
        {
            "memory_retrieval": "memory_retrieval",
            "in_persona_generator": "in_persona_generator",
        },
    )

    # memory_retrieval → in_persona_generator (always)
    graph.add_edge("memory_retrieval", "in_persona_generator")

    # in_persona_generator → citation_verifier (always)
    graph.add_edge("in_persona_generator", "citation_verifier")

    # citation_verifier → confidence_scorer (always)
    graph.add_edge("citation_verifier", "confidence_scorer")

    # confidence_scorer: review queue OR stream OR silence handling
    def after_confidence(state: ConversationState) -> str:
        final_confidence = state.get("final_confidence", 0.0)

        # First: does this go to review queue?
        if profile.review_required:
            return "review_queue_writer"

        # Second: is confidence high enough?
        if final_confidence >= profile.confidence_threshold:
            return "stream_to_user"

        # Third: how do we handle low confidence?
        if profile.silence_behavior == SilenceBehavior.soft_hedge:
            return "soft_hedge_router"
        else:  # strict_silence
            return "strict_silence_router"

    graph.add_conditional_edges(
        "confidence_scorer",
        after_confidence,
        {
            "review_queue_writer": "review_queue_writer",
            "stream_to_user": "stream_to_user",
            "soft_hedge_router": "soft_hedge_router",
            "strict_silence_router": "strict_silence_router",
        },
    )

    # soft_hedge_router → stream_to_user (always)
    graph.add_edge("soft_hedge_router", "stream_to_user")

    # strict_silence_router: review queue or stream (with silence message)
    def after_strict_silence(state: ConversationState) -> str:
        if profile.review_required:
            return "review_queue_writer"
        return "stream_to_user"

    graph.add_conditional_edges(
        "strict_silence_router",
        after_strict_silence,
        {
            "review_queue_writer": "review_queue_writer",
            "stream_to_user": "stream_to_user",
        },
    )

    # stream_to_user: memory writer (if enabled) or voice pipeline or end
    def after_stream(state: ConversationState) -> str:
        if profile.user_memory_enabled:
            return "memory_writer"
        if profile.voice_mode != VoiceMode.text_only:
            return "voice_pipeline"
        return "__end__"

    graph.add_conditional_edges(
        "stream_to_user",
        after_stream,
        {
            "memory_writer": "memory_writer",
            "voice_pipeline": "voice_pipeline",
            "__end__": "__end__",
        },
    )

    # memory_writer → voice pipeline or end (conditionally)
    def after_memory_write(state: ConversationState) -> str:
        if profile.voice_mode != VoiceMode.text_only:
            return "voice_pipeline"
        return "__end__"

    graph.add_conditional_edges(
        "memory_writer",
        after_memory_write,
        {
            "voice_pipeline": "voice_pipeline",
            "__end__": "__end__",
        },
    )

    # voice_pipeline → end (always)
    graph.add_edge("voice_pipeline", "__end__")

    # review_queue_writer → end (always)
    graph.add_edge("review_queue_writer", "__end__")

    # ========================================================================
    # COMPILE AND RETURN
    # ========================================================================

    return graph.compile()
