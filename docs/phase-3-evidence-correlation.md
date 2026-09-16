# TrustID Phase 3 — Verification Intelligence and Evidence Correlation

## Purpose

Phase 3 adds a deterministic evidence-correlation layer over the existing OCR, MRZ, document-validation, tampering, face, and risk modules. It does not replace those providers or create an automatic identity, authenticity, fraud, or officer decision.

## Normalized evidence

Each normalized item contains a deterministic evidence identifier, verification identifier, source module, evidence type, status, severity, optional confidence and score, human-readable explanation, machine-readable reason code, provenance, and creation timestamp. Confidence is copied only from an existing provider result; the correlation layer does not invent confidence values.

Supported source modules include `OCR`, `MRZ`, `DOCUMENT_VALIDATION`, `TAMPERING`, `FACE`, and `RISK`. The normalized statuses are `PASS`, `FAIL`, `REVIEW`, `NOT_AVAILABLE`, and `INCONCLUSIVE`.

## Correlation rules

The current rules are explicit and deterministic. OCR/MRZ field-consistency failures create field-level findings such as `MRZ_OCR_PASSPORT_NUMBER_MISMATCH` with high severity and a risk contribution of 20. A tampering technical signal creates `TAMPERING_SIGNAL` with medium severity and a risk contribution of 15. A face provider `NO_MATCH` creates `FACE_NO_MATCH` with high severity and a risk contribution of 25. Positive or unavailable module results remain evidence without being converted into unsupported conclusions.

The language intentionally uses **inconsistency**, **contradiction**, **suspicious technical signal**, and **review required**. A high-severity finding does not mean that a person is fraudulent.

## Provenance

Every evidence item and finding reports its producing module, provider, implementation version, and rule when applicable. The layer uses actual provider metadata already exposed by the repository; it does not fabricate external model or vendor versions.

## API and officer view

The existing `POST /api/v1/verifications/{verification_id}/analyze` and `GET /api/v1/verifications/{verification_id}/result` responses now include `correlation_summary`, normalized `evidence`, and `findings`. The authorized officer-facing investigation view at `/console/investigation` loads the existing result endpoint and displays findings, severity, risk contribution, source, provider, version, and rule provenance without repeating sensitive identity values.

## Auditability and reproducibility

The existing analysis-started, analysis-completed, analysis-failed, validation, risk, and module audit events remain authoritative. A successful run additionally records `VERIFICATION_CORRELATION_COMPLETED` with the deterministic engine provider label. Evidence and finding identifiers are deterministic for the verification and rule key, and finding ordering is fixed by severity and code. Re-running analysis does not create a separate correlation workflow; it recomputes the same internal representation from the latest persisted module results.

## Scope limitations

The current implementation does not infer demographics, liveness, fraud, identity, or external-database truth. It does not persist raw images, embeddings, or sensitive field values in logs. Persistence of normalized evidence as dedicated database rows can be added later if retention, indexing, and access-control requirements are approved; the current API representation is derived from authorized persisted module results and existing audit records.
