from app.schemas import Claim, Summary, Verdict

COLOR_BY_VERDICT = {
    Verdict.publish: "green",
    Verdict.soften: "yellow",
    Verdict.needs_evidence: "red",
    Verdict.remove_sensitive_data: "purple",
}
ACTION_BY_VERDICT = {
    Verdict.publish: "Safe to publish",
    Verdict.soften: "Soften this claim",
    Verdict.needs_evidence: "Add evidence or remove",
    Verdict.remove_sensitive_data: "Remove sensitive data",
}
WEIGHTS = {
    Verdict.publish: 1.0,
    Verdict.soften: 0.6,
    Verdict.remove_sensitive_data: 0.4,
    Verdict.needs_evidence: 0.1,
}


def summarize(claims: list[Claim], contradictions: list[str], privacy_flags: list[str]) -> Summary:
    score = int(100 * sum(WEIGHTS[c.verdict] for c in claims) / max(len(claims), 1)) - 5 * len(
        contradictions
    )
    return Summary(
        trust_score=max(0, min(100, score)),
        claims_reviewed=len(claims),
        evidence_backed=sum(c.color == "green" for c in claims),
        needing_changes=sum(c.color in {"yellow", "red"} for c in claims),
        privacy_flags=len(privacy_flags),
    )
