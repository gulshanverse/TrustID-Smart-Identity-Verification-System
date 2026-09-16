# TrustID Phase 2.4 Face Detection Coverage Report

## Final status

**COMPLETE WITH DEPLOYMENT BLOCKER**

Phase 2.4 investigated the input, detector, quality, alignment, and SFace pipeline without replacing SFace, changing verification thresholds, modifying the LFW protocol, or starting Phase 3. The central Phase 2.3 finding was reproduced: Haar detection has effectively zero LFW coverage. The investigation identified the blur gate as the dominant YuNet bottleneck. A development-fold sweep showed that a blur threshold of 5.0, while preserving brightness, contrast, face-size, detector, alignment, and threshold controls, raises useful YuNet coverage substantially. The untouched 6,000-pair rerun confirmed the improvement.

The selected configuration is retained as a **candidate configuration**, not as an automatic production default. Haar remains the current default. Production biometric detection remains **NOT READY** because the benchmark represents one authorized dataset, cross-dataset evaluation remains blocked, liveness is not implemented, and Render inference is not validated.

## 1. Phase 2.3 baseline

The immutable Phase 2.3 aggregate artifact was copied to `benchmarks/phase24_baseline_snapshot.json` before Phase 2.4 results were generated. It preserves the historical result without overwriting it.

The Phase 2.3 baseline was Haar with 2/3,000 genuine pairs scored and 0/3,000 impostor pairs scored. YuNet with the 20.0 blur gate scored 164/3,000 genuine pairs and 116/3,000 impostor pairs. The SFace model hash, YuNet model hash, review threshold `0.30`, and match threshold `0.363` were preserved.

The Phase 2.4 full rerun also reproduced the Haar baseline at 2 genuine and 0 impostor scores. Its exact failure breakdown is included below.

## 2. LFW input characteristics

The official LFW loader supplied RGB `float32` arrays with values normalized to 0–1. The Phase 2.4 benchmark used the loader's `resize=2.0` representation, producing 250×188×3 images. This was required because the source representation at `resize=1.0` is 125×94 and fails TrustID's existing 160-pixel minimum dimension validation.

A 100-pair development sample contained 200 images. Its mean grayscale brightness was 125.67, mean contrast was 42.19, and mean Laplacian sharpness was 12.41. The sharpness median was 10.28, with a 5th percentile of 5.05 and a 95th percentile of 25.61. This directly explains why the prior sharpness threshold of 20 rejected much of the LFW representation.

The source arrays were deterministically converted to 8-bit RGB, converted to BGR for OpenCV, and encoded as JPEG quality 95 before entering the TrustID provider. No sharpening, contrast enhancement, hallucination, manual crop, identity alteration, or pair removal was performed.

## 3. Input normalization

The provider continues to use safe OpenCV decoding into BGR `uint8`. It rejects malformed images, dimensions below 160 pixels, images exceeding the pixel limit, and unsupported upload MIME types at the API boundary. The benchmark normalization is deterministic and exists only to bridge the scikit-learn loader representation to the real image-byte provider contract.

No EXIF transformation was required for the LFW arrays. No grayscale-only path was introduced. No aggressive enhancement was introduced. The normalization is therefore considered **technically justified and low risk**.

## 4. Failure breakdown methodology

Every pair was attempted with both reference and presented images. An unavailable pair was not counted as a genuine rejection or impostor acceptance. Failure causes were retained by stage: detector/no-face, multiple-face handling, face-size, blur, exposure/contrast, decode/dimension errors, and provider exceptions. Unavailable attempts remained in the coverage denominator.

The provider now exposes an internal non-persistent trace for decode, detector, quality, alignment, and SFace timings. The trace is not returned by the API and is not persisted.

## 5. Haar detector analysis

Haar was evaluated at its existing `scaleFactor=1.1`, `minNeighbors=12`, and `minSize=(40,40)` configuration. Deterministic box padding of 8% and 12% did not recover useful development-fold coverage. Haar remained dominated by reference-side no-face detection.

The full Phase 2.4 Haar result was:

| Stage or outcome | Count | Percentage of 6,000 pairs |
| --- | ---: | ---: |
| Reference no face | 5,654 | 94.233% |
| Reference blur failure | 205 | 3.417% |
| Presented no face | 85 | 1.417% |
| Reference face too small | 29 | 0.483% |
| Multiple-face/reference selection failure | 12 | 0.200% |
| Presented blur failure | 12 | 0.200% |
| Exposure/contrast failure | 1 | 0.017% |
| Scored | 2 | 0.033% |

The Haar pipeline remains unsuitable for LFW coverage. This is detector/input evidence, not evidence that SFace itself fails.

## 6. YuNet detector analysis

YuNet confidence thresholds 0.60 and 0.90 were preserved in the development sweep. They produced the same low coverage when the 20.0 blur gate remained active, showing that detector confidence was not the primary bottleneck on the development fold. The selected final candidate retains confidence 0.90.

YuNet supplied five landmark points to `FaceRecognizerSF.alignCrop`. Alignment was executed on 5,752 full-run scored pairs. No landmark ordering or coordinate-system failure was observed. The selected candidate uses the original detector box and the existing five-point alignment path without arbitrary crop selection.

## 7. Detector parameter experiments

The development sweep used the first official LFW fold only for selection. The final evaluation remained the complete untouched 10-fold protocol.

| Configuration | Genuine coverage | Impostor coverage | Main finding |
| --- | ---: | ---: | --- |
| Haar baseline | 0.00% | 0.00% | Detector failure dominates |
| Haar + 8% padding | 0.00% | 0.00% | Padding did not solve detector failure |
| Haar + 12% padding | 0.00% | 0.00% | Padding did not solve detector failure |
| YuNet 0.60, blur 20 | 4.00% | 2.33% | Blur gate dominates |
| YuNet 0.90, blur 20 | 4.00% | 2.33% | Blur gate dominates |
| YuNet 0.90, blur 5 | 97.00% | 96.00% | Candidate selected for untouched rerun |
| YuNet 0.90, no blur gate | 99.67% | 98.67% | Higher coverage, but removes an existing safety gate |
| YuNet 0.90, no brightness gate | 4.00% | 2.33% | No material improvement |
| YuNet 0.90, no contrast gate | 4.00% | 2.33% | No material improvement |
| YuNet 0.90, relaxed face size | 4.00% | 2.33% | No material improvement |

The 5.0 candidate was chosen because it retained the blur gate rather than removing it entirely. It was selected using the development fold before the final full rerun and not by inspecting final-test scores.

## 8. Bounding-box experiments

Haar and YuNet were evaluated with 0%, 8%, and 12% deterministic box padding on development data. Padding slightly changed the small scored subset but did not address the dominant Haar no-face failure or the YuNet blur bottleneck. No padding was promoted. The production default remains `FACE_BOX_PADDING=0.0`.

## 9. Face-size handling

The existing minimum face-area gate is 6,400 pixels, equivalent to 80×80. A development experiment using 1,600 pixels did not improve coverage because blur failures occurred first. The face-size gate was therefore not lowered.

This preserves the quality gate and avoids converting low-resolution evidence into apparently valid biometric comparisons.

## 10. Quality-gate audit

The existing checks remain face size, Laplacian sharpness, brightness, and contrast. Development results identified sharpness as the bottleneck. Brightness, contrast, and face-size ablations did not materially improve coverage while the blur threshold remained 20.0.

The selected change is a configurable blur threshold with a conservative default of 20.0. The benchmark candidate uses 5.0. This lets deployment configuration remain explicit and prevents an accidental quality-gate removal.

## 11. Controlled quality ablation

The no-blur ablation produced 99.67% genuine and 98.67% impostor coverage on the development fold. It was not selected because it eliminates the existing blur safety check. The blur-5 candidate produced 97.00% genuine and 96.00% impostor coverage on development data while retaining the blur rule.

The brightness, contrast, and face-size ablations remained near 4% coverage. These checks were not the cause of the low coverage and were not relaxed.

## 12. Alignment analysis

The YuNet path uses the existing five landmarks and OpenCV `alignCrop`. The full candidate run recorded `alignCrop` for all 5,752 scored pairs. SFace embeddings remained 128-dimensional, normalized, and non-persistent. Haar continued to use deterministic crop-and-resize preprocessing.

No alignment redesign was necessary. The main problem was the quality gate applied before SFace inference.

## 13. Full 6,000-pair LFW rerun

The final candidate run processed the complete official protocol:

- 3,000 genuine pairs;
- 3,000 impostor pairs;
- 6,000 total pairs;
- no failed pair removed;
- no threshold changed;
- no final-test tuning;
- no raw image or embedding retained.

### Coverage comparison

| Pipeline | Genuine scored | Genuine coverage | Impostor scored | Impostor coverage |
| --- | ---: | ---: | ---: | ---: |
| Phase 2.3 Haar / Phase 2.4 Haar | 2 / 3,000 | 0.0667% | 0 / 3,000 | 0% |
| Phase 2.3 YuNet blur 20 | 164 / 3,000 | 5.4667% | 116 / 3,000 | 3.8667% |
| Phase 2.4 YuNet blur 5 | 2,908 / 3,000 | **96.9333%** | 2,844 / 3,000 | **94.8000%** |

## 14. Final candidate failure breakdown

| Failure type | Count | Percentage of all pairs |
| --- | ---: | ---: |
| Reference blur failure | 119 | 1.983% |
| Presented blur failure | 105 | 1.750% |
| Reference no face | 6 | 0.100% |
| Presented no face | 10 | 0.167% |
| Reference exposure/contrast | 4 | 0.067% |
| Presented exposure/contrast | 4 | 0.067% |
| Scored | 5,752 | 95.867% |

## 15. Verification metrics

The candidate produced AUC **0.998223** over 2,908 scored genuine and 2,844 scored impostor pairs. This is a substantial sample, but it remains an LFW-only result and does not establish production biometric accuracy or fairness.

The candidate approximate EER point was threshold **0.25829**, with TPR/TAR 0.992435, FAR/FPR 0.007736, and FRR 0.007565. This is a **CANDIDATE** analysis point only. It was not promoted and was not used to tune the final run.

### Threshold 0.30

- TPR/TAR: 0.988996
- FAR/FPR: 0.001758
- FRR: 0.011004
- TNR: 0.998242

### Threshold 0.363

- TPR/TAR: 0.975585
- FAR/FPR: 0.000000
- FRR: 0.024415
- TNR: 1.000000

Coverage context is mandatory: these values use 2,908 genuine and 2,844 impostor scored pairs, while 248 pair attempts were unavailable.

## 16. Genuine and impostor score distributions

The candidate genuine score mean was 0.627645, with median 0.639705 and 95th percentile 0.809137. The impostor score mean was 0.037579, with median 0.036233 and 95th percentile 0.191134. The maximum impostor score was 0.326743, below the unchanged 0.363 match threshold in this run.

These scores are reported as aggregate statistics only. Individual pair identities and biometric vectors were not retained.

## 17. Runtime

| Pipeline | Initialization | Successful mean | Successful P95 | Unavailable mean |
| --- | ---: | ---: | ---: | ---: |
| Haar | 264.34 ms | 103.38 ms | 116.96 ms | 10.75 ms |
| YuNet blur-5 | 240.87 ms | 46.55 ms | 54.02 ms | 7.64 ms |

The overall latency is not used as successful verification latency because it includes early failures. The YuNet candidate was successful on 5,752 pairs and materially improved useful coverage.

## 18. Memory

The previous local production E2E measured peak RSS near 325,000 KiB. Phase 2.4 did not change the SFace model or introduce a new model. This is a local measurement only. Render compatibility remains unvalidated and is not claimed.

## 19. Security

Model SHA-256 validation, missing-model failure, wrong-model failure, MIME validation, magic-byte handling, size limits, malformed image handling, authentication, authorization, ownership checks, audit logging, and no-silent-demo-fallback behavior remain intact. Phase 2.4 did not weaken security checks to increase coverage.

The new quality controls are configuration fields with explicit conservative defaults. An invalid box-padding value fails provider initialization. Face embeddings are still not persisted or returned by the API.

## 20. Privacy

LFW raw data was temporary and remained outside Git. The temporary cache was deleted after the final run. No raw image, crop, debug image, embedding, vector, biometric cache, archive, or personal-name list was committed. Only aggregate JSON and CSV artifacts, code, and reports are retained.

## 21. Regression tests

The existing backend and frontend regression suites remain the required gate. Phase 2.4 also validates provider initialization with correct and incorrect model hashes, explicit missing-model behavior, configuration defaults, and the full local production E2E path.

Liveness remains **NOT_IMPLEMENTED**. No anti-spoofing, replay detection, deepfake detection, or presentation-attack detection is claimed.

## 22. Engineering decision

The detector/input investigation supports YuNet plus `alignCrop` with a blur threshold of 5.0 as the strongest measured candidate. It improves genuine coverage from 5.4667% to 96.9333% and impostor coverage from 3.8667% to 94.8000% without changing SFace or the verification thresholds.

However, this is not enough to automatically switch the production default. The result is from one benchmark family, cross-dataset validation remains unavailable, and operational liveness is absent. Haar remains the default for compatibility. YuNet blur-5 is a documented **candidate configuration** for future authorized deployment validation.

**PRODUCTION BIOMETRIC DETECTION = NOT READY**

## 23. Acceptance matrix

| Requirement | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Phase 2.3 baseline | PASS | Baseline snapshot and Haar rerun | Historical artifact preserved |
| LFW full protocol | PASS | 6,000-pair full rerun | No failed pair removed |
| Input analysis | PASS | `phase24_input_analysis.json` | Aggregate sample only |
| Haar baseline | PASS | Full Haar result | Coverage remains unusable |
| YuNet baseline | PASS | Development and prior full results | Existing blur gate reproduced |
| Detector parameter analysis | PASS | Development sweep | 0.60 and 0.90 preserved |
| Input normalization | PASS | Deterministic RGB/BGR/JPEG bridge | No enhancement |
| Quality-gate audit | PASS | Blur identified as bottleneck | Other gates retained |
| Quality ablation | PASS | Blur, brightness, contrast, size | No-blur not promoted |
| Alignment validation | PASS | 5,752 `alignCrop` outcomes | SFace unchanged |
| Coverage improvement | PASS | 0.0667% to 96.9333% genuine | Candidate only |
| Full LFW rerun | PASS | 6,000 pairs | Complete protocol |
| Threshold evaluation | PASS | 0.30 and 0.363 | Unchanged |
| ROC/AUC | PASS WITH LIMITATION | AUC 0.998223 | LFW-only |
| FAR/FRR/TPR | PASS WITH LIMITATION | Threshold table | Coverage stated |
| EER | PASS WITH LIMITATION | Candidate 0.25829 | Not promoted |
| Runtime | PASS | Stage and outcome timing | Local CPU only |
| Memory | PASS LOCALLY | Prior E2E RSS | Not Render validation |
| Security | PASS | Existing and new provider checks | No weakening |
| Privacy | PASS | No biometric raw data committed | Temporary cache deleted |
| API E2E | PASS | Existing production E2E | Local only |
| Database regression | PASS | Existing suite | No schema change |
| Frontend regression | PASS | Existing typecheck/lint/test/build | No new biometric claims |
| No silent fallback | PASS | Explicit provider selection | — |
| Model hash validation | PASS | Correct/wrong/missing checks | — |
| Embedding non-persistence | PASS | Existing E2E | — |
| Render status | BLOCKED | Not run on Render | DEMO / SIMULATED |
| Liveness status | NOT_IMPLEMENTED | No liveness module | No anti-spoof claim |

## 24. Remaining blockers

The remaining blockers are authorized cross-dataset evaluation, operational capture testing, demographic analysis, liveness and presentation-attack detection, production concurrency/memory validation, and legal review for operational biometric use. The threshold remains unchanged until those gaps are addressed.

## References

[1]: https://vis-www.cs.umass.edu/lfw/ "Labeled Faces in the Wild dataset project"

[2]: https://vis-www.cs.umass.edu/lfw/lfw.pdf "Labeled Faces in the Wild: A Database for Studying Unconstrained Face Recognition"

[3]: https://people.cs.umass.edu/~elm/papers/lfw_update.pdf "Labeled Faces in the Wild updates and reporting procedures"

[4]: https://docs.opencv.org/4.13.0/d0/dd4/tutorial_dnn_face.html "OpenCV DNN face detection and recognition tutorial"
