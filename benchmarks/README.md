# Controlled synthetic face validation

The local corpus under `synthetic_faces/` contains fictional AI-generated portrait images created solely for TrustID engineering validation. It contains no real person photographs, identity documents, or personal identity data. Deterministic brightness, blur, rotation, dark, and small variants are generated from each reference by `scripts/phase2_face_benchmark.py` using OpenCV.

The benchmark invokes the actual `ProductionFaceVerificationProvider`, including Haar detection, quality checks, crop preprocessing, OpenCV SFace ONNX inference, normalized embedding comparison, and threshold decision. It records every pair, including errors; it does not remove poor outcomes or tune scores after inspection.

Run:

```bash
PYTHONPATH=apps/api python3 scripts/phase2_face_benchmark.py \
  --model models/face_recognition_sface_2021dec.onnx \
  --expected-sha256 0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79
```

`phase2_face_benchmark.json` and `.csv` are measured outputs from the current local runtime. These are **controlled synthetic validation measurements only**, not real-world biometric accuracy, FAR/FRR, fairness, government-grade performance, or population-level evidence.

The current corpus demonstrates genuine-pair matching but also exposes substantial impostor overlap. That limitation is intentionally retained in the report; the benchmark is not used to claim production readiness.

Phase 2.2 also records a baseline Haar run and a YuNet landmark-aligned run. The aligned run uses `--detector yunet`, the provisioned YuNet SHA-256, and `--detector-score 0.6` for this synthetic-corpus experiment. Threshold and ROC-style metrics are generated with `scripts/phase2_threshold_analysis.py`. YuNet alignment improved the scored-subset ranking but reduced coverage materially, so Haar remains the default and YuNet remains an explicit experiment rather than an automatic production replacement.

Phase 2.3 adds the official LFW ten-fold evaluation under `results/lfw/`. The run processed 6,000 pairs through both actual TrustID provider paths and retained only aggregate results, threshold tables, ROC points, binned score distributions, and plots. VGGFace2, CelebA, and IJB-C remain explicitly blocked or not validated for the reasons recorded in `benchmarks/datasets/README.md` and the protocol gate files.
