# Tether API Contract Audit

Phase 1 audit performed against the committed React/Vite frontend (`web/src`), the legacy static frontend in the repository root (`index.html` and `app.js`), and FastAPI running with `MOCK_MODE=true` on 2026-09-20. No product code was changed during this phase.

## What FastAPI currently serves

FastAPI mounts the repository-root `dist/` directory. That directory contains the React/Vite bundle built from `web/src/main.jsx`; its bundle includes the current bird logo and static `claims`/`analyses` fixtures. It does **not** serve the repository-root `index.html`, `app.js`, or `styles.css`. Those root files are a legacy frontend and are therefore disconnected from the deployed app.

`web/vite.config.js` builds to `../dist`, so `web/dist` is not the production bundle location. The committed `dist/` bundle is consistent with the current source in the limited sense that it contains the new React application and logo reference. A clean rebuild was deliberately not run in Phase 1 because the requested phase permits no code/build changes.

## Frontend call inventory

The current React source (`web/src/main.jsx`) has no `fetch`, `axios`, `EventSource`, `FormData`, or `/api` use. Every screen renders fixture data; its “API connection” label is display-only. The only actual browser API calls are in the unserved legacy `app.js`.

| Frontend location | Method and URL | Request body / fields | Response fields read |
| --- | --- | --- | --- |
| `app.js:23` | `POST /api/analyses` | Multipart `FormData`: `doc_type`, `draft_text`, repeated `files`. It does not send optional `notes` or `urls`. | `id`; on non-2xx it tries `detail.error.message`. |
| `app.js:22` | `GET /api/analyses/{id}` (polls once/sec) | None. | `status`, `error`, `progress.at(-1).message`, then `result.claims`, `result.summary.trust_score`, `result.summary.evidence_backed`, `result.summary.needing_changes`, `result.summary.privacy_flags`; per claim: `id`, `text`, `category`, `confidence`, `color`, `action`, `evidence_match`, `safe_rewrite`, `evidence_snippets[0].file_name`, `evidence_snippets[0].page`. |
| `app.js:23` | Browser print, no API URL | `window.print()` | None. It never requests the backend PDF or preview. |
| `web/src/main.jsx` | None | None | None. Buttons for new analysis, upload, export, accept rewrite, packs, and settings do not call an API. |

There is no frontend use of `GET /events`, `POST /accept-rewrite`, `GET /evidence-pack`, `GET /evidence-pack/preview`, `POST /demo`, or `GET /health` in either served React source or legacy app.

## Endpoint and contract comparison

| Frontend expectation | Backend reality | Mismatch? | Fix |
| --- | --- | --- | --- |
| `POST /api/analyses` accepts multipart `doc_type`, `draft_text`, repeated `files`. | Exact match. Optional `notes` and repeated `urls` are also supported. Returns `202 {"id", "status"}`. | No for legacy frontend. Current React never calls it. | Keep fields; add React integration only if frontend behavior is explicitly expanded later. |
| `POST /api/analyses` error can be read as `{detail:{error:{code,message}}}`. | Validation/domain `HTTPException`s are wrapped by FastAPI as `{detail:{error:{code,message}}}`. Other validation errors use FastAPI's default `{detail:[...]}`. | Yes: Phase 2 requires top-level `{error:{code,message}}`; current shape is inconsistent. | Add app-level exception handlers that normalize every API error to top-level `error`; update tests. |
| `GET /api/analyses/{id}` returns snake_case result/progress fields read by legacy app. | Exact snake_case match. `status` values are `queued`, `processing`, `complete`, `failed`; `progress` is an array of `{step,message,current,total,at}`. | No for legacy frontend. React expects no data at all. | Preserve snake_case compatibility; aliases alone cannot make the static React UI live. |
| Claim colors are `green`, `yellow`, `red`, `purple`. | Exact match. Verdicts are `publish`, `soften`, `needs_evidence`, `remove_sensitive_data`; categories are `measurable`, `subjective`, `sensitive`, `unverifiable`, `potentially_misleading`. | No for legacy color mapping; React uses its own fixture labels (`Verified`, `Refine`, `Needs proof`, `Private`). | Keep enums and mapped colors. A live React integration would need a presentation mapping, but no such request is made by the current source. |
| Poll progress uses `analysis.progress.at(-1).message`; final status is `complete`/`failed`. | Exact match. Steps emitted are `extracting`, `matching`, repeated `judging`, `privacy`, `scoring`, `done`. | No for polling. | Preserve names; document them as stable contract values. |
| If SSE were used, frontend would need named events and known JSON payload. | No frontend subscribes. SSE sends unnamed `data: <ProgressEvent JSON>` for every step, then `event: complete` with `{ "status": "complete" | "failed" }`. | Yes against the requested shared-event convention: progress events have no `event:` name. | Phase 2: emit a named `progress` event (and retain/consider compatibility for unnamed data), define payload and test it. |
| `POST /api/analyses/{id}/claims/{claim_id}/accept-rewrite` would need a JSON body/response usable by a claim inspector. | No body is accepted. It returns the whole claim in snake_case with `accepted_rewrite` set to `safe_rewrite`. No frontend calls it. | Partial: response is usable but undocumented and there is no frontend expectation. | Stabilize a documented response model; preserve no-body semantics unless UI begins sending a request body. |
| Evidence Pack export should work from the displayed product. | Legacy UI uses `window.print()` and never calls the pack endpoints. React “Export pack” button has no handler. Backend supports PDF download and HTML preview. | Yes: neither served UI can use the backend pack. | Backend cannot make the static React buttons call it. This requires a frontend change, outside Phase 2's backend-only scope. |
| `GET /api/analyses/{id}/evidence-pack/preview` returns embeddable HTML; PDF endpoint downloads PDF. | Preview `GET` is `200 text/html`. PDF `GET` was `503` locally because WeasyPrint dependencies are unavailable; on success it sets `Content-Disposition: attachment`. | No response-shape mismatch; operational PDF dependency is missing locally. | Install/provision WeasyPrint system dependencies before claiming PDF verification. |
| Frontend dev server at Vite default origin can call API. | No Vite `server.proxy` exists. Default `ALLOWED_ORIGINS` is only `http://localhost:3000`; Vite defaults to `http://localhost:5173`. | Yes. | Add `http://localhost:5173` to defaults and/or a Vite `/api` proxy. Because Phase 2 is backend-only, prefer backend CORS default; proxy would be a frontend-config change. |
| FastAPI serves the frontend source used by the team. | It serves root `dist/` (current React build), not `web/src` directly and not legacy root `index.html`. | Partial: this is correct for production but means the only API-aware frontend is unserved. | Keep root `dist/`; integrate API behavior into React source in a separately authorized frontend task. |
| `POST /api/demo` creates a representative demo. | Exact endpoint returns `202 {id,status}` and mock flow yields green/yellow/red/purple claims. | No. | Keep and add endpoint-shape test in Phase 3. |
| `GET /api/health` indicates backend state. | Returns `{status,provider,nemotron,model}`. No frontend calls it. | No direct mismatch. | Add response model/test if stabilizing the public API. |

## Observed mock responses

`POST /api/demo` returned:

```json
{"id":"de5b0f68-4e7c-4761-ba29-30da8a164a25","status":"queued"}
```

After completion, `GET /api/analyses/{id}` returned `status: "complete"`, the nine progress steps listed above, and this summary:

```json
{"trust_score":52,"claims_reviewed":4,"evidence_backed":1,"needing_changes":2,"privacy_flags":1}
```

The result contained colors `green`, `yellow`, `red`, and `purple`. The exact SSE stream emitted unnamed progress data and then:

```text
event: complete
data: {"status": "complete"}
```

`POST /accept-rewrite` returned a complete claim object with `accepted_rewrite: "Raised nearly $2,850 for the robotics club."`. `GET /evidence-pack/preview` returned `200 text/html`; the PDF endpoint returned `503` in this environment due to unavailable PDF rendering dependencies. A missing analysis returned:

```json
{"detail":{"error":{"code":"NOT_FOUND","message":"Analysis not found"}}}
```

## Primary Phase 2 constraints

1. A backend-only change can normalize errors, CORS, schemas, progress, and SSE, but cannot make the served React app submit drafts, load analyses, accept rewrites, or export a pack: it contains no API code.
2. The legacy UI is API-aware but is not served by FastAPI. Replacing the React bundle with it would change the current frontend UI, contrary to the instruction that the frontend is source of truth.
3. The PDF endpoint needs its WeasyPrint dependencies in the execution host; this is deployment setup, not an API contract mismatch.

