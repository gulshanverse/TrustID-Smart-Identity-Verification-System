# TrustID face verification foundation

Phase 8 adds a provider-neutral, photo-based face comparison foundation after document OCR and technical analysis. The flow is API → `FaceVerificationService` → private document retrieval and in-memory presented-photo validation → `DocumentFaceExtractor` → `FaceVerificationProvider` → persisted comparison result and safe audit metadata. The result describes whether the configured provider found the supplied photos sufficiently consistent; it does not establish legal identity, authenticity, liveness, fraud, or criminality.

## Provider and demo scenarios

The domain contract accepts a document-face artifact, a presented-face artifact, and an explicit scenario. `DemoFaceVerificationProvider` is labeled `DEMO / SIMULATED` and uses deterministic fictional outcomes: `MATCH`, `MISMATCH`, `REVIEW`, `NO_FACE`, `MULTIPLE_FACES`, and `LOW_QUALITY`. The presented image and document must contain explicit fixture markers; arbitrary photos cannot be turned into a fabricated match. The demo comparison threshold is `0.80` on a `0.0`–`1.0` similarity scale. It is a provider demo threshold, not an official government or industry standard.

Similarity means how similar the provider considers the two supplied face artifacts. Confidence means how confident the provider is in that comparison outcome. They are kept separate and are never combined with OCR confidence or tampering signals into a risk score.

## Face quality and extraction seams

Before comparison, the service validates MIME/magic bytes, size, and supported format. The presented image is limited to 5 MB and is processed in memory. The demo document-face extractor requires an explicit document fixture marker and returns a controlled quality result. Quality outcomes include `READY`, `NO_FACE`, `MULTIPLE_FACES`, `LOW_QUALITY`, and `UNSUPPORTED_IMAGE`. Advanced face detection, alignment, embeddings, and liveness are intentionally provider seams, not fake implementations.

## Persistence and API

`face_verifications` stores comparison status/outcome, similarity, confidence, provider metadata, safe summary/failure reason, quality states, face count, document/verification relationships, and timestamps. `face_verification_evidence` stores explainable, non-biometric evidence such as document-face availability, presented-face processing, face count, and threshold meaning. Raw images, embeddings, templates, and vectors are not stored in PostgreSQL. Migration `005_face_verification` adds foreign keys, indexes, cascade rules, and audit linkage. Repeated comparisons create historical result records; the read endpoint returns the latest authorized result.

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/documents/{document_id}/face-verification` | `verification:workflow` | Process one presented image server-side with an explicit demo scenario. |
| `GET` | `/api/v1/documents/{document_id}/face-verification` | `document:read` | Read the latest authorized result without biometric payloads. |

Audit events are `FACE_VERIFICATION_STARTED`, `FACE_VERIFICATION_COMPLETED`, and `FACE_VERIFICATION_FAILED`. They include actor/document/result/provider/outcome/status metadata only; face images, image bytes, embeddings, and biometric templates are excluded.

## UI, privacy, and limitations

The verification console adds a presented-face upload, explicit demo scenario selector, real preparing/comparing states, outcome, similarity, confidence, provider label, quality/failure reason, and evidence explanation. Uploaded-photo verification is labeled **PHOTO-BASED DEMO** / **DEMO MODE · SIMULATED** and is not liveness detection. Presented bytes remain server-side for the request and are not written to local storage or public object storage; the prototype does not retain them after processing.

Risk assessment, fraud classification, automatic approval/rejection, officer decision automation, demographic or emotion inference, surveillance, government biometric databases, identity blacklists, blockchain, and production biometric providers are not implemented. Production deployment requires appropriate legal, privacy, security, retention, and human-review controls.
