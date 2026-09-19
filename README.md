# Tether

Tether is an evidence-backed claim checker for student applications, essays, resumes, and project proposals. It turns a draft and optional proof into a reviewer-friendly trust map and Evidence Pack.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive OpenAPI documentation is at `/docs`.

`MOCK_MODE=true` is the default. It provides deterministic, demo-safe claim decisions without an NVIDIA key. To use Nemotron, set `MOCK_MODE=false`, provide `NVIDIA_API_KEY`, and confirm `NEMOTRON_MODEL` in your NVIDIA dashboard.

## API

- `POST /api/analyses` — multipart upload (`doc_type`, `draft_text`, optional `files`, `notes`, `urls`)
- `GET /api/analyses/{id}` — result and progress
- `GET /api/analyses/{id}/events` — server-sent progress events
- `POST /api/analyses/{id}/claims/{claim_id}/accept-rewrite`
- `GET /api/analyses/{id}/evidence-pack` — PDF download
- `GET /api/analyses/{id}/evidence-pack/preview` — server-rendered HTML
- `POST /api/demo` — sample analysis across green/yellow/red/purple verdicts
- `GET /api/health`

## Design notes

The model only judges candidate evidence selected by deterministic retrieval. Evidence IDs returned by the model are validated in code, and a claim cannot be marked publishable without a validated evidence snippet. Scores are computed in code so they are stable and explainable.
