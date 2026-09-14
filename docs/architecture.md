# TrustID architecture

TrustID is being developed as a modular monolith with a Next.js frontend, a FastAPI backend, shared domain contracts, PostgreSQL persistence, Redis coordination, and S3-compatible object storage. Phase 0 establishes boundaries without implementing verification workflows or provider integrations.

## Frontend

`apps/web` contains the Next.js App Router shell, global institutional styling, and feature-oriented locations for future work. The browser must call TrustID API routes rather than AI providers directly. Future feature modules belong under `apps/web/src/features` and should keep UI, data access, and presentation concerns local to each capability.

## Backend

`apps/api` contains the FastAPI modular monolith. Routes live in the API layer, domain contracts define stable concepts, services expose provider-neutral interfaces, repositories will own data access, and database sessions are isolated in `app/db`. The current `/api/v1/health` route is the only business-neutral endpoint.

## Data and infrastructure

PostgreSQL is the long-term relational database and is exposed through SQLAlchemy with Alembic reserved for migrations. Redis is reserved for cache and coordination. MinIO provides local S3-compatible object storage for future document artifacts. Docker Compose provisions these services for local development without committing credentials.

## Shared contracts

`packages/shared/src` holds TypeScript representations of canonical verification states, risk levels, face outcomes, and health responses. The Python backend mirrors the same domain vocabulary in `apps/api/app/domain/contracts.py`; generated cross-language schemas can be introduced in a later phase once the domain stabilizes.

## AI service abstraction

The intended boundary is frontend → verification API → orchestrator → provider-neutral service interfaces → demo or production implementation. Phase 0 defines `OCRService`, `DocumentValidationService`, `TamperingDetectionService`, `FaceVerificationService`, and `RiskAssessmentService` protocols without connecting an AI provider or presenting synthetic results as real.

## Future integrations

Authentication, RBAC, document processing, cases, reports, analytics, audit, government data providers, and optional blockchain anchoring are intentionally deferred. Any future integration must preserve the evidence-first decision-support model and clearly distinguish demo or simulated behavior.
