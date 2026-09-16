# TrustID Phase 2 Final Completion Report

## Executive summary

Phase 2 adds an explicit `ProductionFaceVerificationProvider` using a locally provisioned OpenCV SFace ONNX embedding model, OpenCV Haar face detection, deterministic crop normalization, a quality gate, cosine similarity, and explicit `MATCH`, `REVIEW`, `MISMATCH`, and `UNAVAILABLE` semantics. The existing fictional demo provider remains unchanged and is selected only when `FACE_VERIFICATION_PROVIDER=demo`. Production initialization fails explicitly when the model is missing; it never falls back to demo.

This implementation is **COMPLETE WITH DEPLOYMENT BLOCKER** until the model file is provisioned in the deployed runtime. Local/container validation is the supported Phase 2 target. No liveness or presentation-attack detection is implemented.

## Architecture changes

The existing route → service → provider abstraction is preserved. Production selection is configuration-driven through `FACE_VERIFICATION_PROVIDER=production` and `FACE_MODEL_PATH`. The service validates uploaded bytes, retrieves the private stored document, checks ownership through the existing repository, extracts a reference face only for passport image documents, runs the production provider, persists metadata and safe evidence, and creates audit events. Raw images and embeddings are not persisted or returned.

## Model and library selection

OpenCV was selected because it provides a self-hosted CPU-compatible runtime, bundled Haar cascade deployment, and the `FaceRecognizerSF` interface for genuine SFace embeddings. SFace is materially more defensible than pixel comparison or handcrafted image hashes because the verification score is derived from model embeddings. The model is loaded from a configured local file; the application does not download weights at request time.

The model-weight license must be reviewed against the exact downloaded artifact before commercial redistribution. The OpenCV package license and the model-weight license are separate obligations. Deployment should pin the package and record the model SHA-256 in release metadata.

## Detection, quality, alignment, and reference extraction

The detector returns zero, one, or multiple faces. Zero faces produce `NO_FACE`; multiple faces produce `REVIEW` and no arbitrary face is selected. Quality checks cover minimum face area, Laplacian sharpness, brightness, and contrast. The current deterministic preprocessing crops the sole detected face and resizes it to 112×112 BGR input for SFace. It does not claim landmark alignment; future model-specific landmark alignment can be added without changing the provider contract.

Reference extraction currently supports **passport image files** only. A reference is accepted only when exactly one face is detected in the document image. Visa, national ID, driving licence, permit, and passport PDFs return an explicit unavailable/unsupported result rather than fabricating a reference face.

## Similarity and threshold

Embeddings are L2-normalized and compared with the dot product, equivalent to cosine similarity for normalized vectors. The configured threshold is `0.363`, with a review band beginning at `0.30`. These values are provider configuration, not a government or population-level biometric standard; they must be calibrated with the exact model, preprocessing, and controlled synthetic corpus before operational use. A score is never treated as identity certainty.

## Privacy and security

Presented images are processed in memory and discarded after comparison. Embeddings remain in memory only for the comparison and are not logged, stored, or exposed through the API. Audit events contain provider, status, and safe workflow references only. Existing upload validation remains in place, with production decoding additionally enforcing image dimensions and pixel count. Model loading is local and does not deserialize untrusted pickle files or call external AI services.

## Liveness boundary

`liveness=NOT_IMPLEMENTED` is recorded as evidence. The system does not claim physical presence, spoof resistance, deepfake detection, camera-injection resistance, or presentation-attack detection.

## Deployment feasibility

The OpenCV package and SFace weights are not suitable for assuming a 512 MB free web dyno without measurement and model provisioning. The deployed free-tier configuration should remain `FACE_VERIFICATION_PROVIDER=demo` until a dedicated, controlled runtime has the model file and has passed local/container validation. The exact status is: **real self-hosted verification implemented in code; deployed Render production biometric runtime not validated**.

## Tests and benchmark status

The existing regression suite continues to exercise the demo workflow and persistence boundaries. Production model execution requires the configured SFace ONNX file and fictional synthetic image fixtures. No real people, real identity documents, or fabricated benchmark measurements are included in this report. Benchmark output must be generated only after model provisioning and should record genuine/impostor distributions, face counts, quality, similarity, decision, timing, and peak memory. Synthetic results must be labeled controlled synthetic validation and must not be presented as real-world biometric accuracy.

## Acceptance status

| Criterion | Status | Evidence |
| --- | --- | --- |
| Production provider exists | PASS | `ProductionFaceVerificationProvider` |
| Genuine embeddings and mathematical comparison | PASS | OpenCV SFace + normalized cosine similarity |
| Multiple/no-face handling | PASS | Explicit detector branches |
| Quality gate | PASS | Size, blur, brightness, contrast |
| No silent demo fallback | PASS | Explicit provider construction failure |
| Reference extraction boundaries | PASS | Passport image only; unsupported returns unavailable |
| Liveness boundary | PASS | `NOT_IMPLEMENTED` evidence |
| No raw biometric persistence | PASS | Result schema stores metadata only |
| Local model execution | BLOCKED | Model file must be provisioned and benchmarked |
| Deployed Render runtime | BLOCKED | Free-tier model provisioning not validated |
| Full production E2E and benchmark | BLOCKED | Requires fictional image corpus plus model weights |

## Known limitations and future improvements

Landmark-based alignment, bounded passport PDF portrait extraction, a deterministic fictional face corpus, calibration tooling, and measured memory/performance benchmarking should be completed in the controlled biometric runtime before production enablement. Liveness remains outside Phase 2.
