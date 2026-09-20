# Tether

> **Every claim, tethered to proof.**

Tether is a pre-submission coach for scholarship and college applications. It helps students find claims that need stronger evidence, safer wording, or privacy cleanup before they submit.

Tether does not certify claims or independently authenticate sources. Students see the matched source, choose whether to revise, and decide what—if anything—to attach.

## What Tether does

- Extracts factual, checkable claims from a draft or readable proof file.
- Uses Narrative Mode to leave reflective essay language alone and show what was skipped.
- Matches claims to student-provided sources and explains the match.
- Gives specific next steps for weak claims: advisor confirmations, analytics exports, receipts, and screenshots.
- Redacts deterministic PII before any text is sent to a live model.
- Offers rewrite suggestions without auto-applying them.
- Produces an optional Supporting Appendix for programs that permit attachments.

## Honest claim guidance

| Tether says | Meaning |
| --- | --- |
| Supported by your evidence | A supplied source is relevant to the exact claim. |
| Partially supported | The source is related, but the wording or number needs care. |
| No evidence found | Add proof, soften the language, or remove the claim. |
| Contains private info | Remove or redact personal data before sharing. |

Sources are always labeled **student-provided**. Tether matches source text; it does not independently verify authenticity.

## Privacy and student control

- Upload consent is required in the product before analysis.
- Use **Delete my data** to remove a saved analysis from the local Tether store.
- Rewrites are suggestions. Students should follow their program’s AI-writing policy and submit only work they approve.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). `MOCK_MODE=true` gives deterministic demo decisions. Set `MOCK_MODE=false` and `OLLAMA_API_KEY` for live Nemotron evaluation.

## Frontend

```bash
cd web
npm install
npm run dev
```

The browser fallback reviews pasted text and readable PDF, DOCX, and TXT files when no FastAPI service is available. For server-side privacy safeguards, PDF export, and live Nemotron evaluation, run FastAPI alongside the UI.

## API

- `POST /api/analyses` — draft and/or uploaded evidence
- `GET /api/analyses/{id}` — analysis, coaching steps, and narrative skips
- `POST /api/analyses/{id}/claims/{claim_id}/accept-rewrite`
- `POST /api/analyses/{id}/claims/{claim_id}/feedback`
- `DELETE /api/analyses/{id}` — delete saved data
- `GET /api/analyses/{id}/evidence-pack` and `/preview`
- `POST /api/demo` · `GET /api/health`

## Development checks

```bash
.venv/bin/pytest -q
.venv/bin/ruff check app tests
```
