# TrustID Phase 2 — Final Face Verification Audit

## 1. Executive Summary

**PHASE 2 — COMPLETE WITH DOCUMENTED EXTERNAL BLOCKERS**

TrustID Phase 2 contains a real local production face-verification provider using OpenCV YuNet/Haar detection, quality gates, SFace embeddings, optional landmark alignment, cosine similarity, explicit match/review/no-match/unavailable semantics, model checksum validation, ownership checks, audit persistence, and no embedding persistence.

The strongest measured candidate is YuNet plus `FaceRecognizerSF.alignCrop` with a candidate blur threshold of 5.0. The complete LFW protocol produced 2,908/3,000 genuine scores and 2,844/3,000 impostor scores, with AUC 0.998223. These results are local, LFW-specific evidence and do not establish real-world biometric accuracy, fairness, liveness, legal approval, or production capacity.

The repository now includes a checksum-verifying production Docker image path, cached provider initialization, a process-local inference lock, synthetic operational testing, local concurrency measurement, model provenance documentation, and this final audit. Render execution, cross-dataset validation, demographic analysis, liveness/PAD, and legal model-provenance approval remain external blockers.

## 2. Current Architecture

The provider abstraction remains:

```text
FaceVerificationProvider
  ├── DemoFaceVerificationProvider
  └── ProductionFaceVerificationProvider
        ├── Face detection
        ├── Quality gate
        ├── YuNet landmark alignment or Haar crop-resize
        ├── SFace embedding
        ├── Cosine similarity
        ├── Decision engine
        ├── Optional liveness boundary
        └── Safe result
```

The API selects the provider explicitly from `FACE_PROVIDER`. The configured provider is cached once per API process, so production model weights are not reloaded per request. Production inference is serialized through a process-local lock because OpenCV detector state is mutable and the current deployment architecture uses one API instance.

## 3. Production Face Pipeline

| Stage | Implementation | Status |
|---|---|---|
| Decode | OpenCV image decode into BGR `uint8` | PASS |
| Detection | Configurable Haar or YuNet | PASS WITH LIMITATION |
| Face count | No-face and multiple-face rejection | PASS |
| Quality | Size, blur, brightness, contrast | PASS |
| Alignment | YuNet five-point `alignCrop`; Haar crop-resize | PASS |
| Embedding | OpenCV SFace, normalized 128-dimensional vector | PASS |
| Similarity | Cosine similarity | PASS |
| Decision | MATCH, REVIEW, MISMATCH, UNAVAILABLE | PASS |
| Liveness | Explicitly unavailable | NOT_IMPLEMENTED |

## 4. Detector Decision

The current compatible candidate is YuNet at confidence 0.90. Haar remains the safe existing default until deployment and broader validation criteria are met.

The complete LFW comparison was:

| Detector path | Genuine coverage | Impostor coverage | Successful scored pairs | Local successful latency |
|---|---:|---:|---:|---:|
| Haar, blur 20 | 0.0667% | 0% | 2 | 103.38 ms mean |
| YuNet + alignCrop, blur 5 | 96.9333% | 94.8000% | 5,752 | 46.55 ms mean |

The evidence supports YuNet as the **experimental candidate** and not automatically as a production-ready model. The Docker path supports controlled deployment, but Render has not been validated.

## 5. SFace Model

| Field | Value |
|---|---|
| Model | `face_recognition_sface_2021dec.onnx` |
| Runtime | OpenCV `FaceRecognizerSF` |
| Embedding dimension | 128 observed locally |
| Threshold | 0.363 match; 0.30 review |
| Persistence | Embeddings are not stored or returned |
| Integrity | SHA-256 verified before load |

## 6. Model SHA / Provenance

SFace SHA-256 is `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79`.

YuNet SHA-256 is `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.

Both assets are provisioned from the OpenCV Zoo source paths by [`apps/api/scripts/provision_face_models.sh`](../apps/api/scripts/provision_face_models.sh) and verified in [`apps/api/Dockerfile`](../apps/api/Dockerfile). Model license, training-data provenance, intended-use restrictions, and commercial-use interpretation require legal review. No commercial clearance is claimed.

**LEGAL / MODEL PROVENANCE REVIEW = OPEN**

## 7. Face Quality Pipeline

The default quality controls are:

- Minimum face region: 6,400 pixels, equivalent to 80×80.
- Blur threshold: configurable; current candidate is 5.0, conservative default remains 20.0.
- Brightness: 35–225.
- Contrast: standard deviation at least 18.
- Box padding: 0.0 by default.

The development sweep found blur/sharpness was the dominant LFW coverage bottleneck. Brightness, contrast, and face-size ablations did not materially improve coverage when blur remained at 20.0. Removing the blur gate entirely was not selected because it weakened an existing safety control.

## 8. Alignment

YuNet provides five landmark points and the provider calls OpenCV `FaceRecognizerSF.alignCrop`. The full LFW candidate run recorded `alignCrop` for 5,752 scored pairs. Haar uses deterministic crop-resize and is not claimed to provide landmark alignment.

## 9. Verification Thresholds

Thresholds were not changed:

| Threshold | Value |
|---|---:|
| Review floor | 0.30 |
| Match | 0.363 |

The LFW candidate analysis point near EER was 0.25829 but was not promoted. Threshold calibration remains insufficient for operational biometric deployment.

## 10. Synthetic Validation

The existing fictional corpus includes reference faces and controlled variants. The final operational harness covers frontal, blur, low light, overexposure, low contrast, compression, rotation, partial crop, small face, multiple faces, no face, corrupted bytes, and unsupported-format payloads. Every result is classified by provider stage and retains no raw artifact in the committed output.

The synthetic corpus contains fictional generated assets only. It is not evidence of demographic fairness or real-world performance.

## 11. LFW Validation

The final benchmark used the official LFW 10-fold image-restricted pair structure: 6,000 total pairs, 3,000 genuine, and 3,000 impostor. Unavailable attempts remained in the coverage denominator. No raw LFW data, names, pair identities, or embeddings were committed.

The benchmark loaded LFW pairs through the configured dataset loader and deterministically converted the resulting arrays into the 8-bit RGB/BGR image representation required by the TrustID pipeline. Any floating-point normalization used during benchmark loading was benchmark-side preprocessing and must not be interpreted as a property of the raw LFW dataset. The configured `resize=2.0` representation produced 250×188 arrays for this run; this is a loader result, not an inherent raw-dataset image property.

YuNet candidate results:

| Metric | Value |
|---|---:|
| Genuine scored | 2,908 / 3,000 |
| Impostor scored | 2,844 / 3,000 |
| Genuine coverage | 96.9333% |
| Impostor coverage | 94.8000% |
| AUC | 0.998223 |
| Genuine mean score | 0.627645 |
| Impostor mean score | 0.037579 |
| Successful mean latency | 46.55 ms |
| Successful P95 latency | 54.02 ms |

At threshold 0.30: TPR 0.988996, FAR 0.001758, FRR 0.011004, TNR 0.998242.

At threshold 0.363: TPR 0.975585, FAR 0.000000, FRR 0.024415, TNR 1.000000.

## 12. Cross-Dataset Validation

**BLOCKED.** VGGFace2, CelebA, and IJB-C were not processed because official access, license, intended use, or protocol suitability was unresolved or distribution was unavailable. No uncertain mirror, scraped collection, or random Internet face dataset was used.

## 13. Demographic / Subgroup Analysis

**BLOCKED / NOT AVAILABLE.** No legally and technically authorized evaluation dataset with trustworthy subgroup labels was available for this run. No demographic attributes were inferred from images. No fairness claim is made.

## 14. Operational Capture Testing

**PASS WITH LIMITATION — LOCAL ONLY.** The controlled synthetic operational harness exercises the failure conditions listed in the brief. It uses fictional repository fixtures and does not represent real capture subjects, camera sensors, field lighting, or operational document workflows.

The final dual-pipeline run showed that the existing fictional fixture is detected by Haar in some conditions but is not detected by YuNet in the tested synthetic fixture. This is retained as a measured detector/fixture limitation, not converted into a success. The Haar path is the current default for compatibility. The LFW run remains the evidence for YuNet coverage.

## 15. Liveness / PAD

**NOT_IMPLEMENTED.** No presentation-attack detector, replay detector, anti-spoofing model, or liveness provider was added. The UI and API do not equate face detection with liveness. The frontend explicitly shows `Liveness / PAD: NOT IMPLEMENTED`.

## 16. Production Deployment Validation

The repository now provides a deterministic production image path:

1. `apps/api/Dockerfile` installs the native OpenCV runtime.
2. `scripts/provision_face_models.sh` downloads pinned model files.
3. SHA-256 is checked during image build.
4. A checksum failure stops the build.
5. `FACE_PROVIDER=production` never falls back to demo.

Actual Docker and Render execution were **not available in this sandbox**. Render model loading, startup, memory, request latency, and logs are therefore **BLOCKED**, not inferred from local execution.

## 17. Runtime Benchmarks

Local model initialization was approximately 211–264 ms in the measured runs. YuNet successful LFW pair latency was 46.55 ms mean and 54.02 ms P95. These are local measurements using the sandbox CPU and do not represent Render capacity.

## 18. Memory / Concurrency

Provider caching and a process-local inference lock were added to prevent model reload on each API request and to protect mutable OpenCV state. Local concurrency was measured by the operational harness at 1, 5, 10, and 20 requests using fictional input. Because the YuNet synthetic fixture was unavailable at the reference-detection stage, these particular concurrency samples are failure-path timing, not successful production throughput.

| Pipeline | Level | Success rate | P95 | Peak RSS |
|---|---:|---:|---:|---:|
| Haar | 1 | 0% on fixture | 545 ms | 433 MB |
| Haar | 5 | 0% on fixture | 3,087 ms | 436 MB |
| Haar | 10 | 0% on fixture | 5,453 ms | 436 MB |
| Haar | 20 | 0% on fixture | 10,864 ms | 450 MB |
| YuNet candidate | 1 | 0% on fixture | 382 ms | 720 MB |
| YuNet candidate | 5 | 0% on fixture | 1,661 ms | 727 MB |
| YuNet candidate | 10 | 0% on fixture | 3,235 ms | 727 MB |
| YuNet candidate | 20 | 0% on fixture | 6,568 ms | 728 MB |

The successful local production E2E remains the evidence for real inference: it produced genuine and impostor result rows and persisted no embeddings. These load numbers must not be interpreted as Render capacity.

**RENDER CONCURRENCY = BLOCKED.** Horizontal capacity is not claimed. The deployment guide continues to prohibit multiple replicas because sessions are in-process.

## 19. Security Audit

Confirmed or preserved:

- Explicit provider selection.
- No production-to-demo fallback.
- Model checksum validation.
- Upload MIME and size validation.
- OpenCV decode and dimension checks.
- No-face and multiple-face handling.
- Authentication, RBAC, and ownership checks.
- Audit events without sensitive payloads.
- No embedding database column or API field.
- No raw images or embeddings in application logs.
- Safe exception messages at the API boundary.
- No frontend secrets.
- No third-party biometric API.

Rate limiting and distributed session storage are not implemented. The supported deployment remains a single API instance until those operational controls are added.

## 20. Privacy Audit

No raw faces, face crops, embeddings, vectors, identity names, LFW pair identities, or temporary model downloads were committed. Temporary external dataset caches were deleted. Aggregate JSON, CSV, and Markdown artifacts contain no biometric vectors or individual identity records.

## 21. API Semantics

The API distinguishes:

- `MATCH`
- `REVIEW`
- `MISMATCH`
- `UNAVAILABLE`

Model unavailable and unusable input are not represented as `NO_MATCH`. Provider errors produce a safe unavailable response at the HTTP boundary. Demo and production provider labels remain explicit.

## 22. Frontend Evidence

The face UI displays the provider label, provider version, similarity only when produced, result status, quality evidence, detector/alignment context, and `NOT IMPLEMENTED` for liveness/PAD. The page continues to state that face comparison does not prove identity, authenticity, fraud, or liveness.

## 23. Test Results

The final regression run after the Phase 2 finalization changes produced:

- Backend: 82 passed, 2 skipped.
- Frontend: 4 passed.
- Ruff: passed.
- MyPy: passed.
- Python compilation: passed.
- Alembic validation: passed.
- Frontend typecheck, lint, and build: passed.
- Local production E2E: passed with no embeddings persisted.
- Model integrity verification: SFace and YuNet SHA-256 checks passed; provisioning script syntax passed.


## 24. Known Limitations

The system is not a legal identity authority. It does not provide liveness, PAD, demographic fairness, real-world operational accuracy, cross-dataset generalization, Render capacity, horizontal scaling, or legal model clearance.

## 25. External Blockers

1. Render/Docker production execution is unavailable in the current environment.
2. Cross-dataset access and permission gates remain unresolved.
3. No authorized demographic-label evaluation set is available.
4. Liveness/PAD has no validated compatible implementation.
5. Model provenance and commercial-use legal review remain open.
6. Real operational capture and field-device testing are unavailable.

## 26. Production Readiness Assessment

**Local production provider: PASS WITH LIMITATION.** It loads verified models, performs real inference, returns explicit decisions, and avoids embedding persistence.

**Production deployment: BLOCKED.** The image path is prepared, but the target Render environment has not executed the image.

**Operational biometric deployment: NOT READY.** Threshold calibration, liveness, authorized cross-dataset evidence, demographic analysis, legal review, and production capacity validation remain incomplete.

## 27. Exact Git Commit

The Phase 2 finalization implementation and regression evidence were committed at `fb59a0ca41f496ad3d2a8ce678be3481d94dc70e`. The documentation-only commit that records this line is the subsequent repository HEAD reported with the delivery.

## Status Matrix

| Area | Status | Evidence | Limitation |
|---|---|---|---|
| Real detection | PASS WITH LIMITATION | Local YuNet/Haar providers | Render not validated |
| Face quality | PASS | Size, blur, brightness, contrast gates | Candidate blur threshold needs deployment review |
| Alignment | PASS | YuNet five-point `alignCrop` | Local only |
| SFace embedding | PASS | Real 128-D local inference | Model legal review open |
| Verification | PASS WITH LIMITATION | Cosine similarity and explicit outcomes | Threshold calibration insufficient operationally |
| Synthetic benchmark | PASS WITH LIMITATION | Controlled fictional corpus | Not real subjects |
| LFW | PASS WITH LIMITATION | Full 6,000-pair official protocol | One dataset family |
| Cross-dataset | BLOCKED | Official gates documented | Access/terms/protocol barriers |
| Demographic analysis | BLOCKED | No authorized labels | No fairness claim |
| Operational testing | PASS WITH LIMITATION | Synthetic condition matrix | No field capture |
| Liveness | NOT_IMPLEMENTED | Explicit UI/API boundary | No PAD model |
| Production deployment | BLOCKED | Verified Docker path prepared | Render unavailable |
| Memory | PASS WITH LIMITATION | Local E2E and local harness | Render memory unknown |
| Concurrency | PASS WITH LIMITATION | Local 1/5/10/20 harness | Render/horizontal capacity unknown |
| Security | PASS WITH LIMITATION | Tests, checks, safe failures | Rate limiting not implemented |
| Privacy | PASS | No embeddings/raw external data committed | Operational retention policy needs deployment review |
| Model provenance | PASS WITH LIMITATION | Pinned source and SHA documentation | Legal/commercial review open |
| Tests | PASS WITH LIMITATION | Backend/frontend/static gates | Docker build unavailable |

## Final Decision

**PHASE 2 — COMPLETE WITH DOCUMENTED EXTERNAL BLOCKERS**
