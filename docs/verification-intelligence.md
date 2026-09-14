# TrustID verification intelligence and risk assessment

Phase 9 adds a verification-level orchestration seam across the existing OCR, document validation, tampering, and face-verification results. The orchestrator does not replace the document-level APIs and does not perform new OCR, tampering, or biometric processing. It retrieves the latest authorized module outputs, validates structured OCR fields, maps each signal into deterministic factors, persists the factorized assessment, and exposes an explainable officer-facing result.

## Pipeline

`VerificationAnalysisService` coordinates: document availability → completed OCR → deterministic document validation → existing tampering result → existing face result → deterministic risk assessment. Missing prerequisites fail safely; the system never fabricates a clean tampering result, face match, or successful validation. Repeated analyses create historical validation and risk records rather than silently mutating an earlier assessment.

Document validation uses structured OCR values and metadata only. Demo rules check required fields, passport-number format, expiry or entry validity, and supported document type. No government, MHA, SSB, passport, police, blacklist, or external identity database is queried. External verification is represented as unavailable with zero automatic fraud contribution.

## Risk model

The prototype score is the sum of persisted, explainable contributions and is clamped to `0–100`. The illustrative levels are:

| Score | Level | Meaning |
| --- | --- | --- |
| 0–29 | LOW | No elevated prototype signal; officer review remains required. |
| 30–69 | REVIEW | Officer review is required before any decision. |
| 70–100 | HIGH | Elevated prototype signals require enhanced officer review. |

The current deterministic mappings are: validation passed/review/failed/unavailable = `0/15/30/20`; low OCR confidence = `10`; technical tampering contribution = the bounded technical score mapped to `0–25`; face match/review/mismatch/unavailable = `0/12/25/10`; external verification unavailable = `0`. Each persisted factor contains its name, source module, severity, contribution, explanation, and safe evidence reference. The score is reproducible from the stored factors and has no hidden ML or random component.

**The prototype risk score and thresholds are illustrative and are not official MHA/SSB scoring rules.** TrustID provides AI-assisted decision support and does not independently determine identity, fraud, criminality, immigration eligibility, or officer decisions. A mismatch, tampering signal, expired date, or high score is not proof of fraud.

## API

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/verifications/{verification_id}/analyze` | `verification:workflow` | Run the verification-level pipeline after module prerequisites complete. |
| `GET` | `/api/v1/verifications/{verification_id}/result` | `document:read` | Read the latest explainable analysis with module statuses, validation, and risk factors. |
| `GET` | `/api/v1/verifications/{verification_id}/risk` | `document:read` | Read the latest persisted risk assessment. |

Audit events include `VERIFICATION_ANALYSIS_STARTED`, `DOCUMENT_VALIDATION_COMPLETED`, `RISK_ASSESSMENT_COMPLETED`, `VERIFICATION_ANALYSIS_COMPLETED`, and `VERIFICATION_ANALYSIS_FAILED`. They contain IDs, statuses, and provider metadata only. Raw OCR text, face images, embeddings, passwords, and secrets are not included.

## Persistence and UI

Migration `006_risk_assessment` adds `document_validations`, `document_validation_findings`, `risk_assessments`, `risk_factors`, indexes, foreign keys, and audit linkage. The console now presents Document → OCR → Validation → Tampering → Face Verification → Risk Assessment. It shows score, level, recommendation, module statuses, factor severity/contribution/source/explanation, and a clearly separate human-controlled officer decision area. The UI never calculates or overrides the official score and does not show a completed score when orchestration fails.

Risk assessment does not implement fraud classification, liveness, surveillance, demographic inference, emotion recognition, government integrations, blockchain, automatic approval/rejection, or automatic officer decisions. Production use requires legal, privacy, security, retention, model governance, and human-review controls.
