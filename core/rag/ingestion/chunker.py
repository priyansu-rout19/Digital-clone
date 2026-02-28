def chunk_text(
    blocks: list[str],
    min_tokens: int = 512,
    max_tokens: int = 1024,
    overlap_ratio: float = 0.15,
) -> list[str]:
    if not blocks:
        return []
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


def _estimate_tokens(text: str) -> int:
    word_count = len(text.split())
    return int(word_count * 1.3)


def _extract_tail(text: str, target_tokens: int) -> str:
    target_chars = int(target_tokens * 4.5)
    if len(text) <= target_chars:
        return text
    start_pos = len(text) - target_chars
    search_text = text[max(0, start_pos - 500) :]
    break_pos = search_text.rfind("\n\n")
    if break_pos != -1:
        actual_start = max(0, start_pos - 500) + break_pos + 2
        return text[actual_start:]
    else:
        search_text = text[:start_pos]
        break_pos = search_text.rfind("\n\n")
        if break_pos != -1:
            return text[break_pos + 2 :]
        else:
            return text[start_pos:]
