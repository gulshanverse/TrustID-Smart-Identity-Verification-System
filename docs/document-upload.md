# TrustID document upload

Phase 5 implements **document ingestion only**. An authenticated officer starts a verification, selects one of the supported document categories, uploads a file, and receives a `READY_FOR_ANALYSIS` document record after server validation and object-storage persistence. This state means that the file was accepted and stored; it does not mean that the document is authentic, government verified, fraud-free, or analyzed.

## Supported inputs

The supported document types are Passport, Visa, National ID, Driving License, and Permit. The centralized file allowlist accepts PDF, JPEG/JPG, PNG, and WebP files up to **10 MB**. The API checks the extension, declared MIME type, size, emptiness, and magic bytes. Filenames are sanitized for display only, while object keys are generated from server-side UUIDs and never derived from user-controlled paths.

## Architecture and storage

The request path is frontend → versioned API → `DocumentService` → SQLAlchemy repository → PostgreSQL, with a separate `ObjectStorage` interface → MinIO/S3-compatible adapter for binary content. The S3 adapter receives credentials only from API configuration and stores objects in the configured private bucket. Database metadata is represented by `verifications`, `documents`, and `audit_events` tables; document binary content is not stored in PostgreSQL. Tests use an in-memory storage fake only for isolated storage behavior, while persistence tests exercise the repository against SQLite. If the S3 client or storage configuration is unavailable, the API returns a safe storage-unavailable error and does not claim success.

Start local infrastructure with `docker compose up -d postgres redis minio`. Configure the API using `.env` or the documented defaults, ensure the private `trustid-documents` bucket exists, and run `alembic upgrade head` from `apps/api`. The repository does not publish uploaded objects or return storage credentials or internal object keys to the browser.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/verifications` | Create a verification owned by the authenticated user. |
| `POST` | `/api/v1/verifications/{verification_id}/documents` | Upload a typed document using multipart form data (`document_type`, `file`). |
| `GET` | `/api/v1/verifications/{verification_id}/documents` | List documents after ownership authorization. |
| `GET` | `/api/v1/documents/{document_id}` | Read safe document metadata after ownership authorization. |
| `DELETE` | `/api/v1/documents/{document_id}` | Delete the stored object and mark metadata deleted. |

All endpoints require the existing cookie session and RBAC dependencies. Officers and supervisors have document create/read/delete permissions; auditors remain read-only for audit/report access, and administrators retain all permissions.

## Audit and privacy

Successful verification creation, document upload, and document deletion create safe audit events containing event type, actor, verification, document ID where applicable, status, and timestamp. The implementation does not log document bytes, OCR text, passport numbers, biometric information, credentials, or session tokens. Uploaded identity documents are treated as sensitive private artifacts and are never placed in browser storage, cookies, public URLs, or API response bodies.

## Phase 5 boundary

OCR, field extraction, quality scoring, tampering detection, face processing, risk scoring, government database access, automatic decisions, and production orchestration are intentionally deferred. `READY_FOR_ANALYSIS` is the handoff seam for Phase 6 OCR.

## Known limitations

The authentication service remains the repository's development-stage in-process session boundary. Document verification and metadata persistence use the existing SQLAlchemy session infrastructure in production. Actual object storage requires the configured MinIO/S3-compatible service; without it, tests should use the fake adapter and local API calls should show the storage-unavailable message rather than simulating a successful upload.
