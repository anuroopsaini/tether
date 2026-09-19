import re

from rank_bm25 import BM25Okapi

from app.schemas import EvidenceSnippet


def entities(text: str) -> set[str]:
    money = re.findall(r"\$[\d,]+(?:\.\d{2})?", text)
    percents = re.findall(r"\b\d+(?:\.\d+)?%", text)
    numbers = re.findall(r"\b\d{1,5}\b", text)
    words = re.findall(r"\b[A-Za-z]{4,}\b", text.lower())
    return set(money + percents + numbers + words)


def top_matches(
    claim: str, snippets: list[EvidenceSnippet], limit: int = 5
) -> list[EvidenceSnippet]:
    if not snippets:
        return []
    query = re.findall(r"\w+", claim.lower())
    corpus = [re.findall(r"\w+", s.text.lower()) for s in snippets]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query)
    claim_entities = entities(claim)
    ranked = sorted(
        enumerate(snippets),
        key=lambda item: scores[item[0]] + 3 * len(claim_entities & entities(item[1].text)),
        reverse=True,
    )
    return [snippet for _, snippet in ranked[:limit]]
