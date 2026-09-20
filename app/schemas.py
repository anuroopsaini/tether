from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ClaimCategory(str, Enum):
    measurable = "measurable"
    subjective = "subjective"
    sensitive = "sensitive"
    unverifiable = "unverifiable"
    potentially_misleading = "potentially_misleading"


class Verdict(str, Enum):
    publish = "publish"
    soften = "soften"
    needs_evidence = "needs_evidence"
    remove_sensitive_data = "remove_sensitive_data"


class AnalysisStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class EvidenceSnippet(BaseModel):
    id: str
    text: str
    file_name: str
    page: int | None = None
    source_type: Literal["file", "url", "note"] = "file"


class Evidence(BaseModel):
    id: str
    file_name: str
    type: Literal["pdf", "docx", "txt", "image", "url", "note"]
    extracted_text: str = ""
    snippets: list[EvidenceSnippet] = Field(default_factory=list)


class ExtractedClaim(BaseModel):
    claim: str
    claim_type: ClaimCategory
    source_quote: str


class Claim(BaseModel):
    id: str
    text: str
    source_quote: str = ""
    category: ClaimCategory
    verdict: Verdict
    color: Literal["green", "yellow", "red", "purple"]
    action: str
    confidence: float = Field(ge=0, le=1)
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list)
    evidence_match: str
    missing_proof: list[str] = Field(default_factory=list)
    risk: str
    safe_rewrite: str
    rewrite_options: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    accepted_rewrite: str | None = None
    user_feedback: Literal["verified_by_student", "disagrees"] | None = None
    privacy_flags: list[str] = Field(default_factory=list)
    provenance_note: str = ""
    degraded: bool = False


class ProgressEvent(BaseModel):
    step: str
    message: str
    current: int | None = None
    total: int | None = None
    at: datetime = Field(default_factory=datetime.utcnow)


class Summary(BaseModel):
    trust_score: int = Field(ge=0, le=100)
    claims_reviewed: int
    evidence_backed: int
    needing_changes: int
    privacy_flags: int
    support_range: Literal["strong", "mixed", "limited"] = "limited"


class AnalysisResult(BaseModel):
    summary: Summary
    claims: list[Claim]
    contradictions: list[str] = Field(default_factory=list)
    privacy_flags: list[str] = Field(default_factory=list)
    skipped_statements: list[str] = Field(default_factory=list)


class Analysis(BaseModel):
    id: str
    status: AnalysisStatus
    doc_type: str
    draft_text: str
    notes: str = ""
    urls: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    progress: list[ProgressEvent] = Field(default_factory=list)
    result: AnalysisResult | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreatedAnalysis(BaseModel):
    id: str
    status: AnalysisStatus


class ClaimFeedback(BaseModel):
    choice: Literal["verified_by_student", "disagrees"]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ok"]
    provider: str
    nemotron: Literal["mock", "configured", "unconfigured"]
    model: str


class ClaimJudgment(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_match: str
    missing_proof: list[str] = Field(default_factory=list)
    risk: str
    safe_rewrite: str
    rewrite_options: list[str] = Field(default_factory=list)
    privacy_flags: list[str] = Field(default_factory=list)
    provenance_note: str = ""


class ContradictionResponse(BaseModel):
    contradictions: list[str] = Field(default_factory=list)
