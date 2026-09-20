# Tether

## Purpose

### What Tether is

Tether checks student drafts claim by claim against the student's own proof, so they can submit work they can back up.

### The problem

Students submit scholarship essays, college applications, resumes, club proposals, and research summaries. The writing is rarely the issue. The claims can be vague, inflated, unsupported, or expose personal data such as phone numbers and addresses.

For example, a student may write “Led a team of 12,” “Raised $3,000,” or “Built an app used by 500 students.” Each statement may be true, but it can be hard to tell whether the supplied material supports the exact wording.

### How it works

1. The student pastes a draft and adds proof, including files, links, or notes.
2. Tether extracts factual claims from the supplied text.
3. It finds the parts of the proof that relate to each claim.
4. Nemotron judges whether the supplied proof supports the exact claim.
5. Tether scores the draft and generates the results.

### The four verdicts

| Label | Meaning |
| --- | --- |
| Verified | Backed by the evidence supplied. |
| Refine | Plausible, but needs specifics or softer wording. |
| Needs proof | Unsupported or conflicting. |
| Private | Contains personal data to remove before sharing. |

### What the student gets

Tether provides a claim-by-claim credibility view, the missing proof for each weak claim, and a safer suggested rewrite. It can also create a reviewer-friendly Evidence Pack that pairs a claim with supporting evidence and a short note about where that evidence came from. Evidence is student-provided; Tether matches source text and does not independently authenticate it.

### Who it's for

Tether is for students preparing submissions and reviewers who need to trust a submission quickly. It is designed around scholarship and college-application materials, while also supporting resumes, proposals, and research summaries.

### What Tether is not

It is not a chatbot, it does not write the essay, and it does not decide who gets accepted. It gives the student clear decisions about their own claims, and the student stays in control of what is submitted.

### A before and after example

“Built an app used by 500 students” is marked Needs proof, with the suggested rewrite “Built an app piloted with students at my school.”

Students shouldn't need to exaggerate to stand out. Tether helps them turn real work into claims they can prove.

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
