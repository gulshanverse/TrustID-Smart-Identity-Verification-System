# TrustID Smart Identity Verification System

TrustID is an AI-assisted identity and document screening platform for Smart India Hackathon problem statement 26188: **AI-Based Fake Identity & Document Screening System**. The product promise is **Verify. Detect. Protect.** It is decision support for authorized personnel, not an autonomous legal or criminality determination system.

## Project status

**PHASE 0 COMPLETE — foundation and repository architecture.** The repository now contains the application shells, shared domain vocabulary, backend boundaries, database/infrastructure configuration, tests, quality tooling, and development documentation needed for later phases. Product workflows and AI providers are intentionally not implemented yet.

## Authoritative source of truth

Use both master documents together for all TrustID product, UX, architecture, and implementation work:

| Document | Role |
| --- | --- |
| [`TRUSTID_MASTER_SPEC.md`](./TRUSTID_MASTER_SPEC.md) | Product and engineering requirements, workflows, routes, data models, safety boundaries, and acceptance criteria. |
| [`MANUS_MASTER_CONTEXT_PROMPT.md`](./MANUS_MASTER_CONTEXT_PROMPT.md) | Implementation context covering design direction, architecture, demo scenarios, risk semantics, frontend/backend expectations, and delivery standards. |

The master specification defines **what TrustID must be**. The master context prompt defines **how TrustID should be designed and implemented**. The Phase 0 scope and quality gates are defined in the supplied execution brief.

## Architecture

```text
apps/web (Next.js + React + TypeScript)
        ↓
apps/api (FastAPI modular monolith, /api/v1)
        ↓
services and repositories
        ↓
PostgreSQL · Redis · MinIO

packages/shared (cross-layer domain contracts)
```

The API exposes a working `GET /api/v1/health` endpoint. Provider-neutral protocols exist for OCR, document validation, tampering detection, face verification, and risk assessment, but no provider or fake result is connected in Phase 0.

## Repository structure

```text
apps/
  web/                 Next.js foundation shell and frontend tests
  api/                 FastAPI application, contracts, services, and API tests
packages/
  shared/              Shared TypeScript domain contracts
docs/                  Architecture and development guides
infra/                 Reserved for future infrastructure assets
.github/workflows/     Foundational CI checks
TRUSTID_MASTER_SPEC.md
MANUS_MASTER_CONTEXT_PROMPT.md
.env.example
docker-compose.yml
```

## Local development

Requirements are Node.js 22+, npm, Python 3.11+, Docker, and Docker Compose.

Start local infrastructure from the repository root:

```bash
docker compose up -d postgres redis minio
```

Copy `.env.example` to `.env` if local configuration overrides are needed. Never commit real secrets or identity data.

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`. Quality commands are `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build`.

### Backend

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8000
```

Check the API at `http://localhost:8000/api/v1/health`. Backend quality commands are `pytest`, `ruff check app tests`, and `mypy app`.

## Phase 0 boundaries

The following are deliberately deferred: full public website, dashboard, document upload, OCR implementation, tampering detection, face verification, risk engine, cases, investigation, analytics, reports, audit UI, blockchain, government database integration, production AI providers, and full authentication. Refer to the master documents before beginning the next explicit phase.

See [`docs/architecture.md`](./docs/architecture.md) for boundaries and [`docs/development.md`](./docs/development.md) for the development workflow.
