import logging
import os
from pathlib import Path

import fitz
from groq import Groq

logger = logging.getLogger(__name__)

AUDIO_VIDEO_FORMATS = {".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".flac", ".aac"}
MAX_AUDIO_SIZE_MB = 25  # Groq Whisper file size limit


def parse(file_path: str) -> list[str]:
    path = Path(file_path)
    extension = path.suffix.lower()
    if extension in AUDIO_VIDEO_FORMATS:
        return _parse_audio(file_path)
    if extension not in {".pdf", ".txt", ".md", ".markdown"}:
        raise ValueError(f"Unsupported file type: {extension}")
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if extension == ".pdf":
        return _parse_pdf(file_path)
    if extension in {".txt", ".md", ".markdown"}:
        return _parse_text(file_path)


def _parse_audio(file_path: str) -> list[str]:
    """
    Transcribe audio/video files using Groq's Whisper Large v3 Turbo API.

    Groq provides Whisper at 216x real-time speed. Uses the existing
    GROQ_API_KEY (same key as the LLM). Returns transcript split into
    paragraph-sized blocks for the chunker pipeline.

    Supported: .mp3, .wav, .m4a, .mp4, .avi, .mov, .flac, .aac
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY required for audio transcription. Set it in .env file.")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_AUDIO_SIZE_MB:
        raise ValueError(
            f"Audio file too large ({file_size_mb:.1f}MB). "
            f"Groq Whisper limit is {MAX_AUDIO_SIZE_MB}MB. Split the file first."
        )

    logger.info(f"Transcribing {path.name} ({file_size_mb:.1f}MB) via Groq Whisper...")

    client = Groq(api_key=api_key)
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=(path.name, audio_file.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
        )

    full_text = transcription.text
    if not full_text or not full_text.strip():
        logger.warning(f"Whisper returned empty transcript for {path.name}")
        return []

    logger.info(f"Transcribed {len(full_text)} chars from {path.name}")

    # Split transcript into paragraph-sized blocks.
    # Whisper often returns one continuous block — split into ~500-char chunks
    # at sentence boundaries so the chunker can work effectively.
    blocks = []
    paragraphs = full_text.split("\n\n")
    for paragraph in paragraphs:
        cleaned = paragraph.strip()
        if len(cleaned) >= 20:
            blocks.append(cleaned)

    # If Whisper returned one long block (common for audio), split on sentences
    if len(blocks) <= 1 and len(full_text) > 500:
        blocks = []
        sentences = full_text.replace(". ", ".\n").split("\n")
        current_block = ""
        for sentence in sentences:
            if len(current_block) + len(sentence) > 500 and len(current_block) >= 20:
                blocks.append(current_block.strip())
                current_block = sentence
            else:
                current_block += " " + sentence if current_block else sentence
        if current_block.strip() and len(current_block.strip()) >= 20:
            blocks.append(current_block.strip())

    return blocks if blocks else [full_text.strip()] if full_text.strip() else []


def _parse_pdf(file_path: str) -> list[str]:
    doc = fitz.open(file_path)
    blocks = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        paragraphs = text.split("\n\n")
        for paragraph in paragraphs:
            cleaned = paragraph.strip()
            if len(cleaned) >= 20:
                blocks.append(cleaned)
    doc.close()
    return blocks


def _parse_text(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    paragraphs = text.split("\n\n")
    blocks = []
    for paragraph in paragraphs:
        cleaned = paragraph.strip()
        if len(cleaned) >= 20:
            blocks.append(cleaned)
    return blocks
