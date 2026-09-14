# TrustID Smart Identity Verification System

TrustID is an AI-assisted identity and document screening platform for Smart India Hackathon problem statement 26188: **AI-Based Fake Identity & Document Screening System**. The product promise is **Verify. Detect. Protect.** It is decision support for authorized personnel, not an autonomous legal or criminality determination system.

## Project status

**PHASE 6 COMPLETE — OCR and structured document extraction foundation.** The repository contains secure Phase 5 document ingestion plus provider-neutral, demo-labeled OCR, structured fields, confidence, evidence, PostgreSQL persistence, and authorized OCR results. Dashboard metrics remain fictional/demo display data; OCR is extraction only and does not determine authenticity. Tampering, face, risk, government, and production AI integrations remain deferred.

## Authoritative source of truth

Use both master documents together for all TrustID product, UX, architecture, and implementation work:

| Document | Role |
| --- | --- |
| [`TRUSTID_MASTER_SPEC.md`](./TRUSTID_MASTER_SPEC.md) | Product and engineering requirements, workflows, routes, data models, safety boundaries, and acceptance criteria. |
| [`MANUS_MASTER_CONTEXT_PROMPT.md`](./MANUS_MASTER_CONTEXT_PROMPT.md) | Implementation context covering design direction, architecture, demo scenarios, risk semantics, frontend/backend expectations, and delivery standards. |

The master specification defines **what TrustID must be**. The master context prompt defines **how TrustID should be designed and implemented**.

## Architecture

```text
apps/web (Next.js + React + TypeScript)
        ↓
apps/api (FastAPI modular monolith, /api/v1)
        ↓
auth service · permission dependencies · provider-neutral services
        ↓
PostgreSQL · Redis · MinIO
packages/shared (cross-layer domain contracts)
```

The API exposes `GET /api/v1/health`, the Phase 3 authentication boundary, Phase 5 verification/document endpoints, and Phase 6 OCR execution/result endpoints. See [`docs/document-upload.md`](./docs/document-upload.md) and [`docs/ocr.md`](./docs/ocr.md).

## Repository structure

```text
apps/
  web/                 Next.js public site, auth state, protected console, and frontend tests
  api/                 FastAPI app, auth service, models, migrations, and API tests
packages/
  shared/              Shared TypeScript domain contracts
docs/                  Architecture, auth, public website, and development guides
infra/                 Reserved for future infrastructure assets
.github/workflows/     Foundational CI checks
TRUSTID_MASTER_SPEC.md
MANUS_MASTER_CONTEXT_PROMPT.md
.env.example
docker-compose.yml
```

## Local development

Requirements are Node.js 22+, npm, Python 3.11+, Docker, and Docker Compose. Start local infrastructure from the repository root with `docker compose up -d postgres redis minio`. Copy `.env.example` to `.env` if local configuration overrides are needed. Never commit real secrets or identity data.

To enable fictional demo users locally, set `DEMO_PASSWORD` to a private development-only value of at least ten characters. The password is not committed or embedded in the frontend. Run the API on port 8000 and the web application on port 3000.

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`. Protected console destinations include `/console/dashboard`, `/console/verify`, `/console/verifications`, `/console/cases`, `/console/investigation`, `/console/analytics`, `/console/audit`, `/console/reports`, and `/console/settings`.

### Backend

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8000
```

Check `http://localhost:8000/api/v1/health`. Backend quality commands are `.venv/bin/pytest`, `.venv/bin/ruff check app tests migrations`, `.venv/bin/mypy app`, and `.venv/bin/alembic upgrade --sql head`.

## Scope boundaries

Phase 6 implements OCR extraction only. Tampering detection, face verification, risk calculation, verification orchestration, cases functionality, analytics calculations, reports generation, blockchain, government database integration, production AI providers, automatic fraud classification, and officer decision automation remain deferred. Console dashboard metrics and records are fictional display data; upload/OCR success is never simulated when storage or the configured provider is unavailable.

See [`docs/architecture.md`](./docs/architecture.md), [`docs/authentication.md`](./docs/authentication.md), [`docs/dashboard.md`](./docs/dashboard.md), [`docs/design-system.md`](./docs/design-system.md), [`docs/public-website.md`](./docs/public-website.md), and [`docs/development.md`](./docs/development.md) for implementation boundaries and workflows.
