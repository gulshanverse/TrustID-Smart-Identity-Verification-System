# LFW protocol

TrustID Phase 2.3 uses the official LFW ten-fold pair-verification structure through the scikit-learn loader that retrieves the UMass LFW resources. The run contains 6,000 pairs: 3,000 genuine same-identity pairs and 3,000 impostor different-identity pairs.

The benchmark evaluates both existing TrustID paths without changing the production thresholds before scoring: Haar plus SFace, and YuNet plus five-point `alignCrop` plus SFace. The SFace cosine reference threshold is 0.363 and the TrustID review floor is 0.30. Threshold analysis occurs only after the untouched scoring pass.

The loader's native-size setting was increased to `resize=2.0` because TrustID's actual image-validation contract rejects images below 160 pixels in either dimension. This is recorded as a pipeline compatibility choice rather than an image enhancement. No face crops or embeddings are written. Only aggregate statistics and histograms are retained.

The official UMass protocol and terms sources are cited in the Phase 2.3 report. Raw LFW data remains in temporary local cache storage outside Git and is deleted after evaluation.
