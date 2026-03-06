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
  audio_base64?: string;
  audio_format?: string;
  trace?: TraceRecord[];
}
