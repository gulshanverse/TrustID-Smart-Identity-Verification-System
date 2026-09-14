# TrustID OCR extraction

Phase 6 adds a provider-neutral OCR foundation. An authorized user can process a document that is `READY_FOR_ANALYSIS`; the API retrieves the private object through the `ObjectStorage` abstraction, runs the configured provider, persists the OCR result, fields, evidence, and safe audit events, and returns the structured result. A successful OCR result means **text and fields were extracted**. It does not mean that the document is authentic, government verified, fraud-free, or approved.

## Provider architecture

The orchestration boundary is API → `OCRService` → `OCRProvider` → persisted `OCRResult`. Providers use TrustID domain models rather than vendor SDK response objects. `DemoOCRProvider` is selected with `OCR_PROVIDER=demo` and is explicitly labeled `DEMO / SIMULATED`. It processes only files containing the explicit `TRUSTID-DEMO-OCR:` fixture marker; arbitrary uploaded documents fail safely rather than receiving fabricated fields. A future production adapter can implement the same `OCRProvider.process(document, content)` contract without changing API or UI contracts. No cloud OCR credentials are included.

## Data model

`ocr_results` stores status, raw OCR text, language, overall confidence, provider name/version, document relationship, and timestamps. `ocr_fields` stores normalized field name/value, source text, and field confidence. `ocr_evidence` stores supported traceability references such as page, line, text, and offsets. OCR runs are retained, so reprocessing creates a new result rather than destroying historical output. A completed run transitions the source document to `OCR_COMPLETE`, the handoff for future validation.

Confidence values are normalized from `0.0` to `1.0`. OCR confidence and field confidence are extraction-quality signals only; they are not authenticity, fraud, or risk scores. Current demo passport fields are fictional: full name, passport number, nationality, date of birth, expiry date, and gender. Visa and generic document categories have similarly fictional demo fields.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/documents/{document_id}/ocr` | Execute synchronous OCR for an owned ready document. Requires verification workflow permission. |
| `GET` | `/api/v1/documents/{document_id}/ocr` | Retrieve the latest owned OCR result. Requires document-read permission. |

The backend performs authentication and ownership checks before retrieval or processing. Provider names and result metadata are returned, but storage credentials, provider credentials, filesystem paths, and internal topology are never exposed. Raw OCR text is returned only from the authorized result endpoint and is not placed in URLs, browser storage, or logs.

## Audit and privacy

OCR execution creates `OCR_STARTED`, `OCR_COMPLETED`, and `OCR_FAILED` audit events with actor, document, verification, provider, status, result ID where available, and timestamp. Raw text and field values are intentionally excluded from audit logs. PostgreSQL persists the OCR entities through Alembic migration `003_ocr_extraction`; document binaries remain in private object storage.

## UI behavior

After upload, `/console/verify` shows `READY FOR ANALYSIS` and a real `Start OCR` action. Processing displays the actual request state. Completion shows provider label, overall confidence, field count, structured fields, field confidence, evidence page where available, and collapsed raw OCR text. The interface uses extraction language such as “Text extracted successfully” and “Ready for validation”; it does not claim authenticity, fraud detection, government verification, or automatic approval.

## Local development and limitations

Run `alembic upgrade head` from `apps/api` after starting the existing PostgreSQL/MinIO stack. The test suite uses SQLite for repository integration tests and an in-memory object storage fake only as an isolated test adapter. The default provider is deterministic demo mode, not production OCR. To process a demo fixture, the stored PDF must contain the explicit marker; arbitrary uploads intentionally return a safe OCR failure until an authorized real provider adapter is configured.

Tampering detection, image forensics, face verification, biometric processing, risk scoring, government integrations, blockchain, fraud classification, automatic decisions, and officer decision automation are not implemented in Phase 6.
