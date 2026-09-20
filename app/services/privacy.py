import re

PATTERNS = {
    "Email address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "Phone number": r"(?:\+?1[-. ]?)?(?:\(?\d{3}\)?[-. ]?)\d{3}[-. ]?\d{4}\b",
    "Date of birth": r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b",
    "Student ID": r"\b(?:student\s*(?:id|number)[:#]?\s*)[A-Z0-9-]{5,}\b",
    "Street address": r"\b\d{1,5}\s+[A-Za-z0-9.' -]+\s(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b",
}


def find_pii(text: str) -> list[str]:
    return [label for label, pattern in PATTERNS.items() if re.search(pattern, text, re.IGNORECASE)]


def redact_pii(text: str) -> str:
    """Remove deterministic identifiers before any text is sent to a model."""
    for label, pattern in PATTERNS.items():
        text = re.sub(pattern, f"[{label.upper().replace(' ', '_')} REDACTED]", text, flags=re.IGNORECASE)
    return text
