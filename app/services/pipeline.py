import asyncio
import re
from uuid import uuid4

from app.config import get_settings
from app.schemas import (
    Analysis,
    AnalysisResult,
    AnalysisStatus,
    Claim,
    ClaimCategory,
    ClaimJudgment,
    ExtractedClaim,
    Verdict,
)
from app.services.match import top_matches
from app.services.nemotron import LLMFailure, extract_claims, find_contradictions, judge_claim
from app.services.privacy import find_pii, redact_pii
from app.services.scoring import ACTION_BY_VERDICT, COLOR_BY_VERDICT, summarize
from app.services.store import progress, save


def heuristic_claims(text: str) -> list[ExtractedClaim]:
    normalized = re.sub(
        r"\s+and\s+(?=(?:we\s+)?(?:raised|reduced|built|led|created|organized)\b)",
        ". ",
        text,
        flags=re.IGNORECASE,
    )
    sentences = re.split(r"(?<=[.!?])\s+", normalized.strip())
    chosen = [
        s
        for s in sentences
        if re.search(
            r"\$|\d+%|\b\d+\b|led|built|raised|reduced|created|organized|@|\d{3}[-. ]?\d{3}",
            s,
            re.IGNORECASE,
        )
    ][:10]
    return [
        ExtractedClaim(
            claim=s,
            claim_type=ClaimCategory.measurable
            if re.search(r"\d|\$|%", s)
            else ClaimCategory.unverifiable,
            source_quote=s,
        )
        for s in chosen
    ]


def mock_judgment(claim: ExtractedClaim, snippets: list) -> ClaimJudgment:
    lower = claim.claim.lower()
    has = bool(snippets)
    if "phone" in lower or "@" in lower:
        return ClaimJudgment(
            verdict=Verdict.remove_sensitive_data,
            confidence=0.95,
            evidence_match="Personal contact information should not be included in public materials.",
            risk="Exposes personal data.",
            safe_rewrite="Remove personal contact details before sharing.",
            privacy_flags=["Personal contact information"],
        )
    if "3,000" in lower:
        return ClaimJudgment(
            verdict=Verdict.soften,
            confidence=0.78,
            evidence_ids=[snippets[0].id] if has else [],
            evidence_match="The campaign dashboard supports $2,847, not $3,000.",
            missing_proof=["Final receipt confirming $3,000"],
            risk="Rounded total may appear inflated.",
            safe_rewrite="Raised nearly $2,850 for the robotics club.",
            provenance_note="Campaign dashboard supplied by student.",
        )
    if "40%" in lower:
        return ClaimJudgment(
            verdict=Verdict.needs_evidence,
            confidence=0.31,
            evidence_match="No baseline measurement or waste audit was supplied.",
            missing_proof=["Before-and-after waste audit"],
            risk="The percentage is unsupported.",
            safe_rewrite="Helped launch a campus plastic-waste reduction initiative.",
        )
    if "500" in lower:
        return ClaimJudgment(
            verdict=Verdict.needs_evidence,
            confidence=0.42,
            evidence_match="No usage analytics or school confirmation found.",
            missing_proof=["Usage analytics or school letter"],
            risk="May read as inflated.",
            safe_rewrite="Built an app piloted with students at my school.",
        )
    if "12" in lower:
        return ClaimJudgment(
            verdict=Verdict.publish,
            confidence=0.91,
            evidence_ids=[snippets[0].id] if has else [],
            evidence_match="The advisor letter confirms a 12-student team.",
            risk="",
            safe_rewrite=claim.claim,
            provenance_note="Advisor letter supplied by student.",
        )
    return ClaimJudgment(
        verdict=Verdict.publish if has else Verdict.needs_evidence,
        confidence=0.8 if has else 0.3,
        evidence_ids=[snippets[0].id] if has else [],
        evidence_match="A relevant evidence excerpt was found."
        if has
        else "No supporting evidence was supplied.",
        risk="" if has else "Claim is not independently supported.",
        safe_rewrite=claim.claim,
    )


def next_steps_for(verdict: Verdict, claim: str) -> list[str]:
    """Give students an actionable route to stronger proof, not a dead end."""
    lower = claim.lower()
    if verdict == Verdict.remove_sensitive_data:
        return ["Remove personal contact details before sharing this document."]
    if verdict == Verdict.publish:
        return ["Keep the source available as a student-provided supporting record."]
    steps = ["Ask an advisor or supervisor for a one-line confirmation email."]
    if "$" in claim or "raised" in lower:
        steps.insert(0, "Add a screenshot or receipt showing the final fundraiser total.")
    elif "app" in lower or "user" in lower:
        steps.insert(0, "Export an analytics page or ask your school for a usage confirmation.")
    elif "%" in claim or "reduced" in lower:
        steps.insert(0, "Add a before-and-after measurement or a short audit summary.")
    else:
        steps.insert(0, "Attach a dated document, link, or photo that supports this exact wording.")
    return steps[:2]


def narrative_skips(text: str, claims: list[ExtractedClaim]) -> list[str]:
    claim_quotes = {claim.source_quote for claim in claims}
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [
        sentence
        for sentence in sentences
        if sentence and sentence not in claim_quotes and not re.search(r"\d|\$|%", sentence)
    ][:8]


async def run_pipeline(analysis: Analysis) -> None:
    try:
        analysis.status = AnalysisStatus.processing
        save(analysis)
        progress(analysis, "extracting", "Finding factual claims while leaving personal narrative alone")
        settings = get_settings()
        model_draft = redact_pii(analysis.draft_text)
        try:
            extracted = (
                heuristic_claims(analysis.draft_text)
                if settings.mock_mode
                else await extract_claims(model_draft)
            )
        except LLMFailure:
            extracted = heuristic_claims(analysis.draft_text)
        if not extracted:
            extracted = heuristic_claims(analysis.draft_text)
        all_snippets = [snippet for evidence in analysis.evidence for snippet in evidence.snippets]
        progress(analysis, "matching", "Matching claims to supplied evidence")
        claims: list[Claim] = []
        semaphore = asyncio.Semaphore(4)

        async def process(item: tuple[int, ExtractedClaim]):
            index, extracted_claim = item
            candidates = top_matches(extracted_claim.claim, all_snippets)
            progress(
                analysis,
                "judging",
                f"Nemotron is evaluating claim {index}/{len(extracted)}",
                index,
                len(extracted),
            )
            degraded = False
            try:
                async with semaphore:
                    judgment = (
                        mock_judgment(extracted_claim, candidates)
                        if settings.mock_mode
                        else await judge_claim(
                            ExtractedClaim(
                                claim=redact_pii(extracted_claim.claim),
                                claim_type=extracted_claim.claim_type,
                                source_quote=redact_pii(extracted_claim.source_quote),
                            ),
                            [{**s.model_dump(), "text": redact_pii(s.text)} for s in candidates],
                        )
                    )
            except Exception:
                judgment = ClaimJudgment(
                    verdict=Verdict.needs_evidence,
                    confidence=0.1,
                    evidence_match="Judgment service was unavailable; this claim needs review.",
                    risk="Could not verify support.",
                    safe_rewrite=extracted_claim.claim,
                )
                degraded = True
            valid = {s.id: s for s in candidates}
            matched = [valid[i] for i in judgment.evidence_ids if i in valid]
            if judgment.verdict == Verdict.publish and not matched:
                judgment.verdict = Verdict.needs_evidence
                judgment.risk = "No validated evidence link was returned."
                judgment.evidence_match = "No validated evidence was found."
            pii = find_pii(extracted_claim.claim)
            if pii:
                judgment.verdict = Verdict.remove_sensitive_data
                judgment.privacy_flags = list(set(judgment.privacy_flags + pii))
            return Claim(
                id=str(uuid4()),
                text=extracted_claim.claim,
                source_quote=extracted_claim.source_quote,
                category=extracted_claim.claim_type,
                verdict=judgment.verdict,
                color=COLOR_BY_VERDICT[judgment.verdict],
                action=ACTION_BY_VERDICT[judgment.verdict],
                confidence=judgment.confidence,
                evidence_snippets=matched,
                evidence_match=judgment.evidence_match,
                missing_proof=judgment.missing_proof,
                risk=judgment.risk,
                safe_rewrite=judgment.safe_rewrite,
                rewrite_options=judgment.rewrite_options
                or [judgment.safe_rewrite, f"I contributed to {extracted_claim.claim.lstrip('I ').lower()}"],
                next_steps=next_steps_for(judgment.verdict, extracted_claim.claim),
                privacy_flags=judgment.privacy_flags,
                provenance_note=judgment.provenance_note,
                degraded=degraded,
            )

        claims = list(await asyncio.gather(*(process(pair) for pair in enumerate(extracted, 1))))
        progress(analysis, "privacy", "Checking for sensitive information and contradictions")
        privacy = find_pii(analysis.draft_text) + [
            p for e in analysis.evidence for p in find_pii(e.extracted_text)
        ]
        try:
            contradictions = (
                [] if settings.mock_mode else await find_contradictions([c.text for c in claims])
            )
        except LLMFailure:
            contradictions = []
        progress(analysis, "scoring", "Calculating credibility score")
        analysis.result = AnalysisResult(
            summary=summarize(claims, contradictions, list(set(privacy))),
            claims=claims,
            contradictions=contradictions,
            privacy_flags=list(set(privacy)),
            skipped_statements=narrative_skips(analysis.draft_text, extracted)
            if analysis.doc_type in {"essay", "scholarship_essay", "application"}
            else [],
        )
        analysis.status = AnalysisStatus.complete
        progress(analysis, "done", "Analysis complete")
    except Exception:
        analysis.status = AnalysisStatus.failed
        analysis.error = "Analysis could not be completed."
        save(analysis)
