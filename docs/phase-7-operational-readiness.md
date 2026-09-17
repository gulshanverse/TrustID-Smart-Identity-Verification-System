# TrustID Phase 7 — Operational Readiness

## Scope and authority

Phase 7 hardens the existing monolithic FastAPI verification boundary. It does not add a queue, microservices, Kafka, Kubernetes, LLM decisioning, government integration, or a second risk engine. The deterministic risk engine remains the sole authority for risk contributions. Decision Intelligence remains advisory, and officer decisions remain human actions.

## Verification lifecycle

Verification analysis uses the existing persisted verification lifecycle with deterministic transitions:

| State | Meaning |
|---|---|
| `PENDING` | Verification exists and is awaiting analysis prerequisites. |
| `PROCESSING` | One analysis worker has claimed the verification. Duplicate claims are rejected. |
| `COMPLETED` | Risk and correlation results were persisted successfully. A completed result may still contain explicit `NOT_AVAILABLE` evidence for optional capabilities. |
| `FAILED` | An attempted analysis failed. The failure is distinct from an unavailable provider or missing optional evidence and may be retried. |

Repeated analysis after persisted validation and risk results is idempotent and returns the existing authoritative risk result without creating duplicate risk records or terminal analysis events. A verification already claimed as `PROCESSING` is rejected rather than executed concurrently by the same application boundary.

The API analysis response reports `COMPLETED` for a complete run and `PARTIAL` when OCR, validation, tampering, or face capability is unavailable. Partial output retains normalized evidence and explains what remains unresolved; unavailable modules are not converted into negative findings.

## Health and readiness

`GET /api/v1/health` is a liveness endpoint. It confirms that the process is serving requests and returns only service, environment, version, and a process check.

`GET /api/v1/readiness` is a readiness endpoint. It checks the relational database with a bounded `SELECT 1` and returns `503` with a generic message if the required dependency is unavailable. It does not expose connection strings, credentials, stack traces, or internal topology. Optional provider capabilities remain explicit `NOT_AVAILABLE` results and do not make liveness fail.

## Observability

The middleware emits an `X-Request-ID` response header. Verification analysis logs include only UUID references, terminal outcome, risk level, provider names and versions, safe exception type, and elapsed milliseconds. Uploaded bytes, OCR payloads, raw identity documents, face images, embeddings, credentials, and unnecessary personal data are not logged.

## Error and evidence semantics

The system preserves the distinction between `NOT_AVAILABLE`, `UNKNOWN`, `NO_MATCH`, `FAILED`, `ERROR`, `UNAUTHORIZED`, and invalid input. A provider error is not negative evidence. A quality failure is not an identity mismatch. Missing metadata is not tampering. An unavailable face capability remains `NOT_AVAILABLE` through evidence normalization and Decision Intelligence.

## Deployment boundary

Local validation uses deterministic fictional fixtures and SQLite where appropriate. The repository does not claim live PostgreSQL migration execution, Render execution, Vercel execution, managed Redis availability, private object-storage availability, production OCR readiness, authorized external verification, liveness/PAD, or production forensic accuracy without deployment-specific evidence.

## Validation record

Phase 7 validation must include the complete backend suite, focused lifecycle/readiness/partial-evidence tests, Ruff, MyPy, Python compilation, migration graph checks, frontend typecheck/lint/tests/build, authorization and IDOR regression coverage, upload/resource-bound checks, and a final diff/security review. Concurrency claims are limited to the infrastructure actually exercised; sequential duplicate-operation tests are not concurrency validation.
