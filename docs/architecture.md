# TrustID architecture

TrustID is being developed as a modular monolith with a Next.js frontend, a FastAPI backend, shared domain contracts, PostgreSQL persistence, Redis coordination, and S3-compatible object storage. Phase 3 adds a protected console shell and authentication boundary without implementing verification workflows or provider integrations.

## Frontend

`apps/web` contains the Next.js App Router shell, global institutional styling, public marketing routes, a centralized `AuthProvider`, protected console pages, and feature-oriented locations for future work. Phase 4 adds a deterministic typed dashboard data seam at `apps/web/src/lib/dashboard-data.ts`; it is display-only demo data and is designed to be replaced by an authorized dashboard API provider later. The browser must call TrustID API routes rather than AI providers directly. Future feature modules belong under `apps/web/src/features` and should keep UI, data access, and presentation concerns local to each capability.

## Backend

`apps/api` contains the FastAPI modular monolith. Routes live in the API layer, domain contracts define stable concepts, services expose provider-neutral interfaces, repositories own data access, and database sessions are isolated in `app/db`. Authentication routes delegate to an auth service, session and permission dependencies enforce boundaries, and auth models are represented in Alembic migrations. Phase 5 adds document ingestion with PostgreSQL metadata and private S3-compatible storage. Phase 6 adds OCR extraction and structured fields. Phase 7 adds technical tampering signals and evidence. Phase 8 adds bounded presented-photo validation and provider-neutral face comparison. Phase 9 adds verification-level orchestration, deterministic document validation, persisted factorized risk assessment, safe module statuses, and officer-facing result APIs. Risk is decision support only; it is not fraud, criminality, legal identity, immigration, or automatic decision logic. The `/api/v1/health` route remains unchanged.

## Data and infrastructure

PostgreSQL is the long-term relational database and is exposed through SQLAlchemy with Alembic reserved for migrations. Redis is reserved for cache and coordination. MinIO provides local S3-compatible object storage for future document artifacts. Docker Compose provisions these services for local development without committing credentials.

## Shared contracts

`packages/shared/src` holds TypeScript representations of canonical verification states, risk levels, face outcomes, and health responses. The Python backend mirrors the same domain vocabulary in `apps/api/app/domain/contracts.py`; generated cross-language schemas can be introduced in a later phase once the domain stabilizes.

## AI service abstraction

The intended boundary is frontend → verification API → orchestrator → provider-neutral service interfaces → demo or production implementation. Phase 0 defines `OCRService`, `DocumentValidationService`, `TamperingDetectionService`, `FaceVerificationService`, and `RiskAssessmentService` protocols without connecting an AI provider or presenting synthetic results as real.

## Future integrations

Document processing, cases, reports, production analytics, government data providers, and optional blockchain anchoring remain deferred. The Phase 4 dashboard uses fictional records and deterministic trend data only; it does not create verification persistence or claim live operational health. Authentication and RBAC are now foundations only: local demo sessions use an in-process service until a shared persistent repository and production hardening are added. Any future integration must preserve the evidence-first decision-support model and clearly distinguish demo or simulated behavior.
