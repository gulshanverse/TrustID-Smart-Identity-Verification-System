# TrustID Phase 2.2 External Validation and Alignment Report

## Status

**COMPLETE WITH DEPLOYMENT BLOCKER — SYNTHETIC/LOCAL VALIDATION SCOPE**

The user explicitly declined processing real-face public datasets. Therefore LFW access and external-dataset validation are **BLOCKED BY PRIVACY SCOPE**, not silently substituted. Phase 2.2 was completed within the approved synthetic/local boundary: the existing Haar baseline was re-run, a YuNet + five-point SFace alignment experiment was implemented and measured, threshold/ROC-style analysis was generated, and the result was used to decide whether the aligned path should replace the baseline.

This report does not claim public-benchmark accuracy or real-world biometric performance.

## Executive Summary

The real OpenCV SFace recognition model remains operational. The new aligned experiment uses OpenCV YuNet face detection and `FaceRecognizerSF.alignCrop`, which is the strongest clean local upgrade supported by the existing OpenCV runtime. On the current fictional corpus, the aligned experiment produced materially better score ranking among the small scored subset, but its detection/quality coverage was much worse than the Haar baseline. It therefore **must not replace the baseline in production yet**. The aligned implementation is available behind configuration for controlled follow-up work; the default remains the more-covered Haar path.

The previous Phase 2.1 synthetic result is preserved as historical evidence: genuine mean `0.964342`, impostor mean `0.667048`, and `88/88` scored impostors classified as `MATCH`.

## Dataset Selection and License Gate

| Item | Result |
| --- | --- |
| Requested first external dataset | Labeled Faces in the Wild (LFW) |
| Official protocol source reviewed | Huang and Learned-Miller, *Labeled Faces in the Wild: Updates and New Reporting Procedures*, UM-CS-2014-003 |
| Processing decision | **Blocked** |
| Reason | User explicitly instructed: “Do not use real-face public datasets; limit Phase 2.2 to synthetic/local validation.” |
| Raw public face images downloaded | No |
| Dataset files committed | No |
| Public ROC/FAR/FRR claim | Not made |

The LFW protocol documentation confirms that LFW is a face-verification benchmark with matched/different pairs and defined reporting procedures. Because this approved task scope excludes real-face public datasets, no LFW pair protocol was executed.

## Model Details

| Item | Value |
| --- | --- |
| Recognition model | OpenCV SFace `face_recognition_sface_2021dec.onnx` |
| Recognition SHA-256 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |
| Recognition size | 38,696,353 bytes |
| Runtime | OpenCV DNN `FaceRecognizerSF` on CPU |
| OpenCV | 4.14.0 |
| Embedding dimension | 128 |
| Detector experiment | OpenCV YuNet `face_detection_yunet_2023mar.onnx` |
| YuNet SHA-256 | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| YuNet size | 232,589 bytes |
| YuNet source | OpenCV Zoo model repository |
| YuNet alignment | Five-point landmarks through `FaceRecognizerSF.alignCrop` |

Model weights remain deployment-provisioned and ignored by Git. SHA-256 verification is enforced when configured. No model weights or image corpus are committed.

## Baseline Pipeline

```text
Haar detector
→ bounding box
→ quality gate
→ crop
→ resize 112×112
→ SFace feature
→ normalized cosine similarity
```

The baseline is the existing TrustID implementation and was not modified for its comparison run.

## Aligned Pipeline

```text
YuNet detector
→ bounding box + five landmarks
→ FaceRecognizerSF.alignCrop
→ SFace feature
→ normalized cosine similarity
```

The aligned path is selected with `FACE_DETECTOR=yunet`, model path/hash settings, and a configurable detector confidence threshold. It preserves the existing provider abstraction, in-memory embeddings, quality handling, and no-arbitrary-face-selection behavior.

## Local Synthetic Protocol

The same five fictional AI-generated identities used in Phase 2.1 were used. Each reference had deterministic brightness, blur, rotation, dark, and small variants. The protocol evaluated same-identity pairs as genuine and cross-identity pairs as impostor. All rows were retained, including `LOW_QUALITY`, `MULTIPLE_FACES`, and unavailable outcomes.

This is not an external benchmark. It is a controlled implementation comparison.

## Baseline Results

| Metric | Genuine | Impostor |
| --- | ---: | ---: |
| Total rows | 30 | 120 |
| Scored pairs | 22 | 88 |
| Coverage | 73.3% | 73.3% |
| Minimum | 0.888822 | 0.462933 |
| Mean | 0.964342 | 0.667048 |
| Median | 0.962745 | 0.662625 |
| P05 | 0.919259 | 0.542671 |
| P95 | 0.998207 | 0.843074 |
| Maximum | 0.999206 | 0.861111 |
| Quality/multiple-face unavailable | 8 | 32 |

Baseline threshold analysis on the scored synthetic subset yielded AUC `1.0` because the genuine and impostor score ranges were ordered in this small corpus, but the deployed reference threshold `0.363` was too permissive: TPR `1.0`, FAR `1.0`, FRR `0.0`. This is not a production threshold recommendation.

## Aligned Results

The YuNet aligned experiment used a measured confidence operating point of `0.60`. The OpenCV tutorial's conservative `0.90` point produced no detections on these generated images; lowering the point was retained as an experiment only and was not promoted automatically.

| Metric | Genuine | Impostor |
| --- | ---: | ---: |
| Total rows | 30 | 120 |
| Scored pairs | 8 | 20 |
| Coverage | 26.7% | 16.7% |
| Minimum | 0.357864 | 0.225235 |
| Mean | 0.755891 | 0.359476 |
| Median | 0.837995 | 0.337634 |
| P05 | 0.416507 | 0.248680 |
| P95 | 0.964855 | 0.489885 |
| Maximum | 0.972137 | 0.599618 |
| MATCH / REVIEW / MISMATCH scored impostors | 9 / 4 / 7 |

Aligned threshold analysis on the scored subset yielded AUC `0.9375`. At reference threshold `0.363`, TPR was `0.875`, FAR was `0.45`, and FRR was `0.125`. The approximate equal-error operating point in the coarse sweep was near `0.475` with TPR `0.875` and FPR `0.10`. These are synthetic scored-subset measurements only and are not production calibration.

## Alignment Decision

**Do not make YuNet alignment the default yet.**

The aligned path improved the separation of the scored fictional rows and reduced the impostor match rate, but coverage fell from `73.3%/73.3%` to `26.7%/16.7%`. A verification pipeline that rejects most inputs is not a defensible production improvement. The experiment is retained behind configuration so it can be tested on an authorized, representative dataset later.

The Haar baseline remains the default because it is more robust on the approved synthetic corpus. This is an evidence-based decision, not a preference for the older detector.

## Threshold Policy

The production reference threshold remains `0.363`, and the TrustID review floor remains `0.30`. Neither was changed based on this synthetic analysis. The values are engineering parameters, not government or universal biometric standards. Candidate thresholds identified by analysis are not promoted.

## Runtime

| Pipeline | Mean provider call | Median | P95 | Model load |
| --- | ---: | ---: | ---: | ---: |
| Haar baseline | 735.48 ms | 768.54 ms | 1,141.62 ms | 280.05 ms |
| YuNet aligned, score 0.60 | 472.60 ms | 320.60 ms | 999.02 ms | 292.70 ms |

The aligned timing includes many fast unavailable paths, so it must not be interpreted as a faster successful verification pipeline. Peak memory remains environment-specific and Render has not been validated.

## Security and Privacy

No real public dataset was downloaded. No raw face image, embedding, vector, or benchmark cache is committed. The provider performs model hash validation, does not silently fall back to demo, does not persist embeddings, and does not return model internals. Liveness remains `NOT_IMPLEMENTED`.

## Required Acceptance Matrix

| Validation | Result | Evidence |
| --- | --- | --- |
| Real SFace inference | PASS | Existing local execution and provider benchmarks |
| LFW dataset access | BLOCKED | Explicit user privacy boundary |
| Dataset license verified | BLOCKED | No real dataset used |
| Standard external protocol | BLOCKED | No LFW processing permitted |
| Genuine benchmark | PASS | Synthetic/local baseline and aligned outputs |
| Impostor benchmark | PASS | Synthetic/local baseline and aligned outputs |
| ROC-style analysis | PASS | Aggregate threshold analysis artifacts |
| FAR/FRR/TAR/TPR | PASS | Threshold sweep over scored synthetic subsets |
| Reference threshold 0.363 | PASS | Evaluated without changing production value |
| TrustID policy analysis | PASS | Review floor `0.30`, match threshold `0.363` |
| Baseline Haar pipeline | PASS | Existing provider benchmark |
| Alignment experiment | PASS | YuNet + `alignCrop` implemented and executed |
| YuNet adoption | BLOCKED | Coverage materially worse on approved corpus |
| Quality coverage | PASS | All rows retained and coverage reported |
| Runtime benchmark | PASS | Baseline and aligned timings recorded |
| Memory benchmark | PASS | Existing local E2E measurement retained |
| Security regression | PASS | Existing suite plus model integrity checks |
| Privacy regression | PASS | No real dataset, embeddings, or biometric store |
| API/service E2E | PASS | Existing local production E2E remains passing |
| Frontend integration | PASS | Existing frontend gate remains required |
| Demo isolation | PASS | Provider selection remains explicit |
| No silent fallback | PASS | Provider initialization failures remain explicit |
| Liveness boundary | PASS | `NOT_IMPLEMENTED` preserved |
| Render production | BLOCKED | Native/model runtime not validated on free deployment |

## Final Engineering Answers

1. **Does SFace execute correctly?** Yes, locally with real inference and verified model hashes.
2. **Does TrustID perform face verification through its service?** Yes, through the existing local production service path.
3. **Does this approved benchmark show meaningful separation?** The aligned scored subset shows improved ranking, but coverage is inadequate; the baseline synthetic corpus remains insufficient for operational claims.
4. **Does preprocessing need improvement?** Landmark alignment is a credible future improvement, but the current corpus does not justify adopting it as default because coverage falls sharply.
5. **Does 0.363 behave as expected?** It is permissive on this synthetic corpus and is not calibrated for this application.
6. **Does TrustID policy need calibration?** Yes, using authorized representative data; no change is promoted here.
7. **Does the quality gate exclude significant data?** Yes, especially for the aligned experiment; this is explicitly reported.
8. **Is local computation practical?** Yes for controlled local execution, with environment-specific memory and latency caveats.
9. **Can current Render run production inference?** Not validated; keep Render in demo mode.
10. **What remains before operational deployment?** Authorized dataset evaluation, legal/privacy review, representative threshold calibration, demographic analysis, liveness/presentation-attack testing, and deployment load testing.

## Final Conclusion

Phase 2.2 is complete within the approved synthetic/local scope. The strongest clean local model path—SFace with YuNet landmark alignment—has been implemented as an explicit experiment, measured, and rejected as the default for now because coverage is materially worse. The reliable current default remains the Haar baseline, with all limitations preserved. External LFW validation is intentionally blocked by the user's privacy instruction, and Render remains a deployment blocker.
