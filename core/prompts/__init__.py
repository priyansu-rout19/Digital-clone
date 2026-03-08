"""Re-exports all prompts for clean imports: `from core.prompts import QUERY_CLASSIFIER_PROMPT`"""

from core.prompts.registry import (
    QUERY_CLASSIFIER_PROMPT,
    CRAG_REFORMULATOR_PROMPT,
    interpretive_generator_prompt,
    mirror_only_generator_prompt,
    SENTENCE_SPLITTER_PROMPT,
)

__all__ = [
    "QUERY_CLASSIFIER_PROMPT",
    "CRAG_REFORMULATOR_PROMPT",
    "interpretive_generator_prompt",
    "mirror_only_generator_prompt",
    "SENTENCE_SPLITTER_PROMPT",
]
