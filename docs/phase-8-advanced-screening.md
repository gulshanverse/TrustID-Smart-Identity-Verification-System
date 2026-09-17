# Phase 8 — Advanced Screening Intelligence & Officer Investigation

## Scope

Phase 8 extends the existing OCR, MRZ, validation, evidence, risk, case, audit, and officer-decision architecture. New logic is deterministic and advisory. It does not replace the authoritative risk engine, create a second scoring system, or allow an AI model to decide identity, fraud, eligibility, or the officer outcome.

## Implemented boundaries

The `app.domain.advanced_document_intelligence` module preserves each raw extracted value alongside a normalized value and rule version. Date, country, document-number, name, and gender normalization are conservative. Confidence is passed through only when a provider supplies it; unavailable confidence remains `null`.

Cross-field checks emit `MATCH`, `NO_MATCH`, `REVIEW`, or `NOT_AVAILABLE` with rule identifiers, versions, explanations, and provenance. Cross-document correlation compares only semantically comparable fields and labels mismatches as review signals, never as fraud.

The evaluation helper records dataset identity, a dataset fingerprint, sample count, commit SHA, environment, model version, threshold, timestamp, and limitations. Empty or unlabeled inputs produce `DATASET_VALIDATION_PENDING`; no production benchmark claim is generated.

Advanced forensic certainty and liveness are explicitly bounded. Existing technical tampering providers remain the source of technical signals. Liveness is `NOT_IMPLEMENTED` unless a separately validated PAD provider is configured; static face imagery is never labelled `LIVE`.

## Verification

Run backend Phase 8 tests with:

```bash
cd apps/api
pytest tests/test_phase8.py
```

The existing risk and Decision Intelligence implementations remain authoritative and advisory respectively. Phase 9 was NOT started.
