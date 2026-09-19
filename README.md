# Tether

Tether is a frontend prototype for an AI-powered claim verification system. It turns a student draft and supporting proof into a clear Trust Map: evidence-backed claims, missing proof, unsafe wording, and privacy risks.

## Run locally

Open `index.html` in a browser. No build tooling or dependency install is required.

## Product flow

1. Add a scholarship essay, resume, or proposal and supporting evidence.
2. Run the Nemotron audit.
3. Review claim-level confidence, source provenance, safe rewrites, and privacy flags.
4. Export the resulting Evidence Pack from the browser print dialog.

The included data is a polished demo state. The intended production pipeline is Jinja2 prompt templating + NeMo Guardrails + structured Nemotron claim-verdict JSON.
