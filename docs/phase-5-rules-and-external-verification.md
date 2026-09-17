# TrustID Phase 5 — Rules and External Verification

## Status

**Complete with documented external blockers.** Phase 5 adds deterministic, versioned document rules, explicit validity evaluation, safe external-provider abstractions, normalized external evidence, an authenticated external verification endpoint, persistence of rule metadata, and officer-facing API metadata. No authorized government or immigration database was connected.

## Architecture

The implemented path is `document → OCR/MRZ → versioned rules → optional external provider → normalized Phase 3 evidence correlation → existing risk engine → officer review`. The rule engine and external provider are separate concerns. External verification is an enhancement and is never a prerequisite for local verification.

The existing `DocumentValidationProvider` seam remains in use. `RulesEngine` in `apps/api/app/domain/rules.py` produces deterministic `RuleResult` values. `DemoDocumentValidationProvider` adapts those values to the existing validation persistence model. `ExternalVerificationProvider` in `apps/api/app/domain/external_verification.py` defines normalized provider semantics without permitting arbitrary outbound URLs.

## Rule engine and catalog

Rules use the stable version `phase5-rules-v1`, and every result carries a rule ID, rule version, document type, field, condition, severity, status, explanation, observed value, and expected condition. Supported passport rules include required fields, technical passport-number format, ISO dates, non-future date of birth, expiry validity, and MRZ checksum availability/validation. Supported visa rules include required fields, entry validity, and a bounded technical stay-duration format. National ID, driving license, and permit remain recognized domain types but return `NOT_APPLICABLE` until an authoritative rule catalog is approved; no unsupported requirements were invented.

Missing values produce required-field failures or `NOT_AVAILABLE` where appropriate, not forgery conclusions. Country handling is limited to caller-supplied technical code shape in the API schema; no nationality or country risk scoring is implemented. An injectable `Clock` and `FixedClock` make date tests deterministic.

## External verification

The normalized query contains document type, document number, optional country code, and an optional non-raw date-of-birth reference. The current endpoint does not accept a provider URL, credentials, or arbitrary payload. Production mode is explicit and returns `NOT_AVAILABLE` when no authorized provider is configured. It never silently falls back to demo and never fabricates `VERIFIED` data.

The mock provider is named **Simulated External Verification**, marks every result `demo: true`, uses synthetic outcomes only, and creates a non-sensitive synthetic reference. Its statuses are `VERIFIED`, `NO_MATCH`, `UNKNOWN`, `NOT_AVAILABLE`, `UNAUTHORIZED`, and `ERROR`; these meanings are not conflated. A real provider adapter, if later approved, must be allowlisted, authenticated server-side, bounded by the configured timeout, and audited without raw identity payloads.

## Phase 3, risk, and decisions

`correlate()` now accepts an optional `ExternalVerificationResult` and emits `EXTERNAL_VERIFICATION` evidence. `NOT_AVAILABLE` remains `NOT_AVAILABLE`; `NO_MATCH` produces `EXTERNAL_RECORD_MISMATCH` for officer review and a zero new risk contribution. No second risk engine or hidden score was added. The existing deterministic risk engine remains authoritative.

Rule IDs, rule versions, observed/expected conditions, and provider versions are persisted with validation findings. Migration `011_phase5_rule_metadata` adds nullable metadata columns so older records remain readable and historical results retain their original rule context. Existing decision/case workflows remain human-controlled and immutable through their existing persistence path.

## API and officer review

The existing analysis API exposes `provider_version` and per-finding rule metadata (`rule_id`, `rule_version`, `field`, `observed`, `expected`). The new authenticated endpoint is:

`POST /api/v1/verifications/{verification_id}/external/verify`

It requires the existing verification-workflow permission and owner-scoped lookup. It returns provider, version, status, reason, timestamp, query reference, and an explicit demo marker. A production-default request returns `NOT_AVAILABLE` with the reason that no authorized external database provider is configured. The current investigation view already separates normalized evidence, provenance, findings, and risk; the API now supplies the rule details needed for a dedicated local-rules section.

## Audit and security

Existing ownership and RBAC dependencies protect the endpoint. Verification IDs are resolved through an owner-scoped query, so an unrelated user receives `404` rather than another user’s data. Provider credentials are not accepted by the frontend or persisted in query objects. No arbitrary HTTP client was added, so there is no new SSRF path. The provider contract is synchronous and bounded by `EXTERNAL_VERIFICATION_TIMEOUT_SECONDS` configuration (1–60 seconds); the current unavailable/mock adapters make no network calls. Raw query payloads and identity values are not logged.

## Testing

The repository regression suite passes **84 tests**, with **2 existing skips**. Frontend tests pass **4 tests across 2 files**, and frontend TypeScript typecheck passes. Phase 5 smoke checks confirm fixed-date validity evaluation, production `NOT_AVAILABLE`, and synthetic demo `VERIFIED`. Backend Ruff checks and Python compilation pass for modified modules. The migration is structurally linked after revision `010_ocr_intelligence_metadata`; live managed PostgreSQL/Render migration execution was not available in this sandbox.

## Carry-forward audit

| Previous phase | Item | Status | Resolved? | Evidence |
|---|---|---|---|---|
| Phase 1 | Local OCR/MRZ and deterministic extraction seams | EXISTS | Yes for repository tests | Existing OCR/MRZ tests remain green; production deployment is not claimed |
| Phase 2 | Face validation and provenance | EXISTS | No external deployment claim | Existing face tests remain green |
| Phase 2 | Liveness/PAD, demographic analysis, threshold calibration | BLOCKED | No | Requires a legitimate provider, datasets, governance, and operational validation; remains not implemented |
| Phase 3 | Evidence correlation and risk authority | EXISTS | Extended | External evidence now flows through existing `correlate()`; no second risk engine |
| Phase 4 | Forensics/tampering integration | EXISTS | Preserved | Existing tampering tests remain green; Render/resource validation remains not demonstrated |
| Phases 1–4 | Production deployment, real capture, legal/model review | BLOCKED | No | Requires Render, storage, hardware/capture, and organizational approvals not available here |

## Limitations and explicit claims policy

**NO AUTHORIZED GOVERNMENT DATABASE CONNECTED.** The repository contains no live government, passport, border, visa, police, blacklist, or immigration integration. Demo outcomes are synthetic and visibly labeled. No result is a legal determination, identity certainty, fraud confirmation, immigration decision, or officer decision. Production latency and real-world accuracy were not measured. The remaining deployment, liveness/PAD, cross-dataset, demographic, legal/provenance, real-capture, and forensic-production blockers must remain documented until independently demonstrated.
