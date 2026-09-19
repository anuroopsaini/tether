import re

from app.schemas import EvidenceSnippet


def chunk_text(
    text: str, evidence_id: str, file_name: str, source_type: str = "file", page: int | None = None
) -> list[EvidenceSnippet]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks, buffer = [], ""
    for sentence in sentences:
        if buffer and len(buffer) + len(sentence) + 1 > 600:
            chunks.append(buffer.strip())
            buffer = sentence
        else:
            buffer += " " + sentence
    if buffer.strip():
        chunks.append(buffer.strip())
    if not chunks and text.strip():
        chunks = [text.strip()[:600]]
    return [
        EvidenceSnippet(
            id=f"{evidence_id}-s{i + 1}",
            text=value,
            file_name=file_name,
            page=page,
            source_type=source_type,
        )
        for i, value in enumerate(chunks)
    ]
