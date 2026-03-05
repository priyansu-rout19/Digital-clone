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

// WebSocket messages (discriminated union)
export interface WSProgressMessage {
  type: 'progress';
  node: string;
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
  created_at: string;
}

export interface ReviewUpdate {
  action: 'approve' | 'reject';
  notes?: string;
}

export interface ReviewUpdateResponse {
  id: string;
  status: string;
  reviewer_notes: string | null;
  reviewed_at: string | null;
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
}
