# TrustID SIH demo deployment guide

This guide prepares the existing TrustID prototype for a controlled SIH 2026 demonstration deployment. It is **not** a production authorization for real government identity data. Use fictional demo identities and documents only.

## Deployment architecture

Deploy the Next.js frontend to Vercel, the FastAPI API to one Render or equivalent service instance, PostgreSQL to a managed PostgreSQL provider, Redis to a managed Redis provider, and documents to a private S3-compatible bucket such as Cloudflare R2. MinIO remains a local-development dependency. Do not configure multiple API replicas because authentication and sessions currently use in-process memory. The production face image is built from `apps/api/Dockerfile`; it installs OpenCV and downloads the pinned SFace/YuNet assets through checksum-verifying `apps/api/scripts/provision_face_models.sh`.

### Render Docker build context

The API Dockerfile is intentionally written for `apps/api` as its build context. Configure the Render Docker web service as follows:

| Render setting | Required value |
| --- | --- |
| Runtime | Docker |
| Root Directory | `apps/api` |
| Dockerfile Path | `./Dockerfile` |
| Health Check Path | `/api/v1/health` |
| Auto-Deploy | Enabled if desired |

With this configuration, Docker `COPY pyproject.toml ./`, `COPY app ./app`, and `COPY scripts/provision_face_models.sh ...` resolve inside `apps/api`. Do not configure repository root as the Docker build context while pointing at `apps/api/Dockerfile`; that context does not contain the paths expected by the Dockerfile and fails before dependency installation. The repository root also does not contain a backend `pyproject.toml` or `app/` directory.

The equivalent declarative configuration is committed in [`render.yaml`](../render.yaml). It contains only non-secret defaults; all database, Redis, object-storage, CORS, and demo-password values remain unsynchronized secret settings.

## Required services and variables

The API requires PostgreSQL, Redis configuration, and a private S3-compatible bucket. Set these server-only variables on the API service:

| Variable | Deployment value |
| --- | --- |
| `APP_ENV` | `production` |
| `DATABASE_URL` | Managed PostgreSQL URL with TLS as required by the provider |
| `REDIS_URL` | Managed Redis URL |
| `OBJECT_STORAGE_ENDPOINT` | Private R2/S3-compatible endpoint |
| `OBJECT_STORAGE_REGION` | `auto` for R2, or the provider's region |
| `OBJECT_STORAGE_BUCKET` | Private demo bucket name |
| `OBJECT_STORAGE_ACCESS_KEY` | Provider access key; never commit it |
| `OBJECT_STORAGE_SECRET_KEY` | Provider secret; never commit it |
| `OCR_PROVIDER` | `demo` |
| `TAMPERING_PROVIDER` | `demo` |
| `FACE_PROVIDER` | `demo` in the local example; `production` is explicit in `apps/api/Dockerfile` |
| `FACE_DETECTOR` | `haar` in application configuration; the production Docker candidate explicitly sets `yunet` |
| `FACE_MODEL_PATH` | Pinned SFace path inside the production image when `FACE_PROVIDER=production` |
| `FACE_MODEL_SHA256` | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |
| `FACE_DETECTOR_MODEL_PATH` | Pinned YuNet path inside the production image when `FACE_DETECTOR=yunet` |
| `FACE_DETECTOR_MODEL_SHA256` | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| `FACE_DETECTOR_SCORE_THRESHOLD` | `0.90` in the production Docker candidate |
| `FACE_MIN_FACE_PIXELS` | `6400` in the production Docker candidate |
| `FACE_BLUR_THRESHOLD` | `20.0` application default; `5.0` explicitly in the production Docker candidate |
| `FACE_BRIGHTNESS_MIN` / `FACE_BRIGHTNESS_MAX` | `35` / `225` in the production Docker candidate |
| `FACE_CONTRAST_MIN` | `18` in the production Docker candidate |
| `FACE_BOX_PADDING` | `0.0` in the production Docker candidate |
| `CORS_ORIGINS` | Exact HTTPS Vercel origin, comma-separated if required |
| `DEMO_PASSWORD` | Private demo-only password, at least ten characters |
| `SESSION_COOKIE_SECURE` | `true` |
| `SESSION_COOKIE_SAMESITE` | `none` when frontend and API are on different sites |
| `SESSION_COOKIE_MAX_AGE` | Desired session lifetime in seconds |

Set `NEXT_PUBLIC_API_URL` only in the Vercel project. It is browser-visible and must contain only the HTTPS API base URL, for example `https://api.example.invalid`; it must not contain credentials or secrets.

## Database migration

Run migrations from the API release environment, not from a developer laptop against an unknown database:

```bash
cd apps/api
alembic upgrade head
```

The migration chain currently ends at `015_analysis_processing_time`. Revision identifiers are kept at or below PostgreSQL Alembic's `VARCHAR(32)` version-table limit. The CI-safe validation command is:

```bash
alembic upgrade --sql head
```

## Backend start command

Use one backend instance with the platform-provided port:

```bash
cd apps/api
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Configure the platform liveness check as `GET /api/v1/health` and, where the platform supports it, readiness as `GET /api/v1/readiness`. Neither requires authentication. Liveness checks only the process; readiness checks the required relational database and returns a generic `503` when it is unavailable. The API reads database, Redis, storage, provider, CORS, and cookie settings from environment variables.

The face provider is cached once per API process after configuration and uses a process-local inference lock. This prevents model reloading on every request and avoids concurrent mutation of OpenCV detector state. This is a safe single-instance optimization, not a horizontal-capacity guarantee.

The **strongest measured candidate** is YuNet + `alignCrop` + blur threshold `5.0` on LFW. The **current application default** remains Haar + blur threshold `20.0` for backwards compatibility. The **production Docker candidate** is explicitly configured as YuNet + `alignCrop` + blur threshold `5.0`, but it is not yet a Render-validated production configuration.

In `APP_ENV=production`, invalid or unavailable object-storage client initialization fails API startup instead of silently installing an unavailable-storage fallback. This makes Render deployment logs identify configuration/dependency failures before an upload request is attempted. Local development retains the unavailable-storage fallback for environments where MinIO is intentionally not running.

## Frontend deployment

From `apps/web`, Vercel should use the standard Next.js build and start behavior. Set `NEXT_PUBLIC_API_URL` before the build. Required checks are `npm install`, `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build`. The browser no longer falls back to a localhost API URL when the variable is absent; a missing value will therefore fail visibly instead of silently targeting a developer machine.

## CORS and cookies

The API must list the exact frontend HTTPS origin in `CORS_ORIGINS`; never use `*` with credentialed requests. Because Vercel and a separately hosted API are cross-origin, use `SESSION_COOKIE_SECURE=true` and `SESSION_COOKIE_SAMESITE=none`. Keep the session cookie HttpOnly and use HTTPS on both services. Logout revokes the in-process token and clears the cookie.

## Storage and uploads

Use a private bucket and do not expose MinIO publicly. The API uses UUID-derived storage keys, safe display filenames, extension and MIME checks, magic-byte checks, and a 10 MB maximum upload size. The S3-compatible adapter accepts an explicit endpoint and region. Credentials stay on the API service and are never sent to the frontend or written to logs.

## Demo safety and known limitation

Keep all three processing providers set to `demo`. Do not connect government databases, real identity systems, production biometric providers, or invented APIs. Arbitrary real uploads must not be presented as verified identities. Reports and analytics remain decision-support output with explicit disclaimers.

Authentication users, sessions, and idempotency protections are persisted in the database. Horizontal deployment still requires managed PostgreSQL transaction behavior, shared private object storage, and deployment-specific validation; do not claim multi-replica readiness solely from local tests.

## Readiness checklist

| Area | Status | Notes |
| --- | --- | --- |
| Frontend build and routes | Ready | Standard Next.js deployment; API URL is configurable |
| Backend start and health | Ready with configuration | Bind to `0.0.0.0`; set the platform `PORT` |
| Database and migrations | Ready | Run `alembic upgrade head` against managed PostgreSQL |
| Redis | Ready with configuration | Runtime currently reserves Redis for coordination; provide the managed URL |
| Object storage | Ready with configuration | Private S3-compatible bucket and region required |
| Authentication | Ready with condition | DB-backed sessions and idempotency are implemented; validate managed PostgreSQL behavior before horizontal deployment |
| CORS and cookies | Ready with configuration | Exact HTTPS origin, secure cookies, SameSite=None cross-site |
| Demo safety | Ready | Keep deterministic demo providers and fictional data |
| Production face image | Ready for controlled image build | Use `apps/api/Dockerfile`; model checksum is verified during build |
| Render production face inference | Blocked | This repository has no validated Render image/model execution evidence |
| CI | Ready | Backend and frontend quality gates pass, including migration SQL validation |

Do not deploy until the actual frontend/API domains, managed service credentials, and private demo bucket have been selected and configured through the hosting providers' secret managers.
