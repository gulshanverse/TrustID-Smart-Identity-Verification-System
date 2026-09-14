# TrustID tampering detection foundation

Phase 7 adds a provider-neutral technical tampering analysis foundation after document ingestion and OCR. The flow is API → `TamperingService` → `ObjectStorage` retrieval and bounded preprocessing → `TamperingProvider` → `TamperingResult` → PostgreSQL findings/evidence and audit events. A result describes technical signals that may warrant review; it does not prove fraud, authenticity, criminality, or identity theft.

## Provider and scenarios

`TamperingProvider` receives TrustID domain models, document bytes, and optional OCR context. It does not expose cloud/vendor response classes. The configured default is `TAMPERING_PROVIDER=demo`, using the explicitly labeled `DEMO / SIMULATED` provider. Its deterministic scenarios are clean document, text manipulation, photo inconsistency, visa/stamp alteration, and metadata anomaly. A fixture must contain the matching `TRUSTID-TAMPERING:<SCENARIO>` marker; arbitrary uploaded files fail safely rather than receiving fabricated findings. Demo finding IDs are stable per scenario, but result IDs and timestamps remain run-specific.

The prototype score is `0.0` to `1.0` and means **strength of technical tampering signals only**. It is not a fraud probability, risk score, authenticity score, or decision. Findings use controlled types and severities (`INFO`, `LOW`, `MEDIUM`, `HIGH`) and careful language such as “Potential text manipulation detected” and “Review recommended.”

## Evidence and persistence

`tampering_results` stores status, technical signal score, overall confidence, provider/version, summary, document relationship, and timestamps. `tampering_findings` stores type, severity, confidence, explanation, and optional related OCR field. `tampering_evidence` supports multiple records per finding, including page, region, description, source reference, technical signal, and confidence. Migration `004_tampering_detection` adds foreign keys, indexes, cascade behavior, and audit linkage. Reprocessing creates a historical result rather than silently replacing earlier results; the API exposes the latest authorized result.

## API and authorization

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/documents/{document_id}/tampering` | `verification:workflow` | Run technical analysis with a controlled demo scenario. |
| `GET` | `/api/v1/documents/{document_id}/tampering` | `document:read` | Read the latest result for the owning user. |

The service confirms ownership, requires an active analysis lifecycle, retrieves bytes only through private `ObjectStorage`, validates format and size, optionally consumes the latest OCR context, and executes server-side. Audit events are `TAMPERING_STARTED`, `TAMPERING_COMPLETED`, and `TAMPERING_FAILED`; they contain safe identifiers and provider/status metadata, never document bytes or sensitive identity values.

## UI and security

The verification console now flows from document upload to OCR to tampering analysis. It shows actual processing/error states, a keyboard-accessible scenario selector, provider label, technical signal score, confidence, severity, explanations, related OCR fields, and textual evidence. Evidence is not represented as a fake image overlay. Raw OCR and identity values are not logged or placed in URLs/local storage. Preprocessing enforces inherited size limits, supported MIME/magic signatures, and malformed-document rejection before the provider runs.

Face verification, biometric matching, risk assessment, final fraud classification, automatic approval/rejection, officer decision automation, government or blacklist integrations, blockchain, and production forensic AI are not implemented. A future provider can replace the demo adapter without changing API, database, UI, or orchestration contracts.
