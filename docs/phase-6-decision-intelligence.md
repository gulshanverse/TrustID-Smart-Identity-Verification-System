# TrustID Phase 6 — Decision Intelligence

## Status

**Complete with documented external blockers.** Decision Intelligence is an explainability and officer-assistance layer over persisted OCR/MRZ, validation, forensics, face verification, Phase 3 correlation, Phase 5 provider results, and the existing authoritative risk assessment. It is **not** an autonomous fraud detector, legal decision system, immigration decision engine, identity-certification authority, replacement for authorized databases, or replacement for officer judgment.

## Data flow and decision context

The service in `apps/api/app/domain/decision_intelligence.py` transforms normalized evidence into an evidence summary, contradictions, review priorities, missing-information entries, risk context, and provenance. The deterministic content is identified by `analysis_fingerprint`, a SHA-256 fingerprint over normalized evidence, findings, priorities, missing-information codes, risk context, correlation summary, and provider/rule versions. `generated_at` remains execution metadata and is excluded from the fingerprint, so identical source state and versions produce identical content fingerprints.

The risk context is copied from the persisted authoritative risk assessment. Phase 6 never recalculates the score, changes risk contributions, or creates a second risk engine. Risk factors retain their persisted contribution, source reference, explanation, and assessment version.

## Evidence categories

Evidence is grouped into `DOCUMENT`, `IDENTITY`, `FORENSICS`, `EXTERNAL`, and `CORRELATION`. Each item preserves source, status, severity, explanation, provider, version, and a rule ID when available. External statuses remain distinct. `NOT_AVAILABLE` is not converted to negative evidence; `UNKNOWN` is not `VERIFIED`; `NO_MATCH` is a review conflict rather than fraud confirmation.

## Contradictions and priorities

The service surfaces existing Phase 3 mismatches and external-record conflicts as contradictions. Face `NO_MATCH`, tampering signals, and document validation failures are signals or attention items; they are not automatically contradictions and never constitute proof of fraud. Priorities are `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW` workflow guidance only. Where a priority comes from normalized evidence, its `evidence_ids` reference the actual evidence item; IDs are never invented. No new numeric risk weights are introduced.

Missing information explicitly includes liveness/PAD and any OCR, validation, tampering, face, or external module whose persisted state is `NOT_AVAILABLE`. Decision Intelligence operates over all available persisted structured evidence and does not convert unavailable states into failure. Optional external results are persisted in `external_verifications` by migration `012_external_verification_results`; repeated provider calls reuse the latest result and do not trigger duplicate provider work.

## Historical officer decision snapshot

When an officer records `APPROVE`, `REVIEW`, or `REJECT`, migration `013_decision_context_snapshot` stores a safe structured `decision_context` on the immutable `case_decisions` row. The snapshot contains the Phase 6 version and fingerprint, risk score/band/version and factors, evidence IDs, correlation and priority codes, missing-information codes/statuses, and provenance. It excludes `generated_at`, raw provider payloads, biometric embeddings, face or document images, unnecessary PII, and provider secrets. Regenerating current analysis therefore cannot change the historical context used by an officer decision.

## API and UI

Authenticated owner-scoped endpoints:

- `GET /api/v1/verifications/{verification_id}/decision-intelligence` with existing document-read permission.
- `POST /api/v1/verifications/{verification_id}/decision-intelligence` with existing verification-workflow permission.

The POST route writes at most one `DECISION_INTELLIGENCE_COMPLETED` audit event per verification and actor. Both routes use an owner-scoped verification lookup, return safe errors, and expose no raw provider payloads. The investigation page now loads the decision-intelligence response and shows priorities, missing information, contradictions, evidence categories, provider/rule provenance, and the authoritative risk context. It never clicks or changes `APPROVE`, `REJECT`, or `REVIEW` decisions.

## Phase 5 integrity audit

Phase 5 has one authoritative rule interpretation: `RulesEngine` produces rule results and `DocumentValidationProvider` adapts them to the existing validation contract. The existing risk engine remains the only risk engine. Production external verification remains explicitly unavailable without authorized configuration; demo results remain simulated; no arbitrary URL or frontend credential path exists. Rule metadata is persisted by migration `011_phase5_rule_metadata`, and normalized external results are now persisted by migration `012_external_verification_results`.

## Security and privacy

Access is authenticated, permission-checked, and owner-scoped. IDs cannot be used to read another owner’s verification. No arbitrary outbound request, SSRF-capable URL, frontend credential, raw biometric embedding, raw identity payload, raw DOB, passport number, or provider secret is logged by Phase 6. Audit metadata contains only verification ID, version/provider, status, and timestamps. Repeated analysis recomputes from persisted structured evidence and does not create duplicate risk records.

## Validation

The repository backend suite passes **94 tests with 2 existing skips**, including focused fingerprint, evidence-link, signal-semantics, partial-evidence, and officer-snapshot tests. Ruff, MyPy, Python compilation, frontend tests, frontend typecheck, production build, and migration-chain validation are run as part of final verification. Local test results do not establish production latency, biometric accuracy, forensic accuracy, demographic fairness, or legal authority.

## Carry-forward blockers

| Phase | Item | Status | Resolved? | Evidence | Remaining blocker |
|---|---|---|---|---|---|
| 1 | Render OCR deployment, Tesseract/Poppler production availability, operational OCR testing | DEPLOYMENT | No | Repository tests only | Render/infrastructure execution |
| 2 | Render face validation, liveness/PAD, cross-dataset, demographic, threshold calibration, real capture, SFace legal/provenance review | EXTERNAL SERVICE / DATASET / HARDWARE / LEGAL/GOVERNANCE | No | Existing local tests and documented provider seams | Authorized models, datasets, hardware, deployment, governance |
| 3 | Evidence correlation and risk authority | REPOSITORY | Yes | Existing correlation, fingerprint, and snapshot tests | No remaining Phase 6 repository blocker; production validation remains outside this repository |
| 4 | Production forensic resources, operational testing, threshold validation | DEPLOYMENT / DATASET | No | Existing tampering tests | Production environment and benchmark ground truth |
| 5 | Authorized government/external database, production provider, external security validation | EXTERNAL SERVICE / LEGAL/GOVERNANCE | No | Production adapter truthfully returns `NOT_AVAILABLE`; simulated provider is labeled | Authorized provider, credentials, allowlist, security review |

**NO AUTHORIZED GOVERNMENT DATABASE CONNECTED.** No Phase 6 result is a legal, identity, fraud, immigration, or officer decision.

## Version

Decision Intelligence version: `phase6-decision-intelligence-v1`.
