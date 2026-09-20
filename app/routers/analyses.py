import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, Response, StreamingResponse

from app.config import get_settings
from app.schemas import Analysis, AnalysisStatus, Claim, CreatedAnalysis, Evidence, HealthResponse
from app.services.extract import extract_upload, extract_url, note_evidence
from app.services.pack import pdf_pack, render_pack
from app.services.pipeline import run_pipeline
from app.services.store import get, save

router = APIRouter(prefix="/api", tags=["analyses"])


def require(analysis_id: str) -> Analysis:
    analysis = get(analysis_id)
    if not analysis:
        raise HTTPException(
            404, detail={"error": {"code": "NOT_FOUND", "message": "Analysis not found"}}
        )
    return analysis


async def prepare_evidence(files: list[UploadFile], notes: str, urls: list[str]) -> list[Evidence]:
    if len(files) > 3:
        raise HTTPException(
            422,
            detail={
                "error": {
                    "code": "TOO_MANY_FILES",
                    "message": "Upload at most three evidence files",
                }
            },
        )
    evidence: list[Evidence] = []
    for upload in files:
        try:
            evidence.append(await extract_upload(upload))
        except ValueError as error:
            raise HTTPException(
                422, detail={"error": {"code": "INVALID_FILE", "message": str(error)}}
            ) from error
    note = note_evidence(notes)
    if note:
        evidence.append(note)
    for url in urls[:3]:
        try:
            evidence.append(await extract_url(url))
        except Exception:
            pass
    return evidence


@router.post("/analyses", response_model=CreatedAnalysis, status_code=202)
async def create_analysis(
    background_tasks: BackgroundTasks,
    doc_type: str = Form(...),
    draft_text: str = Form(""),
    notes: str = Form(""),
    urls: list[str] = Form(default=[]),
    files: list[UploadFile] = File(default=[]),
):
    evidence = await prepare_evidence(files, notes, urls)
    if not draft_text.strip() and not evidence:
        raise HTTPException(
            422,
            detail={
                "error": {
                    "code": "MISSING_INPUT",
                    "message": "Provide a draft or at least one evidence source",
                }
            },
        )
    # An uploaded PDF, DOCX, note, or URL can stand alone as the work sample.
    # Its extracted text becomes the claim-extraction source when no draft is pasted.
    source_text = draft_text.strip() or "\n\n".join(
        item.extracted_text for item in evidence if item.extracted_text.strip()
    )
    if not source_text.strip():
        raise HTTPException(
            422,
            detail={
                "error": {
                    "code": "NO_EXTRACTABLE_TEXT",
                    "message": "No readable text was found in the supplied evidence",
                }
            },
        )
    analysis = Analysis(
        id=str(uuid4()),
        status=AnalysisStatus.queued,
        doc_type=doc_type,
        draft_text=source_text,
        notes=notes,
        urls=urls,
        evidence=evidence,
    )
    save(analysis)
    background_tasks.add_task(run_pipeline, analysis)
    return CreatedAnalysis(id=analysis.id, status=analysis.status)


@router.get("/analyses/{analysis_id}", response_model=Analysis)
async def get_analysis(analysis_id: str):
    return require(analysis_id)


@router.get("/analyses/{analysis_id}/events")
async def events(analysis_id: str):
    require(analysis_id)

    async def stream():
        sent = 0
        while True:
            analysis = require(analysis_id)
            while sent < len(analysis.progress):
                yield f"event: progress\ndata: {analysis.progress[sent].model_dump_json()}\n\n"
                sent += 1
            if analysis.status in {AnalysisStatus.complete, AnalysisStatus.failed}:
                yield f"event: complete\ndata: {json.dumps({'status': analysis.status})}\n\n"
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/analyses/{analysis_id}/claims/{claim_id}/accept-rewrite",
    response_model=Claim,
)
async def accept_rewrite(analysis_id: str, claim_id: str):
    analysis = require(analysis_id)
    if not analysis.result:
        raise HTTPException(
            409, detail={"error": {"code": "NOT_READY", "message": "Analysis is not complete"}}
        )
    claim = next((claim for claim in analysis.result.claims if claim.id == claim_id), None)
    if not claim:
        raise HTTPException(
            404, detail={"error": {"code": "CLAIM_NOT_FOUND", "message": "Claim not found"}}
        )
    claim.accepted_rewrite = claim.safe_rewrite
    save(analysis)
    return claim


@router.get("/analyses/{analysis_id}/evidence-pack")
async def evidence_pack(analysis_id: str, include_notes: bool = Query(False)):
    analysis = require(analysis_id)
    if not analysis.result:
        raise HTTPException(
            409, detail={"error": {"code": "NOT_READY", "message": "Analysis is not complete"}}
        )
    try:
        document = pdf_pack(analysis, include_notes)
    except OSError as error:
        raise HTTPException(
            503,
            detail={
                "error": {
                    "code": "PDF_UNAVAILABLE",
                    "message": "PDF rendering dependencies are not installed on this host",
                }
            },
        ) from error
    return Response(
        document,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="tether-evidence-pack-{analysis.id}.pdf"'
        },
    )


@router.get("/analyses/{analysis_id}/evidence-pack/preview", response_class=HTMLResponse)
async def pack_preview(analysis_id: str, include_notes: bool = Query(False)):
    analysis = require(analysis_id)
    if not analysis.result:
        raise HTTPException(
            409, detail={"error": {"code": "NOT_READY", "message": "Analysis is not complete"}}
        )
    return render_pack(analysis, include_notes)


@router.post("/demo", response_model=CreatedAnalysis, status_code=202)
async def demo(background_tasks: BackgroundTasks):
    draft = "I led a team of 12 students to build a recycling app. We raised $3,000 for the robotics club, reduced plastic waste by 40%, and built an app used by 500 students. Contact me at 555-123-4567."
    evidence = [
        Evidence(
            id="advisor-letter",
            file_name="Advisor Letter.pdf",
            type="pdf",
            extracted_text="I confirm that the student led a 12-student team during the recycling-app project.",
            snippets=[],
        ),
        Evidence(
            id="fundraiser",
            file_name="Campaign Dashboard.pdf",
            type="pdf",
            extracted_text="Robotics Club Spring Fundraiser. Total donations: $2,847.",
            snippets=[],
        ),
    ]
    from app.services.chunk import chunk_text

    for item in evidence:
        item.snippets = chunk_text(item.extracted_text, item.id, item.file_name, page=1)
    analysis = Analysis(
        id=str(uuid4()),
        status=AnalysisStatus.queued,
        doc_type="project_proposal",
        draft_text=draft,
        evidence=evidence,
    )
    save(analysis)
    background_tasks.add_task(run_pipeline, analysis)
    return CreatedAnalysis(id=analysis.id, status=analysis.status)


@router.get("/health", response_model=HealthResponse)
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "provider": "ollama",
        "nemotron": "mock"
        if settings.mock_mode
        else ("configured" if settings.provider_api_key else "unconfigured"),
        "model": settings.nemotron_model,
    }
