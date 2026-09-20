import re
from pathlib import Path
from typing import TypeVar

import httpx
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.schemas import ClaimJudgment, ContradictionResponse, ExtractedClaim

T = TypeVar("T", bound=BaseModel)
PROMPTS = Path(__file__).parent.parent / "prompts"
env = Environment(loader=FileSystemLoader(PROMPTS), undefined=StrictUndefined, autoescape=False)


class LLMFailure(RuntimeError):
    pass


def render_prompt(template: str, **context: object) -> str:
    return env.get_template(template).render(**context)


def strip_fences(value: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", value.strip(), flags=re.IGNORECASE)


async def call_json(template: str, schema: type[T], **context: object) -> T:
    settings = get_settings()
    if not settings.provider_api_key:
        raise LLMFailure("OLLAMA_API_KEY is not configured")
    prompt = render_prompt(template, **context)
    for attempt in range(2):
        try:
            # Ultra prioritizes deep reasoning and can take longer than the
            # previous fast model. Ask Ollama to enforce the target schema so
            # its result remains safe to render in the claim dashboard.
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    "https://ollama.com/api/chat",
                    headers={"Authorization": f"Bearer {settings.provider_api_key}"},
                    json={
                        "model": settings.nemotron_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "format": schema.model_json_schema(),
                        "options": {"temperature": 0.1},
                    },
                )
                response.raise_for_status()
                raw = response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, TypeError) as error:
            raise LLMFailure(f"Ollama request failed: {error}") from error
        try:
            return schema.model_validate_json(strip_fences(raw))
        except ValidationError as error:
            if attempt == 1:
                raise LLMFailure(f"Model returned invalid structured output: {error}") from error
            prompt = render_prompt("corrective.j2", error=str(error), bad=raw)
    raise LLMFailure("Unexpected model retry failure")


async def extract_claims(draft: str) -> list[ExtractedClaim]:
    response = await call_json("extract_claims.j2", ClaimList, draft=draft)
    return [
        claim for claim in response.claims if claim.source_quote and claim.source_quote in draft
    ][:10]


class ClaimList(BaseModel):
    claims: list[ExtractedClaim]


async def judge_claim(claim: ExtractedClaim, snippets: list[dict]) -> ClaimJudgment:
    return await call_json(
        "judge_claim.j2", ClaimJudgment, claim=claim.model_dump(), snippets=snippets
    )


async def find_contradictions(claims: list[str]) -> list[str]:
    return (
        await call_json("contradictions.j2", ContradictionResponse, claims=claims)
    ).contradictions
