import re
from pathlib import Path
from typing import TypeVar

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from openai import AsyncOpenAI
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
    if not settings.nvidia_api_key:
        raise LLMFailure("NVIDIA_API_KEY is not configured")
    prompt = render_prompt(template, **context)
    client = AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1", api_key=settings.nvidia_api_key
    )
    for attempt in range(2):
        raw = (
            await client.chat.completions.create(
                model=settings.nemotron_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1800,
                timeout=30,
            )
        ).choices[0].message.content or ""
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
