# TrustID SIH demo deployment guide

This guide prepares the existing TrustID prototype for a controlled SIH 2026 demonstration deployment. It is **not** a production authorization for real government identity data. Use fictional demo identities and documents only.

## Deployment architecture

Deploy the Next.js frontend to Vercel, the FastAPI API to one Render or equivalent service instance, PostgreSQL to a managed PostgreSQL provider, Redis to a managed Redis provider, and documents to a private S3-compatible bucket such as Cloudflare R2. MinIO remains a local-development dependency. Do not configure multiple API replicas because authentication and sessions currently use in-process memory.

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
| `FACE_PROVIDER` | `demo` |
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

The migration chain currently ends at `009_verification_lifecycle`. The CI-safe validation command is:

```bash
alembic upgrade --sql head
```

## Backend start command

Use one backend instance with the platform-provided port:

```bash
cd apps/api
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Configure the platform health check as `GET /api/v1/health`. It does not require authentication. The API reads database, Redis, storage, provider, CORS, and cookie settings from environment variables.

## Frontend deployment

From `apps/web`, Vercel should use the standard Next.js build and start behavior. Set `NEXT_PUBLIC_API_URL` before the build. Required checks are `npm install`, `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build`. The browser no longer falls back to a localhost API URL when the variable is absent; a missing value will therefore fail visibly instead of silently targeting a developer machine.

## CORS and cookies

The API must list the exact frontend HTTPS origin in `CORS_ORIGINS`; never use `*` with credentialed requests. Because Vercel and a separately hosted API are cross-origin, use `SESSION_COOKIE_SECURE=true` and `SESSION_COOKIE_SAMESITE=none`. Keep the session cookie HttpOnly and use HTTPS on both services. Logout revokes the in-process token and clears the cookie.

## Storage and uploads

Use a private bucket and do not expose MinIO publicly. The API uses UUID-derived storage keys, safe display filenames, extension and MIME checks, magic-byte checks, and a 10 MB maximum upload size. The S3-compatible adapter accepts an explicit endpoint and region. Credentials stay on the API service and are never sent to the frontend or written to logs.

## Demo safety and known limitation

Keep all three processing providers set to `demo`. Do not connect government databases, real identity systems, production biometric providers, or invented APIs. Arbitrary real uploads must not be presented as verified identities. Reports and analytics remain decision-support output with explicit disclaimers.

Authentication and session storage are in-process. This is acceptable only for a **single backend instance** during the SIH demonstration. Do not enable autoscaling or multiple replicas. A persistent authentication/session implementation is required before any real production use.

## Readiness checklist

| Area | Status | Notes |
| --- | --- | --- |
| Frontend build and routes | Ready | Standard Next.js deployment; API URL is configurable |
| Backend start and health | Ready with configuration | Bind to `0.0.0.0`; set the platform `PORT` |
| Database and migrations | Ready | Run `alembic upgrade head` against managed PostgreSQL |
| Redis | Ready with configuration | Runtime currently reserves Redis for coordination; provide the managed URL |
| Object storage | Ready with configuration | Private S3-compatible bucket and region required |
| Authentication | Ready with condition | One API instance only; in-process sessions are not horizontally scalable |
| CORS and cookies | Ready with configuration | Exact HTTPS origin, secure cookies, SameSite=None cross-site |
| Demo safety | Ready | Keep deterministic demo providers and fictional data |
| CI | Ready | Backend and frontend quality gates pass, including migration SQL validation |

Do not deploy until the actual frontend/API domains, managed service credentials, and private demo bucket have been selected and configured through the hosting providers' secret managers.
