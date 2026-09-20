# Tether

Tether is an evidence-backed claim checker for student applications, essays, resumes, and project proposals. It turns a draft and optional proof into a reviewer-friendly Trust Map and Evidence Pack.

The repository includes a polished frontend demo plus a FastAPI/Nemotron evidence-analysis backend.

## Run locally

Open `index.html` in a browser. No frontend dependency install is required.

## Product flow

1. Add a scholarship essay, resume, or proposal and supporting evidence.
2. Run the Nemotron audit.
3. Review claim-level confidence, source provenance, safe rewrites, and privacy flags.
4. Export the resulting Evidence Pack from the browser print dialog.

## Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive OpenAPI documentation is at `/docs`.

`MOCK_MODE=true` is the default. It provides deterministic, demo-safe claim decisions without a provider key. To use live Nemotron through Ollama Cloud, set `MOCK_MODE=false`, provide `OLLAMA_API_KEY`, and set `NEMOTRON_MODEL=nemotron-3-ultra:cloud`.

## API

- `POST /api/analyses` - multipart upload (`doc_type`, `draft_text`, optional `files`, `notes`, `urls`)
- `GET /api/analyses/{id}` - result and progress
- `GET /api/analyses/{id}/events` - server-sent progress events
- `POST /api/analyses/{id}/claims/{claim_id}/accept-rewrite`
- `GET /api/analyses/{id}/evidence-pack` - PDF download
- `GET /api/analyses/{id}/evidence-pack/preview` - server-rendered HTML
- `POST /api/demo` - sample analysis across green/yellow/red/purple verdicts
- `GET /api/health`

## Guardrails

The model only judges candidate evidence selected by deterministic retrieval. Evidence IDs returned by the model are validated in code, and a claim cannot be marked publishable without a validated evidence snippet. Scores are computed in code so they are stable and explainable.

## Frontend

The React/Vite workspace lives in `web/` and provides a compact, dark-mode product UI with Workspace, Analyses, claim review, Evidence Packs, and Settings screens.

```bash
cd web
npm install
npm run dev
```

Create a production bundle with `npm run build`.
