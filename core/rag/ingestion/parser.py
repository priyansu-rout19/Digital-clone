import fitz
from pathlib import Path


def parse(file_path: str) -> list[str]:
    path = Path(file_path)
    extension = path.suffix.lower()
    audio_video_formats = {".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".flac", ".aac"}
    if extension in audio_video_formats:
        raise NotImplementedError(
            "Audio/video parsing requires Whisper integration (future work)"
        )
    if extension not in {".pdf", ".txt", ".md", ".markdown"}:
        raise ValueError(f"Unsupported file type: {extension}")
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if extension == ".pdf":
        return _parse_pdf(file_path)
    if extension in {".txt", ".md", ".markdown"}:
        return _parse_text(file_path)


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
