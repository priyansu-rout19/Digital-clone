import logging
from typing import Optional

from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


def chunk_text(
    blocks: list[str],
    strategy: str = "semantic",
    embeddings: Optional[Embeddings] = None,
    breakpoint_threshold_type: str = "percentile",
    breakpoint_threshold_amount: float = 85,
    min_chunk_chars: int = 200,
    max_chunk_tokens: int = 1024,
    min_tokens: int = 512,
    max_tokens: int = 1024,
    overlap_ratio: float = 0.15,
) -> list[str]:
    if not blocks:
        return []

    if strategy == "semantic":
        if embeddings is None:
            raise ValueError(
                "Embeddings instance required for semantic chunking. "
                "Pass embeddings= or use strategy='fixed_size'."
            )
        return _semantic_chunk(
            blocks,
            embeddings=embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
            min_chunk_chars=min_chunk_chars,
            max_chunk_tokens=max_chunk_tokens,
        )
    elif strategy == "fixed_size":
        return _fixed_size_chunk(blocks, min_tokens, max_tokens, overlap_ratio)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")


# --- Semantic Chunking (NEW) ---

def _semantic_chunk(
    blocks: list[str],
    embeddings: Embeddings,
    breakpoint_threshold_type: str,
    breakpoint_threshold_amount: float,
    min_chunk_chars: int,
    max_chunk_tokens: int,
) -> list[str]:
    full_text = "\n\n".join(blocks)

    chunker = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type=breakpoint_threshold_type,
        breakpoint_threshold_amount=breakpoint_threshold_amount,
        min_chunk_size=min_chunk_chars,
    )

    raw_chunks = chunker.split_text(full_text)
    logger.info(f"SemanticChunker produced {len(raw_chunks)} raw chunks")

    final_chunks = _enforce_max_size(raw_chunks, max_chunk_tokens)
    logger.info(f"After max-size enforcement: {len(final_chunks)} chunks")
    return final_chunks


def _enforce_max_size(chunks: list[str], max_tokens: int) -> list[str]:
    max_chars = int(max_tokens * 4.5)
    result = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chars,
        chunk_overlap=0,
        separators=["\n\n", "\n", ". ", " "],
    )

    for chunk in chunks:
        if _estimate_tokens(chunk) > max_tokens:
            sub_chunks = splitter.split_text(chunk)
            result.extend(sub_chunks)
        else:
            result.append(chunk)

    return result


# --- Fixed-Size Chunking (ORIGINAL — preserved as fallback) ---

def _fixed_size_chunk(
    blocks: list[str],
    min_tokens: int = 512,
    max_tokens: int = 1024,
    overlap_ratio: float = 0.15,
) -> list[str]:
    current_chunk = ""
    chunks = []
    for block in blocks:
        if current_chunk:
            current_chunk += "\n\n" + block
        else:
            current_chunk = block
        current_tokens = _estimate_tokens(current_chunk)
        if current_tokens >= min_tokens:
            chunks.append(current_chunk)
            overlap_tokens = int(current_tokens * overlap_ratio)
            current_chunk = _extract_tail(current_chunk, overlap_tokens)
    if current_chunk.strip():
        chunks.append(current_chunk)
    return chunks


# --- Shared Helpers ---

def _estimate_tokens(text: str) -> int:
    word_count = len(text.split())
    return int(word_count * 1.3)


def _extract_tail(text: str, target_tokens: int) -> str:
    target_chars = int(target_tokens * 4.5)
    if len(text) <= target_chars:
        return text
    start_pos = len(text) - target_chars
    search_text = text[max(0, start_pos - 500):]
    break_pos = search_text.rfind("\n\n")
    if break_pos != -1:
        actual_start = max(0, start_pos - 500) + break_pos + 2
        return text[actual_start:]
    else:
        search_text = text[:start_pos]
        break_pos = search_text.rfind("\n\n")
        if break_pos != -1:
            return text[break_pos + 2:]
        else:
            return text[start_pos:]
