import io
import mimetypes
from pathlib import Path
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup
from docx import Document
from fastapi import UploadFile
from pypdf import PdfReader

from app.config import get_settings
from app.schemas import Evidence
from app.services.chunk import chunk_text


async def extract_upload(upload: UploadFile) -> Evidence:
    raw = await upload.read()
    if len(raw) > get_settings().max_file_size_mb * 1024 * 1024:
        raise ValueError(f"{upload.filename} exceeds the file-size limit")
    name = Path(upload.filename or "evidence").name
    mime = upload.content_type or mimetypes.guess_type(name)[0] or ""
    evidence_id = str(uuid4())
    if mime == "application/pdf" or name.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages)
        snippets = [
            s
            for number, page in enumerate(pages, 1)
            for s in chunk_text(page, evidence_id, name, page=number)
        ]
        kind = "pdf"
    elif "wordprocessingml" in mime or name.lower().endswith(".docx"):
        text = "\n".join(p.text for p in Document(io.BytesIO(raw)).paragraphs)
        kind = "docx"
        snippets = chunk_text(text, evidence_id, name)
    elif mime.startswith("text/") or name.lower().endswith(".txt"):
        text = raw.decode("utf-8", errors="replace")
        kind = "txt"
        snippets = chunk_text(text, evidence_id, name)
    elif mime.startswith("image/"):
        try:
            import pytesseract
            from PIL import Image

            text = pytesseract.image_to_string(Image.open(io.BytesIO(raw)))
        except ImportError as exc:
            raise ValueError("Image OCR requires the optional OCR dependencies") from exc
        kind = "image"
        snippets = chunk_text(text, evidence_id, name)
    else:
        raise ValueError(f"Unsupported evidence format: {name}")
    return Evidence(
        id=evidence_id, file_name=name, type=kind, extracted_text=text, snippets=snippets
    )


async def extract_url(url: str) -> Evidence:
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(" ", strip=True)[:20000]
    evidence_id = str(uuid4())
    return Evidence(
        id=evidence_id,
        file_name=url,
        type="url",
        extracted_text=text,
        snippets=chunk_text(text, evidence_id, url, "url"),
    )


def note_evidence(notes: str) -> Evidence | None:
    if not notes.strip():
        return None
    evidence_id = str(uuid4())
    return Evidence(
        id=evidence_id,
        file_name="Student notes",
        type="note",
        extracted_text=notes,
        snippets=chunk_text(notes, evidence_id, "Student notes", "note"),
    )
