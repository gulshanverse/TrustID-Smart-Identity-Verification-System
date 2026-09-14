# TrustID cases and investigation workflow

Phase 10 operationalizes existing verification outputs as an auditable officer workflow. A case references one existing verification; it does not copy or replace the verification, OCR, validation, tampering, face, or risk records. **Cases and investigation records are operational workflow records. They do not independently establish fraud, criminality, or legal status.**

## Lifecycle and permissions

Cases move explicitly through `OPEN`, `UNDER_REVIEW`, `ESCALATED`, `RESOLVED`, and `CLOSED`. Closed cases are immutable for notes, evidence, assignment, decisions, and ordinary edits. Officers can work authorized cases, add notes and evidence, transition review states, and record human decisions. Supervisors can assign, resolve, and close cases. Auditors have read-only case visibility through the existing audit permission. Every operation performs server-side permission and ownership/assignment checks; frontend role labels are never trusted.

Priorities are operational fields: `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`. They do not represent criminality or an automatic decision. Case numbers are human-readable references such as `TRUST-2026-000001` while UUIDs remain internal identifiers.

## Evidence and timeline

Case creation from a verification automatically adds reference-only evidence for the linked document and any available OCR result, tampering result/finding, face verification result, and risk assessment. Evidence stores `source_type` and `source_id` plus a short safe summary; it does not copy raw OCR text, face images, embeddings, passwords, or secrets. Manually added evidence is accepted only when its underlying source record exists.

The timeline is a projection of existing audit events, including case creation, assignment, status changes, escalation, resolution, closure, evidence, notes, and decisions. Notes store the author, timestamp, and officer-provided body. Note additions and decisions are audited; rejection decisions require a reason.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/cases` | Create one case linked to an existing verification. |
| `GET` | `/api/v1/cases` | List authorized cases with search, status, priority, risk, limit, and offset filters. |
| `GET` | `/api/v1/cases/{case_id}` | Read case, evidence, notes, and timeline. |
| `PATCH` | `/api/v1/cases/{case_id}` | Update editable case metadata. |
| `POST` | `/api/v1/cases/{case_id}/assign` | Assign an officer or supervisor with assignment permission. |
| `POST` | `/api/v1/cases/{case_id}/status` | Execute an explicit lifecycle transition. |
| `POST` | `/api/v1/cases/{case_id}/decision` | Record an authenticated human decision: approve, review, or reject. |
| `GET/POST` | `/api/v1/cases/{case_id}/evidence` | Read or add reference-oriented evidence. |
| `GET/POST` | `/api/v1/cases/{case_id}/notes` | Read or add officer notes. |
| `GET` | `/api/v1/cases/{case_id}/timeline` | Read the safe audit timeline projection. |

## Safety boundaries

Risk is contextual evidence. TrustID does not automatically approve, reject, classify fraud, determine criminality, determine immigration or legal status, perform surveillance, infer demographics or emotion, run liveness, query government databases, use blockchain, or create hidden AI case prioritization. Officer decisions remain human-controlled, authenticated, timestamped, and audited. Demo examples are explicitly labeled `DEMO / SIMULATED` and do not represent real investigations.
