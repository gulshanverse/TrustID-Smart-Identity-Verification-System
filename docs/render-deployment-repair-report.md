# TrustID Render Deployment Repair Report

## Root Cause

The repository contains the backend packaging files under `apps/api` only. The API Dockerfile uses:

```dockerfile
COPY pyproject.toml ./
COPY app ./app
COPY scripts/provision_face_models.sh /usr/local/bin/provision-face-models
```

Therefore its Docker build context must be `apps/api`. The repository root does not contain `pyproject.toml` or `app/`. If Render uses repository root as the Docker build context while pointing to `apps/api/Dockerfile`, the build fails at the first `COPY` instruction before Python dependencies, OpenCV, model provisioning, or application startup are reached.

This is a shared Render configuration failure, not an independent application failure in each Phase 6–9 commit.

## Exact Render Configuration

Configure the Render backend as a Docker web service:

| Setting | Value |
|---|---|
| Runtime | Docker |
| Root Directory | `apps/api` |
| Dockerfile Path | `./Dockerfile` |
| Health Check Path | `/api/v1/health` |
| Auto-Deploy | Enabled if desired |

The effective build command is equivalent to:

```bash
docker build -f apps/api/Dockerfile apps/api
```

The build context must contain `pyproject.toml`, `app/`, and `scripts/`. The Dockerfile itself copies the provisioning script from `scripts/`; tests and migrations are not copied into the production image, but remain in the repository context for local validation and release checks.

A declarative Render configuration was added at [`render.yaml`](../render.yaml). It uses `sync: false` for database, Redis, object-storage, CORS, and demo-password values. No secrets were added to Git.

## Dockerfile and Model Provisioning Review

The Dockerfile:

1. Uses `python:3.12-slim`.
2. Installs `curl`, CA certificates, OpenCV runtime libraries, and OpenMP support.
3. Installs the package from the context-local `pyproject.toml`.
4. Provisions SFace and YuNet models through the repository script.
5. Verifies both downloads with SHA-256 checksums.
6. Starts Uvicorn on `0.0.0.0` using `${PORT:-8000}`.

The model provisioning script uses retrying HTTPS downloads, a bounded timeout, and checksum verification. The repair did not remove or weaken those controls.

## Health and Startup

The intended Render health path is unauthenticated `GET /api/v1/health`. It checks only process health and does not depend on OCR, face, tampering, liveness, or external providers. Database-dependent readiness remains available separately at `GET /api/v1/readiness`.

The Uvicorn command respects Render's `PORT` environment variable:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Production Configuration

The Render service must provide production database, Redis, private object-storage, CORS, cookie, and demo-password settings through Render's secret manager. The declarative file contains no secret values.

The existing demo/production/unavailable provider separation remains unchanged. Demo providers are explicit. Liveness remains `NOT_IMPLEMENTED`. No accuracy, external database verification, or forensic certainty is claimed.

## Validation Results

### Completed locally

- Repository structure inspected.
- `apps/api/Dockerfile` inspected.
- `apps/api/pyproject.toml` inspected.
- Model provisioning and checksums inspected.
- Deployment assumptions inspected.
- Render context diagnosis confirmed from actual file paths.
- Backend full regression suite: **113 passed, 2 skipped**.
- Frontend lint, TypeScript, tests, and production build: **passed; 4 frontend tests passed**.
- Ruff: **passed** for application and changed test files.
- MyPy: **passed**.
- Python compilation: **passed**.
- Alembic offline SQL generation: **passed through migration 015**.
- Git diff and secret-file checks: **passed**.

### Not executable in this environment

Docker is not installed or available in the Manus environment. Consequently, the following were not claimed:

- Docker image build.
- Base image pull.
- apt dependency installation inside the image.
- OpenCV installation inside the image.
- SFace download during image build.
- YuNet download during image build.
- Container startup.
- Container health response.
- Render deployment success.

Status: `DOCKER_VALIDATION_PENDING` and `RENDER_EXTERNAL_VALIDATION_PENDING`.

## Files Changed

- `render.yaml`
- `docs/deployment.md`
- `docs/render-deployment-repair-report.md`

No application logic, risk weights, evidence semantics, authentication behavior, migrations, provider boundaries, or model checksums were changed.

## Git State

The repair is committed and pushed as one focused deployment configuration change. Final branch, commit, remote parity, and working-tree state are verified in the delivery response.

## Final Status

> **DEPLOYMENT CONFIGURATION REPAIRED — DOCKER/RENDER VALIDATION PENDING**

The exact repository-level Render configuration problem is repaired and documented. A successful Render deployment must still be observed externally, and the Docker image must be built and run in an environment with Docker access.
