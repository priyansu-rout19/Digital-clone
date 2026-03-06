// Enums as string unions (mirrors core/models/clone_profile.py)
export type GenerationMode = 'interpretive' | 'mirror_only';
export type SilenceBehavior = 'soft_hedge' | 'strict_silence';
export type VoiceMode = 'ai_clone' | 'original_only' | 'text_only';
export type DeploymentMode = 'standard' | 'air_gapped';
export type RetrievalTier = 'vector' | 'tree_search';
export type AccessTier = 'public' | 'devotee' | 'friend' | 'follower';
export type ChunkingStrategy = 'fixed_size' | 'semantic';

// Clone profile (17 fields from clone_profile.py)
export interface CloneProfile {
  slug: string;
  display_name: string;
  bio: string;
  avatar_url: string;
  generation_mode: GenerationMode;
  confidence_threshold: number;
  silence_behavior: SilenceBehavior;
  silence_message: string;
  review_required: boolean;
  user_memory_enabled: boolean;
  voice_mode: VoiceMode;
  voice_model_ref: string | null;
  retrieval_tiers: RetrievalTier[];
  provenance_graph_enabled: boolean;
  access_tiers: AccessTier[];
  chunking_strategy: ChunkingStrategy;
  deployment_mode: DeploymentMode;
}

// Chat
export interface ChatRequest {
  query: string;
  user_id?: string;
  access_tier?: string;
}

export interface CitedSource {
  source: string;
  chunk_text: string;
  score: number;
  date?: string | null;
  location?: string | null;
  event?: string | null;
  verifier?: string | null;
  source_title?: string | null;
  doc_id?: string;
  chunk_id?: string;
  [key: string]: unknown;
}

export interface ChatResponse {
  response: string;
  confidence: number;
  cited_sources: CitedSource[];
  silence_triggered: boolean;
  audio_base64?: string | null;
  audio_format?: string | null;
}

// Reasoning trace record (per node in the pipeline)
export interface TraceRecord {
  node: string;
  intent?: string;
  sub_query_count?: number;
  response_tokens?: number;
  passage_count?: number;
  confidence?: number;
  reranked?: boolean;
  top_rerank_score?: number;
  retry_count?: number;
  new_queries?: number;
  context_chars?: number;
  has_history?: boolean;
  has_memory?: boolean;
  generated?: boolean;
  citation_count?: number;
  final_confidence?: number;
  silence_triggered?: boolean;
  has_audio?: boolean;
}

// WebSocket messages (discriminated union)
export interface WSProgressMessage {
  type: 'progress';
  node: string;
  trace?: TraceRecord;
}

export interface WSResponseMessage {
  type: 'response';
  response: string;
  confidence: number;
  cited_sources: CitedSource[];
  silence_triggered: boolean;
  suggested_topics?: string[];
  audio_base64?: string | null;
  audio_format?: string | null;
}

export interface WSErrorMessage {
  type: 'error';
  message: string;
}

export type WSMessage = WSProgressMessage | WSResponseMessage | WSErrorMessage;

// Review (Sacred Archive)
export interface ReviewItem {
  id: string;
  query_text: string;
  response_text: string;
  confidence_score: number | null;
  cited_sources?: CitedSource[];
  created_at: string;
}

export interface ReviewUpdate {
  action: 'approve' | 'reject' | 'edit';
  notes?: string;
  edited_response?: string;
}

export interface ReviewUpdateResponse {
  id: string;
  status: string;
  response_text?: string;
  reviewer_notes: string | null;
  reviewed_at: string | null;
}

// Analytics
export interface AnalyticsSummary {
  total_queries: number;
  avg_confidence: number | null;
  avg_latency_ms: number | null;
  silence_rate: number;
  queries_per_day: { date: string; count: number }[];
  top_intents: { intent: string; count: number }[];
}

// UI-side chat message model
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  confidence?: number;
  cited_sources?: CitedSource[];
  silence_triggered?: boolean;
  suggested_topics?: string[];
  audio_base64?: string;
  audio_format?: string;
  trace?: TraceRecord[];
}

// Shared node label mappings (single source of truth)
// Keys used by useChat for progress labels, ReasoningTrace for display names
export const NODE_LABELS: Record<string, string> = {
  query_analysis: 'Analyzing your question...',
  query_analyzer: 'Analyzing your question...',
  sub_query_generator: 'Breaking down the query...',
  tier1_retrieval: 'Searching knowledge base...',
  tier2_retrieval: 'Searching document tree...',
  tier2_tree_search: 'Searching document tree...',
  passage_merger: 'Merging results...',
  crag_evaluator: 'Evaluating relevance...',
  query_reformulator: 'Refining search...',
  provenance_graph_query: 'Looking up sources...',
  context_assembler: 'Assembling context...',
  conversation_history: 'Loading conversation...',
  memory_retrieval: 'Loading your preferences...',
  memory_injector: 'Loading your preferences...',
  in_persona_generator: 'Generating response...',
  response_generator: 'Generating response...',
  citation_verifier: 'Verifying accuracy...',
  verifier: 'Verifying accuracy...',
  confidence_scorer: 'Checking confidence...',
  silence_checker: 'Checking confidence...',
  soft_hedge_router: 'Checking confidence...',
  strict_silence_router: 'Checking confidence...',
  review_queue_writer: 'Routing response...',
  review_router: 'Routing response...',
  stream_to_user: 'Preparing output...',
  voice_pipeline: 'Generating voice...',
  voice_synth: 'Generating voice...',
  memory_writer: 'Saving memory...',
  provenance_lookup: 'Looking up sources...',
};

// Display names for ReasoningTrace timeline (short, noun-style)
export const NODE_DISPLAY_NAMES: Record<string, string> = {
  query_analysis: 'Query Analysis',
  query_analyzer: 'Query Analysis',
  tier1_retrieval: 'Vector Search',
  tier2_tree_search: 'Tree Search',
  tier2_retrieval: 'Tree Search',
  crag_evaluator: 'Relevance Check',
  query_reformulator: 'Query Reformulation',
  provenance_graph_query: 'Provenance Lookup',
  context_assembler: 'Context Assembly',
  conversation_history: 'Conversation History',
  memory_retrieval: 'Memory Retrieval',
  in_persona_generator: 'Response Generation',
  response_generator: 'Response Generation',
  citation_verifier: 'Citation Verification',
  verifier: 'Citation Verification',
  confidence_scorer: 'Confidence Scoring',
  soft_hedge_router: 'Low Confidence Hedge',
  strict_silence_router: 'Silence Triggered',
  review_queue_writer: 'Queued for Review',
  stream_to_user: 'Preparing Output',
  voice_pipeline: 'Voice Synthesis',
  memory_writer: 'Memory Update',
};
