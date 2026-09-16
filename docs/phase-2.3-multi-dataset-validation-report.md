# TrustID Phase 2.3 Multi-Dataset Validation Report

## Final status

**COMPLETE WITH DEPLOYMENT BLOCKER**

The existing TrustID SFace pipeline was evaluated on the official Labeled Faces in the Wild (LFW) ten-fold verification protocol. Both the Haar baseline and the implemented YuNet plus landmark-alignment path were executed through the actual TrustID provider. Raw LFW data remained outside Git, and only aggregate metrics and reproducibility metadata were retained.

The other requested datasets were not silently substituted. VGGFace2 was blocked because the official download is unavailable and dataset-specific terms were not established. CelebA was blocked because its official identity-annotation access was not available during this run and it has no official verification-pair protocol. IJB-C was not validated because NIST discontinued distribution and no lawful local copy was available.

Local implementation and LFW validation are complete. Render production inference, authorized operational datasets, liveness, presentation-attack testing, legal review, and deployment calibration remain outside this phase.

## Scope and existing architecture

TrustID continues to use the existing provider abstraction. The recognition engine is OpenCV SFace. The default path is Haar detection followed by the existing quality gate, crop, resize, SFace feature extraction, normalization, and cosine similarity. The optional experiment uses YuNet detection, five-point landmark alignment through `FaceRecognizerSF.alignCrop`, SFace inference, normalization, and cosine similarity.

The reference cosine threshold remains **0.363**. The TrustID review floor remains **0.30**. Neither value is a government threshold, a universal biometric threshold, or an operational deployment recommendation.

## Model details

| Model | SHA-256 | Runtime |
| --- | --- | --- |
| OpenCV SFace `face_recognition_sface_2021dec.onnx` | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` | OpenCV DNN FaceRecognizerSF on CPU |
| OpenCV YuNet `face_detection_yunet_2023mar.onnx` | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` | OpenCV FaceDetectorYN on CPU |

The SFace embedding dimension is 128. Model hashes were checked before the benchmark. Model files are deployment-provisioned and are not committed.

## Dataset inventory and terms review

| Dataset | Official source and terms | Processing status |
| --- | --- | --- |
| LFW | The UMass project and technical reports describe the database and verification protocols. Research evaluation is supported by the official materials, but unrestricted redistribution and commercial rights were not established. | **Processed locally** under the official pair protocol. |
| VGGFace2 | The Oxford VGG page states that download links are no longer available. The reviewed official materials do not establish a dataset-specific license or commercial-use grant. | **BLOCKED; not processed.** |
| CelebA | The official CUHK page permits non-commercial research, prohibits redistribution and commercial exploitation, and releases identity annotations upon request. It does not define an official verification-pair protocol. | **BLOCKED; not processed.** Official identity access was unavailable in this run. |
| IJB-C | NIST discontinued distribution on 14 March 2023. The official README describes per-item Creative Commons variants and verification protocols, but no lawful local copy was available. | **NOT VALIDATED; not processed.** |

LFW was cached temporarily at `/tmp/trustid-lfw`, used for evaluation, and removed after the run. No raw dataset, face crop, embedding, pair-level score, or biometric cache was committed.

## LFW protocol and split methodology

The benchmark used the official 10-fold image-restricted pair structure returned by the LFW loader: 6,000 total pairs, comprising 3,000 genuine pairs and 3,000 impostor pairs. The benchmark did not train or fine-tune SFace. Thresholds were not changed before the initial scoring pass.

The LFW images were loaded at `resize=2.0` because the source representation otherwise produced images below TrustID's real input validation minimum of 160 pixels. The benchmark did not sharpen, enhance, or hallucinate image content. The selected loader path produced 250×188 images for processing.

TrustID's provider was used for decode, detector execution, face-count handling, quality checks, preprocessing, SFace inference, normalization, similarity, and threshold outcomes. Unavailable cases remained in the coverage denominator.

## LFW results: Haar baseline

The Haar pipeline scored only 2 of 3,000 genuine pairs and 0 of 3,000 impostor pairs. Genuine coverage was **0.0667%** and impostor coverage was **0%**. AUC and EER are **not meaningful** because there were no scored impostors.

The dominant failure was reference-side no-face detection: 5,654 pair attempts. Other observed causes included blur, small face regions, multiple-face handling, brightness/contrast rejection, and presented-image no-face cases. This is evidence that the current Haar detector and quality gate do not generalize to this LFW representation at useful coverage.

At both 0.30 and 0.363, the two scored genuine pairs were accepted. FAR is undefined because zero impostor pairs were scored. This result must not be interpreted as low false-match behavior.

## LFW results: YuNet plus alignment

The YuNet aligned path scored 164 of 3,000 genuine pairs and 116 of 3,000 impostor pairs. Genuine coverage was **5.4667%** and impostor coverage was **3.8667%**. The scored subset produced AUC **0.999947**. This high AUC is limited by the very low coverage and must not be interpreted as production accuracy.

The approximate equal-error point from the deterministic score sweep was threshold **0.297571**, with TPR `0.993902`, FAR `0.008621`, and FRR `0.006098` on the scored subset. This is an analysis point, not a promoted production threshold.

At the existing TrustID review floor of **0.30**, the aligned path produced TPR/TAR `0.993902`, FAR/FPR `0.008621`, and FRR `0.006098` on scored pairs. At the existing reference threshold of **0.363**, it produced TPR/TAR `0.969512`, FAR/FPR `0.000000`, and FRR `0.030488` on scored pairs. Coverage remains only 5.47% for genuine attempts and 3.87% for impostor attempts.

The dominant aligned-path failure was blur-related quality rejection: 4,050 pair attempts. There were also 707 generic low-quality outcomes, 903 provider errors, 51 brightness/contrast failures, and 9 no-face outcomes. The benchmark records these failures rather than dropping them.

## Threshold table

| Pipeline | Threshold | TPR/TAR | FAR/FPR | FRR | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| Haar | 0.30 | 1.000000 | Undefined | 0.000000 | No impostor pair scored; unusable for FAR inference |
| Haar | 0.363 | 1.000000 | Undefined | 0.000000 | No impostor pair scored; unusable for FAR inference |
| YuNet aligned | 0.30 | 0.993902 | 0.008621 | 0.006098 | Existing policy floor; scored subset only |
| YuNet aligned | 0.363 | 0.969512 | 0.000000 | 0.030488 | Existing reference threshold; scored subset only |
| YuNet aligned | 0.297571 | 0.993902 | 0.008621 | 0.006098 | Candidate analysis point near approximate EER; not promoted |

No threshold was promoted. The benchmark does not justify changing 0.363 or 0.30 because coverage is too low and only one dataset was legally and technically processable in this run.

## ROC and score distributions

The LFW aggregate ROC and score-distribution plots use only in-memory scores converted to binned aggregate counts. Individual scores and pair identities were not persisted. The ROC plot is therefore a threshold-sweep visualization over aggregate counts, not a claim of independent calibration.

## Cross-dataset generalization

Cross-dataset validation was **BLOCKED** because only LFW was processable. VGGFace2 had no available official download and unclear dataset-specific rights. CelebA required identity annotations and a non-commercial research access path that was not available in this run. IJB-C distribution was discontinued and no lawful copy was available.

No cross-dataset threshold transfer claim is made. This is a critical remaining validation gap.

## Calibration, false matches, and false non-matches

Calibration was not performed on the final LFW test pairs. The values 0.30 and 0.363 were evaluated as pre-existing engineering parameters. The approximate 0.297571 operating point is reported only as a candidate from the scored subset and is not production configuration.

The aligned pipeline had one false-match event at the approximate EER point and none at 0.363 among scored impostors. Because only 116 impostors were scored and overall impostor coverage was 3.8667%, this does not support a claim of zero false matches in deployment.

The aligned pipeline had five false non-matches at 0.363 among 164 scored genuine pairs. The available evidence supports a strong association between unavailable attempts and quality/detection handling, especially blur, but it does not establish general causal performance across pose, age, demographic groups, or operational capture conditions.

Hard-negative analysis is limited to the aggregate threshold outputs. Pair-level hard-negative identifiers were deliberately not retained because the privacy policy prohibits publishing unnecessary identity-linked biometric records.

Demographic analysis is **NOT AVAILABLE**. No demographic labels were used or inferred.

## Performance and memory

Model initialization was measured locally at approximately 304 ms for Haar and 281 ms for YuNet in the final run. These values are environment-specific.

For Haar, successful scored-pair latency had a mean of 112.16 ms, a median of 112.16 ms, and a P95 of 135.86 ms across only two successful pairs. Overall latency across 6,000 pair attempts had a mean of 10.29 ms, a median of 9.89 ms, and a P95 of 14.24 ms; this is dominated by early failures and must not be compared with successful verification latency.

For YuNet alignment, successful scored-pair latency had a mean of 46.92 ms, a median of 47.30 ms, and a P95 of 52.44 ms across 280 successful pair attempts. Overall latency had a mean of 8.08 ms, a median of 5.74 ms, and a P95 of 12.78 ms; this is also dominated by early unavailable paths.

The local production E2E harness measured peak resident memory at approximately 325,384 KiB. This is a local environment measurement. It does not establish Render compatibility.

## Regression and security results

The existing local production E2E path passed. Face verification records and audit events persisted correctly, and the E2E confirmed that embeddings were not persisted. Model integrity checks passed for correct hashes and failed for incorrect hashes. Missing models fail explicitly. Production selection does not silently fall back to demo.

The existing provider continues to return safe result fields only. It does not return embeddings, raw tensors, private model paths, or raw benchmark images. Liveness remains **NOT_IMPLEMENTED**. No anti-spoofing, replay protection, mask detection, deepfake detection, or presentation-attack detection is claimed.

## Deployment and operational limitations

Render remains **DEMO / SIMULATED**. Local SFace execution does not prove that the current Render deployment can provision the model, remain within memory limits, initialize reliably, or serve concurrent production requests.

This work does not integrate with passport, visa, immigration, police, MHA, SSB, or national identity databases. No government certification or approval is claimed. The architecture remains ₹0/free-tier and does not use paid face APIs or cloud biometric services.

## Engineering decision

The LFW evidence does not support replacing Haar with YuNet as the default. YuNet alignment improves measured score separation on the small scored subset and provides materially better coverage than Haar on this LFW representation, but its absolute coverage remains too low for operational adoption. Haar is also unusable on this representation because it scores almost no pairs. The correct engineering conclusion is to preserve both paths, retain Haar as the existing default for backwards compatibility, and require a future representative, authorized dataset and input-format investigation before changing the default.

## Final acceptance matrix

| Validation | Status | Evidence | Limitation |
| --- | --- | --- | --- |
| Real SFace inference | PASS | Local provider and E2E | Local only |
| LFW evaluation | PASS | 6,000 official pairs processed | Terms do not establish commercial redistribution rights |
| VGGFace2 evaluation | BLOCKED | Official download unavailable; terms unclear | No lawful copy |
| CelebA evaluation | BLOCKED | Official non-commercial terms reviewed | Identity access and verification protocol unavailable |
| IJB-C evaluation | NOT VALIDATED | NIST distribution discontinued | No lawful copy |
| Dataset license review | PASS WITH LIMITATIONS | Official sources reviewed | Several dataset rights remain incomplete |
| Standard protocol | PASS for LFW | Official ten-fold pair structure | Other datasets unavailable |
| Genuine benchmark | PASS for LFW | 3,000 genuine attempts | Low score coverage |
| Impostor benchmark | PASS for LFW | 3,000 impostor attempts | Low score coverage |
| ROC/AUC | PASS for aligned LFW subset | AUC 0.999947 | Coverage limitation |
| FAR/FRR/TPR | PASS for aligned scored subset | Threshold table | Not deployment-calibrated |
| EER | LIMITED | Approximate threshold 0.297571 | Small scored subset |
| Threshold sweep | PASS | Deterministic sweep | No threshold promoted |
| Cross-dataset validation | BLOCKED | Only LFW processable | Major remaining gap |
| Haar baseline | PASS | Actual TrustID Haar provider | 0.0667% genuine coverage |
| YuNet alignment | PASS as experiment | Actual TrustID YuNet provider | 5.4667% genuine coverage |
| Quality coverage | PASS | Failure taxonomy retained | LFW representation is low coverage |
| Runtime | PASS | Separate success/unavailable timings | Local hardware only |
| Memory | PASS locally | E2E peak RSS recorded | Not Render validation |
| Security regression | PASS | Hash, fallback, validation, ownership tests | No production deployment audit |
| Privacy regression | PASS | No embeddings or raw images committed | Dataset legal review remains required |
| API E2E | PASS | Existing production E2E | Local only |
| Database regression | PASS | Records and audit events persisted | No new schema changes |
| Frontend regression | PASS | Existing frontend suite/build | No new biometric UI claims |
| Demo isolation | PASS | Explicit provider selection | Deployment configuration remains separate |
| No silent fallback | PASS | Explicit provider failure | — |
| Liveness boundary | PASS | Not implemented and not claimed | Future requirement |
| Render production inference | BLOCKED | Not validated on Render | Keep demo mode |

## Recommended next engineering phase

Do not start Phase 3 automatically. Before operational deployment, obtain an authorized representative evaluation set with clear rights, repeat the frozen TrustID protocol across at least two legally usable datasets, investigate the LFW resolution and detector-quality mismatch, calibrate thresholds on development identities only, evaluate demographic and presentation-attack risks, and validate deployment memory and concurrency in the actual target environment.

## References

[1]: https://vis-www.cs.umass.edu/lfw/ "Labeled Faces in the Wild dataset project"

[2]: https://vis-www.cs.umass.edu/lfw/lfw.pdf "Labeled Faces in the Wild: A Database for Studying Unconstrained Face Recognition"

[3]: https://people.cs.umass.edu/~elm/papers/lfw_update.pdf "Labeled Faces in the Wild: Updates and New Reporting Procedures"

[4]: https://www.robots.ox.ac.uk/~vgg/data/vgg_face2/ "VGGFace2 official Oxford VGG page"

[5]: https://github.com/ox-vgg/vgg_face2 "Official VGGFace2 repository"

[6]: https://mmlab.ie.cuhk.edu.hk/projects/CelebA.html "Official CelebA dataset page and agreement"

[7]: https://www.nist.gov/programs-projects/face-challenges "NIST Face Challenges and IJB-C information"

[8]: https://www.nist.gov/system/files/documents/2017/12/26/readme.pdf "IJB-C README and license notice"

[9]: https://docs.opencv.org/4.13.0/d0/dd4/tutorial_dnn_face.html "OpenCV DNN face detection and recognition tutorial"
