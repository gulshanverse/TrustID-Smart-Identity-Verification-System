# TrustID development guide

## Local setup

Install Node.js 22+, npm, Python 3.11+, Docker, and Docker Compose. Copy `.env.example` to `.env` when local overrides are needed. No real credentials or identity data belong in the repository.

Start infrastructure with `docker compose up -d postgres redis minio` from the repository root. Enable fictional development accounts by setting a local-only `DEMO_PASSWORD` of at least ten characters. The password is never committed or embedded in the frontend.

## Frontend

Run `cd apps/web && npm install`, then `npm run dev`. The public website is available at `http://localhost:3000`; authenticated console destinations are under `/console/*` and redirect to `/login` without a valid session. Use `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build` for quality checks.

## Backend

Create a virtual environment with `python3 -m venv .venv`, activate it, and install development dependencies with `pip install -e '.[dev]'` from `apps/api`. Start the API with `uvicorn app.main:app --reload --port 8000`. The health endpoint is `GET http://localhost:8000/api/v1/health`.

Authentication endpoints are `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, and `GET /api/v1/auth/me`. The browser session uses an HttpOnly cookie. Run `.venv/bin/pytest`, `.venv/bin/ruff check app tests migrations`, `.venv/bin/mypy app`, and `.venv/bin/alembic upgrade --sql head` from `apps/api`.

## SIH demo workflow

Use `/console/demo` to orient judges to the five supported fictional scenarios: genuine/low risk, tampered document, face mismatch, expired document, and multiple issues. The golden path is `/console/verify` followed by persisted OCR, validation, technical tampering, face comparison, explainable risk, optional case work, audit, analytics, and report generation. The deterministic demo providers require no external government API. Arbitrary real uploads cannot receive fabricated demo results.

## Branch and commit expectations

Use small, descriptive conventional commits. Preserve history, do not force-push, and keep the Phase 3 authentication and console foundation separate from later verification phases.

## Scope discipline

Do not add government integration, blockchain, production AI providers, surveillance, demographic or emotion inference, automatic approval/rejection, or fabricated metrics. Risk thresholds remain deterministic prototype semantics: LOW 0–29, REVIEW 30–69, HIGH 70–100. Refer to [`TRUSTID_MASTER_SPEC.md`](../TRUSTID_MASTER_SPEC.md) and [`docs/authentication.md`](./authentication.md) for the authoritative boundaries.
