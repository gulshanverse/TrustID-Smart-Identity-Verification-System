from __future__ import annotations

import json
from pathlib import Path

from phase24_development_sweep import run
from sklearn.datasets import fetch_lfw_pairs

MODEL = "models/face_recognition_sface_2021dec.onnx"
MODEL_SHA = "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"
YUNET = "models/face_detection_yunet_2023mar.onnx"
YUNET_SHA = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"


def main() -> None:
    lfw = fetch_lfw_pairs(subset="10_folds", color=True, resize=2.0, funneled=True, download_if_missing=True, data_home="/tmp/trustid-lfw")
    pairs, labels = lfw.pairs[:600], lfw.target[:600]
    results = []
    for threshold in (0.0, 2.5, 5.0, 10.0, 15.0, 20.0):
        results.append(run(f"yunet_blur_{threshold:g}", {"detector": "yunet", "detector_model_path": YUNET, "detector_expected_sha256": YUNET_SHA, "detector_score_threshold": 0.9, "blur_threshold": threshold}, pairs, labels))
    payload = {"kind": "phase24_development_blur_sweep", "official_fold": 0, "thresholds_unchanged": {"review": 0.30, "match": 0.363}, "results": results}
    Path("benchmarks/phase24_blur_sweep.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
