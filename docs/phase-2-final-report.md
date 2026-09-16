# TrustID Phase 2 Final Completion Report

## 1. Executive Summary

Phase 2.1 has now been validated with actual local execution of the configured OpenCV SFace ONNX model. The production provider initializes the real model, detects faces, applies a quality gate, generates 128-dimensional normalized embeddings in memory, computes cosine similarity, applies configured decision thresholds, persists safe result metadata, and writes audit events. A local service-level production E2E run processed fictional reference and presented images through storage, ownership checks, reference extraction, real inference, comparison, persistence, and audit.

The final status is **COMPLETE WITH DEPLOYMENT BLOCKER**. The local production pipeline is verified. The current free-tier Render deployment is not validated for the native OpenCV/model runtime and must remain in demo mode until a suitable controlled runtime is provisioned.

The benchmark is intentionally not a success claim: the fictional corpus produced genuine similarity scores above the configured threshold, but also produced substantial impostor overlap. This is an important engineering finding. The implementation does not claim real-world biometric accuracy, legal identity, government verification, liveness, or spoof resistance.

## 2. What Was Actually Verified

The exact model artifact loaded by `ProductionFaceVerificationProvider` was executed locally. The model was used for real inference rather than mocked or replaced with a deterministic score. The service-level E2E run produced two persisted results and the expected start/completed audit events. Embeddings were generated in memory and were not persisted. The frontend build and API contract remain intact.

## 3. Architecture

The existing provider abstraction remains unchanged conceptually:

```text
FaceVerificationProvider
├── DemoFaceVerificationProvider
│   └── DEMO / SIMULATED fictional fixtures
└── ProductionFaceVerificationProvider
    ├── bounded image decode
    ├── Haar face detection
    ├── face quality gate
    ├── deterministic 112×112 BGR crop
    ├── OpenCV SFace ONNX inference
    ├── L2-normalized embedding
    ├── cosine similarity
    └── explicit decision policy
```

Production model initialization is explicit and never falls back to the demo provider. The model path and optional SHA-256 are configured through `FACE_MODEL_PATH` and `FACE_MODEL_SHA256`.

## 4. Model and Runtime Evidence

| Item | Measured value |
| --- | --- |
| Model filename | `face_recognition_sface_2021dec.onnx` |
| Model size | 38,696,353 bytes |
| Model SHA-256 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |
| Source | OpenCV Zoo repository path: `models/face_recognition_sface/face_recognition_sface_2021dec.onnx` |
| Runtime | OpenCV DNN `FaceRecognizerSF` on CPU |
| OpenCV version | 4.14.0 |
| Embedding dimension | 128 |
| Input | BGR crop resized to 112×112 |
| Integrity | Model existence/readability and optional SHA-256 verification implemented |
| Model loading time | 293.52 ms in final benchmark run |

The exact model-weight license and redistribution terms must still be reviewed against the model release before commercial redistribution. The Python/package license and model-weight license are separate concerns.

## 5. Synthetic Corpus

The benchmark corpus contains five fictional AI-generated portrait identities. No real photographs, identity documents, celebrities, or scraped images were used. Each identity has a reference and deterministic brightness, blur, rotation, dark, and small variants generated with OpenCV. The corpus is retained locally under `benchmarks/synthetic_faces/`; generated raw images are excluded from Git to avoid storing unnecessary biometric-like artifacts in the repository.

The benchmark is labeled **CONTROLLED SYNTHETIC VALIDATION**. It is not evidence of real-world FAR, FRR, fairness, demographic performance, government-grade performance, or population-level biometric accuracy.

## 6. Genuine-Pair Benchmark

The final run evaluated 30 same-identity rows. Twenty-two had a usable single-face/quality path and generated a real similarity score. Five were rejected by the quality gate and three were sent to review because multiple faces were detected. The 22 scored genuine pairs were all classified `MATCH`.

| Metric | Genuine scored pairs |
| --- | ---: |
| Count | 22 |
| Minimum | 0.888822 |
| Maximum | 0.999206 |
| Mean | 0.964342 |
| Median | 0.962745 |
| Standard deviation | 0.029918 |
| P05 | 0.919259 |
| P95 | 0.998207 |
| MATCH | 22 |
| REVIEW | 0 |
| UNAVAILABLE/quality | 5 |
| MULTIPLE_FACES/review | 3 |

## 7. Impostor-Pair Benchmark

The final run evaluated 120 cross-identity rows. Eighty-eight had a usable single-face/quality path and generated a real similarity score. Twenty were rejected by the quality gate and twelve were sent to review because multiple faces were detected. All 88 scored impostor pairs exceeded the current match threshold and were classified `MATCH`.

| Metric | Impostor scored pairs |
| --- | ---: |
| Count | 88 |
| Minimum | 0.462933 |
| Maximum | 0.861111 |
| Mean | 0.667048 |
| Median | 0.662625 |
| Standard deviation | 0.084669 |
| P05 | 0.542671 |
| P95 | 0.843074 |
| MATCH | 88 |
| REVIEW | 0 |
| UNAVAILABLE/quality | 20 |
| MULTIPLE_FACES/review | 12 |

This overlap is a material limitation and is not hidden. The synthetic identities are visually similar enough that this corpus does not support using the current threshold as evidence of safe operational verification. The benchmark validates execution and exposes calibration/data limitations; it does not justify real-world deployment.

## 8. Threshold Analysis

The production provider uses cosine similarity on L2-normalized embeddings. The current match threshold is `0.363`; the TrustID review-band floor is `0.30`. These are configurable engineering parameters, not Indian government, MHA, SSB, or universal biometric thresholds. The `0.363` value is treated as an OpenCV SFace reference-style parameter and must be revalidated with an authorized operational dataset before deployment.

The benchmark demonstrates strong overlap between the current synthetic genuine and impostor score distributions. No threshold was tuned after observing these results. The current policy is therefore retained as a documented implementation parameter, not presented as calibrated production policy.

## 9. Detection and Quality Validation

The provider detects zero, one, or multiple faces and never arbitrarily selects one from a multi-face image. A zero-face reference is unavailable; a multi-face reference is unavailable; a multi-face presented image produces `REVIEW`. The quality gate measures face area, Laplacian sharpness, brightness, and contrast.

| Metric | Current implementation | Meaning |
| --- | --- | --- |
| Face area | At least 80×80 pixels | Rejects very small face regions |
| Sharpness | Laplacian variance at least 20 | Rejects severe blur |
| Brightness | 35–225 mean grayscale | Rejects very dark/overexposed regions |
| Contrast | Standard deviation at least 18 | Rejects low-contrast regions |
| Detection | Haar, `scaleFactor=1.1`, `minNeighbors=12`, `minSize=40×40` | Requires exactly one face |

The final benchmark produced measured `READY`, `LOW_QUALITY`, and `MULTIPLE_FACES` outcomes. It also showed that synthetic/generated face images can trigger false secondary detections, which are correctly handled as review/unavailable rather than silently selected.

## 10. Preprocessing and Alignment

TrustID currently uses Haar bounding-box detection followed by a deterministic crop and resize to 112×112 BGR input. It does **not** use five-point landmark alignment or claim that it does. OpenCV SFace reference pipelines commonly use landmark-aware alignment; adding YuNet plus landmarks is a future improvement, but the current implementation is explicit about the limitation.

## 11. Reference Face Extraction

| Document type | Reference-face status |
| --- | --- |
| Passport image | Supported when exactly one detectable, quality-passing face exists |
| Passport PDF | Explicitly unavailable; bounded portrait extraction is not implemented |
| Visa | Explicitly unsupported/unavailable |
| National ID | Explicitly unsupported/unavailable |
| Driving licence | Explicitly unsupported/unavailable |
| Permit | Explicitly unsupported/unavailable |

The service does not use OCR text as a face, does not fabricate a reference image, and does not randomly choose a face.

## 12. Production Service E2E Evidence

The local production E2E harness used SQLite and in-memory private storage with fictional PNG/JPEG images and the real configured model.

| Evidence | Result |
| --- | --- |
| Provider initialized | PASS |
| Model SHA verified | PASS |
| Reference passport image uploaded | PASS |
| Reference face extracted | PASS |
| Genuine presented image | `MATCH`, similarity `0.979623`, quality `READY`, one face |
| Impostor presented image | `MATCH`, similarity `0.734584`, quality `READY`, one face |
| Persisted face results | 2 |
| Audit events | Started/completed for both runs |
| Embeddings persisted | No |
| Peak resident memory | 325,552 KB in this Python process |
| Total two-comparison elapsed time | 2,621.98 ms |

The impostor `MATCH` is a real model result and is deliberately reported as a limitation, not overwritten with an expected classification.

## 13. Failure-Path and Integrity Behavior

The provider explicitly fails for missing model files, unreadable files, SHA-256 mismatch, missing native runtime, malformed images, unsupported image data, and unusable reference faces. Production initialization errors are not converted to demo success. The service emits safe failure responses and audit events without returning stack traces, model paths, raw images, or embeddings.

## 14. Security and Privacy Audit

Raw face images are processed in memory and are not stored as part of a face result. Embeddings are generated in memory, compared, and discarded. Embeddings are not persisted, logged, or returned from the API. Existing ownership and permission checks remain in the service/repository path. Upload checks include extension, MIME, magic bytes, size, and malformed-image validation; production decoding adds dimension and pixel-count checks. No external cloud AI, LLM identity decision, vector database, blockchain biometric payload, or liveness claim is introduced.

## 15. API and Frontend

The existing authenticated face-verification API remains in place. The response exposes provider, result, similarity, quality, face count, safe evidence, and reason. It does not expose embeddings or raw tensors. The UI labels the provider returned by the API and distinguishes fictional demo scenarios from `REAL AI / PRODUCTION`. Liveness remains visibly `NOT_IMPLEMENTED`.

## 16. Performance and Memory

The final benchmark processed 150 pair rows. Timing statistics for the full provider call were:

| Metric | Value |
| --- | ---: |
| Count | 150 |
| Minimum | 271.41 ms |
| Mean | 717.53 ms |
| Median | 742.49 ms |
| P05 | 388.82 ms |
| P95 | 1,090.65 ms |
| Maximum | 1,411.71 ms |
| Model load | 293.52 ms |

Peak resident memory for the service E2E process was 325,552 KB. This measurement is from the sandbox Python process, not Render, and does not establish safe operation within a 512 MB free-tier service under concurrent load.

## 17. Deployment Status

**Local production biometric inference: VERIFIED.**

**Synthetic benchmark: VERIFIED, with material impostor overlap.**

**Application service E2E: VERIFIED locally.**

**Security/privacy boundaries: VERIFIED by code inspection and regression tests.**

**Render production inference: NOT VALIDATED.**

**Current Render mode: DEMO / SIMULATED.**

The free Render runtime should not be switched to production until the model, native OpenCV runtime, startup time, memory, cold start, and inference behavior are validated in that deployment environment or a dedicated worker is provisioned.

## 18. Test Results

| Check | Result |
| --- | ---: |
| Backend pytest | 81 passed, 2 skipped |
| Ruff | Passed |
| MyPy | Passed |
| Python compilation | Passed |
| Alembic migration head | `010_ocr_intelligence_metadata` |
| Frontend typecheck | Passed |
| Frontend lint | Passed |
| Frontend tests | 4 passed |
| Frontend production build | Passed |
| Real SFace model initialization | Passed |
| Real SFace synthetic benchmark | Passed with measured limitations |
| Production service E2E | Passed with measured impostor overlap |

## 19. Final Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Production provider exists | PASS | `ProductionFaceVerificationProvider` |
| Real SFace model loads | PASS | Local initialization and E2E |
| Model SHA verified | PASS | Configurable SHA-256; measured hash recorded |
| Real inference executed | PASS | 128-dimensional embeddings and real scores |
| Genuine benchmark | PASS | 22 scored genuine pairs |
| Impostor benchmark | PASS | 88 scored impostor pairs |
| Similarity distributions measured | PASS | JSON/CSV benchmark artifacts |
| Threshold documented | PASS | Match `0.363`, review floor `0.30` |
| Quality gate tested | PASS | READY, LOW_QUALITY, MULTIPLE_FACES observed |
| No-face handling | PASS | Explicit no-face/reference unavailable path |
| Multiple-face handling | PASS | No arbitrary selection; review/unavailable |
| Reference extraction | PASS | Passport image only, exactly one face |
| Unsupported documents explicit | PASS | Matrix and service behavior |
| API integration | PASS | Existing authenticated API route wired to provider |
| Persistence | PASS | Two E2E results persisted |
| Audit trail | PASS | Started/completed audit events persisted |
| Privacy checks | PASS | No embeddings/images persisted or returned |
| Failure paths | PASS | Safe model/image/provider failure behavior |
| Performance benchmark | PASS | 150 measured rows |
| Memory benchmark | PASS | 325,552 KB peak in sandbox E2E process |
| Full local production E2E | PASS | Storage → service → model → persistence → audit |
| Frontend integration | PASS | Typecheck, tests, build passed |
| Demo mode preserved | PASS | Existing suite and provider unchanged |
| No silent fallback | PASS | Explicit initialization failures |
| Liveness boundary | PASS | `NOT_IMPLEMENTED` |
| Render validation | BLOCKED | Free-tier native/model runtime not validated |

## 20. Known Limitations

The current SFace preprocessing uses a Haar crop rather than five-point landmark alignment. The synthetic corpus is small and visually similar, and the measured impostor overlap is unacceptable as operational identity evidence. Passport PDF portrait extraction is not implemented. Liveness and presentation-attack detection are not implemented. The model license and redistribution terms require release-specific review. Render free-tier performance and concurrency are not validated.

## 21. Final Phase 2 Status

# COMPLETE WITH DEPLOYMENT BLOCKER

Phase 2 has achieved its local validation goal: the real self-hosted face-verification pipeline executes end-to-end with actual fictional images, real SFace inference, measured genuine/impostor distributions, quality and detection handling, persistence, audit, API wiring, and frontend compatibility. The status is not a claim that the current threshold or corpus is suitable for real-world biometric deployment. The free deployment remains in demo mode until its runtime is independently validated.
