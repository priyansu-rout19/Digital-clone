"""
Clone Profile Config Model

A Pydantic model defining the configuration for a digital clone. Stored in PostgreSQL
as a JSONB column (clones.profile). Read by LangGraph at every request to feature-gate
all behavioral differences between clients (ParaGPT vs Sacred Archive).

One unified codebase, zero code branches — everything is driven by this config.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class GenerationMode(str, Enum):
    """Controls whether the LLM synthesizes and applies frameworks (interpretive)
    or constructs responses from direct quotes only (mirror_only)."""
    interpretive = "interpretive"
    mirror_only = "mirror_only"


class SilenceBehavior(str, Enum):
    """Defines what happens when confidence falls below threshold."""
    soft_hedge = "soft_hedge"  # LLM generates a hedged response
    strict_silence = "strict_silence"  # Response queued for human review


class VoiceMode(str, Enum):
    """Defines how audio output is handled."""
    ai_clone = "ai_clone"  # TTS via trained OpenAudio voice model
    original_only = "original_only"  # Link to original recordings by provenance
    text_only = "text_only"  # No audio output


class DeploymentMode(str, Enum):
    """Infrastructure deployment model."""
    standard = "standard"  # Connected to network, can use external APIs
    air_gapped = "air_gapped"  # Zero external calls, all models pre-installed


class RetrievalTier(str, Enum):
    """Defines which retrieval stages are enabled."""
    vector = "vector"  # Tier 1: Vector search (always runs)
    tree_search = "tree_search"  # Tier 2: PageIndex hierarchical navigation


class AccessTier(str, Enum):
    """Content access tiers for Sacred Archive (ParaGPT uses only 'public')."""
    public = "public"
    devotee = "devotee"
    friend = "friend"
    follower = "follower"


class ChunkingStrategy(str, Enum):
    """Controls how documents are split into chunks during ingestion.
    fixed_size: paragraph-aware token counting (original).
    semantic: embedding-based topic boundary detection (uses Google Gemini embeddings)."""
    fixed_size = "fixed_size"
    semantic = "semantic"



# CLONE PROFILE MODEL

class CloneProfile(BaseModel):
    """
    Complete configuration for a digital clone.

    Stores identity, generation behavior, retrieval strategy, voice settings,
    access control, and infrastructure mode. Every field controls pipeline behavior
    via runtime checks in LangGraph nodes.
    """

    # Identity & UI
    slug: str = Field(max_length=64, description="URL identifier (e.g. 'paragpt-client')")
    display_name: str = Field(description="Display name shown on chat page")
    bio: str = Field(description="Bio text shown below avatar")
    avatar_url: str = Field(description="Path to avatar image")

    # Generation behavior
    generation_mode: GenerationMode = Field(description="interpretive=synthesis, mirror_only=quotes only")
    confidence_threshold: float = Field(
        ge=0.0, le=1.0,
        description="Score below this triggers silence behavior (0.0-1.0)"
    )
    silence_behavior: SilenceBehavior = Field(
        description="soft_hedge=hedged response, strict_silence=queue for review"
    )
    silence_message: str = Field(
        description="Fallback text when silence is triggered"
    )

    # Review & quality control
    review_required: bool = Field(
        description="true=all responses go to review queue, false=stream high-confidence responses"
    )

    # User memory & personalization
    user_memory_enabled: bool = Field(
        description="true=inject Mem0 cross-session memory, false=each session independent"
    )

    # Voice & audio
    voice_mode: VoiceMode = Field(description="ai_clone=TTS, original_only=recorded audio, text_only=no audio")
    voice_model_ref: Optional[str] = Field(
        default=None,
        description="Reference to trained voice model (required if voice_mode='ai_clone')"
    )

    # Retrieval strategy
    retrieval_tiers: list[RetrievalTier] = Field(
        min_length=1,
        description="['vector'] or ['vector', 'tree_search']"
    )

    # Provenance & access
    provenance_graph_enabled: bool = Field(
        description="true=run Apache AGE Cypher queries, false=vector search only"
    )
    access_tiers: list[AccessTier] = Field(
        min_length=1,
        description="Which content tiers this clone can access"
    )

    # Ingestion behavior
    chunking_strategy: ChunkingStrategy = Field(
        default=ChunkingStrategy.semantic,
        description="fixed_size=paragraph-aware token counting, semantic=embedding-based topic boundaries"
    )

    # Infrastructure
    deployment_mode: DeploymentMode = Field(
        description="standard=network connected, air_gapped=zero external calls"
    )

    @model_validator(mode="after")
    def validate_voice_model_ref(self) -> "CloneProfile":
        """voice_model_ref required if voice_mode is ai_clone, must be None otherwise."""
        if self.voice_mode == VoiceMode.ai_clone and self.voice_model_ref is None:
            raise ValueError(
                "voice_model_ref is required when voice_mode is 'ai_clone'"
            )
        if self.voice_mode != VoiceMode.ai_clone and self.voice_model_ref is not None:
            raise ValueError(
                "voice_model_ref must be None when voice_mode is not 'ai_clone'"
            )
        return self


# PRESET FACTORY FUNCTIONS

def paragpt_profile() -> CloneProfile:
    """
    ParaGPT preset: Interpretive, voice-enabled, public access, standard deployment.

    Parag Khanna's digital clone — synthesizes frameworks, references past work,
    responds with confidence. User memory enabled. Direct streaming (no review).
    """
    return CloneProfile(
        slug="paragpt-client",
        display_name="Parag Khanna",
        bio="Author, geopolitical strategist known for synthesizing complex global trends into accessible frameworks. "
            "Data-driven analysis connecting history, economics, and geography.",
        avatar_url="/avatars/parag-khanna.png",
        generation_mode=GenerationMode.interpretive,
        confidence_threshold=0.80,
        silence_behavior=SilenceBehavior.soft_hedge,
        silence_message="I don't have a specific teaching on that topic. "
                        "Feel free to ask about my work on geopolitics, connectivity, or strategic thinking.",
        review_required=False,
        user_memory_enabled=True,
        voice_mode=VoiceMode.ai_clone,
        voice_model_ref="voice_pk_v1",
        retrieval_tiers=[RetrievalTier.vector],
        provenance_graph_enabled=False,
        access_tiers=[AccessTier.public],
        chunking_strategy=ChunkingStrategy.semantic,
        deployment_mode=DeploymentMode.standard,
    )


def sacred_archive_profile() -> CloneProfile:
    """
    Sacred Archive preset: Mirror-only, original recordings, tiered access, air-gapped.

    Direct quotes only — no synthesis, no paraphrasing. All responses queued for
    human review before serving. User memory disabled. Provenance and access
    control strict. Air-gapped deployment.
    """
    return CloneProfile(
        slug="sacred-archive",
        display_name="Sacred Teachings",
        bio="Mirror of timeless wisdom, curated with reverence and scholarly care. "
            "Direct teachings, unaltered and verified.",
        avatar_url="/static/avatars/sacred-archive.jpg",
        generation_mode=GenerationMode.mirror_only,
        confidence_threshold=0.95,
        silence_behavior=SilenceBehavior.strict_silence,
        silence_message="This question falls outside the verified teachings in our archive. "
                        "We honor the tradition by remaining silent rather than speculating. "
                        "Please consult a senior guide, or explore related topics within the archive.",
        review_required=True,
        user_memory_enabled=False,
        voice_mode=VoiceMode.original_only,
        voice_model_ref=None,
        retrieval_tiers=[RetrievalTier.vector, RetrievalTier.tree_search],
        provenance_graph_enabled=True,
        access_tiers=[AccessTier.devotee, AccessTier.friend, AccessTier.follower],
        chunking_strategy=ChunkingStrategy.semantic,
        deployment_mode=DeploymentMode.air_gapped,
    )
