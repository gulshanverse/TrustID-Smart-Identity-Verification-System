from __future__ import annotations

import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from app.domain.face import FaceScenario, ProductionFaceVerificationProvider
from sklearn.datasets import fetch_lfw_pairs

MODEL = "models/face_recognition_sface_2021dec.onnx"
MODEL_SHA = "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"
YUNET = "models/face_detection_yunet_2023mar.onnx"
YUNET_SHA = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"


def encode(image: np.ndarray) -> bytes:
    image = np.clip(image * 255, 0, 255).astype(np.uint8) if image.dtype != np.uint8 else image
    ok, encoded = cv2.imencode(".jpg", cv2.cvtColor(image, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ok:
        raise RuntimeError("image encode failed")
    return encoded.tobytes()


def run(name: str, kwargs: dict[str, Any], pairs: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    provider = ProductionFaceVerificationProvider(MODEL, MODEL_SHA, **kwargs)
    failures: Counter[str] = Counter()
    stage_counts: Counter[str] = Counter()
    genuine: list[float] = []
    impostor: list[float] = []
    timings: list[float] = []
    for index, pair in enumerate(pairs):
        started = time.perf_counter()
        try:
            result = provider.compare(encode(pair[0]), encode(pair[1]), FaceScenario.MATCH)
            timings.append((time.perf_counter() - started) * 1000)
            _, score, _, _, reason, quality, face_count = result
            if face_count == 0:
                stage_counts["no_face"] += 1
            elif face_count is not None and face_count > 1:
                stage_counts["multiple_face"] += 1
            elif score is not None:
                stage_counts["scored"] += 1
            else:
                stage_counts[quality.value.lower()] += 1
            if score is None:
                failures[reason or quality.value] += 1
            elif labels[index] == 1:
                genuine.append(float(score))
            else:
                impostor.append(float(score))
        except Exception as exc:  # noqa: BLE001
            timings.append((time.perf_counter() - started) * 1000)
            message = str(exc)
            if "dimensions are not suitable" in message:
                category = "invalid_dimensions"
            elif "Reference face unavailable" in message:
                category = "reference_" + message.split(":", 1)[-1].strip().replace(" ", "_").lower().replace(".", "")
            else:
                category = type(exc).__name__
            failures[category] += 1
            stage_counts["exception"] += 1
    return {"name": name, "config": kwargs, "pairs": len(pairs), "genuine_pairs": int(sum(labels == 1)), "impostor_pairs": int(sum(labels == 0)), "genuine_scored": len(genuine), "impostor_scored": len(impostor), "genuine_coverage": len(genuine) / int(sum(labels == 1)), "impostor_coverage": len(impostor) / int(sum(labels == 0)), "genuine_mean": statistics.mean(genuine) if genuine else None, "impostor_mean": statistics.mean(impostor) if impostor else None, "stage_counts": dict(stage_counts), "failures": dict(failures), "latency_ms": {"mean": statistics.mean(timings), "median": statistics.median(timings), "p95": float(np.percentile(timings, 95))}}


def main() -> None:
    lfw = fetch_lfw_pairs(subset="10_folds", color=True, resize=2.0, funneled=True, download_if_missing=True, data_home="/tmp/trustid-lfw")
    # Development only: first official fold. The untouched final protocol is not used for selection.
    pairs = lfw.pairs[:600]
    labels = lfw.target[:600]
    configs = [
        ("haar_baseline", {"detector": "haar"}),
        ("haar_padding_08", {"detector": "haar", "box_padding": 0.08}),
        ("haar_padding_12", {"detector": "haar", "box_padding": 0.12}),
        ("yunet_score_060", {"detector": "yunet", "detector_model_path": YUNET, "detector_expected_sha256": YUNET_SHA, "detector_score_threshold": 0.60}),
        ("yunet_score_090", {"detector": "yunet", "detector_model_path": YUNET, "detector_expected_sha256": YUNET_SHA, "detector_score_threshold": 0.90}),
        ("yunet_score_060_padding_08", {"detector": "yunet", "detector_model_path": YUNET, "detector_expected_sha256": YUNET_SHA, "detector_score_threshold": 0.60, "box_padding": 0.08}),
        ("yunet_score_090_padding_08", {"detector": "yunet", "detector_model_path": YUNET, "detector_expected_sha256": YUNET_SHA, "detector_score_threshold": 0.90, "box_padding": 0.08}),
        ("yunet_no_blur_gate", {"detector": "yunet", "detector_model_path": YUNET, "detector_expected_sha256": YUNET_SHA, "detector_score_threshold": 0.90, "blur_threshold": 0.0}),
        ("yunet_no_brightness_gate", {"detector": "yunet", "detector_model_path": YUNET, "detector_expected_sha256": YUNET_SHA, "detector_score_threshold": 0.90, "brightness_min": 0.0, "brightness_max": 255.0}),
        ("yunet_no_contrast_gate", {"detector": "yunet", "detector_model_path": YUNET, "detector_expected_sha256": YUNET_SHA, "detector_score_threshold": 0.90, "contrast_min": 0.0}),
        ("yunet_relaxed_size", {"detector": "yunet", "detector_model_path": YUNET, "detector_expected_sha256": YUNET_SHA, "detector_score_threshold": 0.90, "min_face_pixels": 40 * 40}),
    ]
    results = [run(name, kwargs, pairs, labels) for name, kwargs in configs]
    payload = {"kind": "phase24_development_only_sweep", "dataset": {"name": "LFW", "official_fold": 0, "pairs": len(pairs), "raw_data_committed": False}, "thresholds_unchanged": {"review": 0.30, "match": 0.363}, "selection_rule": "No configuration selected on AUC alone; final configuration requires coverage, failure breakdown, score behavior, and full untouched rerun.", "results": results}
    Path("benchmarks/phase24_development_sweep.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
