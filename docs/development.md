# TrustID development guide

## Local setup

Install Node.js 22+, pnpm or npm, Python 3.11+, Docker, and Docker Compose. Copy `.env.example` to `.env` when local overrides are needed. No real credentials or identity data belong in the repository.

Start infrastructure with `docker compose up -d postgres redis minio` from the repository root.

## Frontend

Run `cd apps/web && npm install`, then `npm run dev`. The foundation shell is available at `http://localhost:3000`. Use `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build` for quality checks.

## Backend

Create a virtual environment with `python3 -m venv .venv`, activate it, and install development dependencies with `pip install -e '.[dev]'` from `apps/api`. Start the API with `uvicorn app.main:app --reload --port 8000`. The health endpoint is `GET http://localhost:8000/api/v1/health`.

Run backend checks from `apps/api`: `pytest`, `ruff check app tests`, and `mypy app`.

## Testing and quality

Phase 0 tests prove that the frontend test harness runs and that the FastAPI application starts with a functioning health endpoint. Keep tests focused on behavior and contracts rather than adding tests for their own sake.

## Branch and commit expectations

Use small, descriptive conventional commits such as `feat: establish TrustID application foundation`. Preserve history, do not force-push, and keep Phase 0 separate from later product phases.

## Scope discipline

Do not add the dashboard, public marketing site, upload workflow, real OCR, tampering analysis, face verification, risk engine, government integration, blockchain, or production AI provider in Phase 0. Refer to [`TRUSTID_MASTER_SPEC.md`](../TRUSTID_MASTER_SPEC.md), [`MANUS_MASTER_CONTEXT_PROMPT.md`](../MANUS_MASTER_CONTEXT_PROMPT.md), and the Phase 0 execution brief for the authoritative scope.
