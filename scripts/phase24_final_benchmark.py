from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
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


def run(name: str, provider: ProductionFaceVerificationProvider, pairs: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    genuine: list[float] = []
    impostor: list[float] = []
    failures: Counter[str] = Counter()
    stages: Counter[str] = Counter()
    timings: list[float] = []
    successful: list[float] = []
    unavailable: list[float] = []
    traces: Counter[str] = Counter()
    for index, pair in enumerate(pairs):
        started = time.perf_counter()
        try:
            _outcome, score, _, _, reason, quality, face_count = provider.compare(encode(pair[0]), encode(pair[1]), FaceScenario.MATCH)
            elapsed = (time.perf_counter() - started) * 1000
            timings.append(elapsed)
            trace = provider.last_trace
            if face_count == 0:
                stages["no_face"] += 1
            elif face_count is not None and face_count > 1:
                stages["multiple_faces"] += 1
            elif score is None:
                stages[quality.value.lower()] += 1
            else:
                stages["scored"] += 1
            if trace.get("alignment"):
                traces[trace["alignment"]] += 1
            if score is None:
                unavailable.append(elapsed)
                failures[reason or quality.value] += 1
            else:
                successful.append(elapsed)
                (genuine if labels[index] == 1 else impostor).append(float(score))
        except Exception as exc:  # noqa: BLE001
            elapsed = (time.perf_counter() - started) * 1000
            timings.append(elapsed)
            unavailable.append(elapsed)
            message = str(exc)
            if "dimensions are not suitable" in message:
                category = "invalid_dimensions"
            elif "Reference face unavailable" in message:
                category = "reference_" + message.split(":", 1)[-1].strip().replace(" ", "_").lower().replace(".", "")
            else:
                category = type(exc).__name__
            failures[category] += 1
            stages["exception"] += 1
    scores = np.asarray(genuine + impostor, dtype=float)
    labels_array = np.asarray([1] * len(genuine) + [0] * len(impostor), dtype=int)
    if len(scores) and len(genuine) and len(impostor):
        order = np.argsort(-scores)
        ordered = labels_array[order]
        tpr = np.cumsum(ordered == 1) / len(genuine)
        fpr = np.cumsum(ordered == 0) / len(impostor)
        auc = float(np.trapezoid(np.r_[0.0, tpr], np.r_[0.0, fpr]))
    else:
        auc = None
    def at(threshold: float) -> dict[str, float | int | None]:
        tp = sum(value >= threshold for value in genuine)
        fn = len(genuine) - tp
        fp = sum(value >= threshold for value in impostor)
        tn = len(impostor) - fp
        return {"threshold": threshold, "tp": tp, "tn": tn, "fp": fp, "fn": fn, "tpr_tar": tp / len(genuine) if genuine else None, "far_fpr": fp / len(impostor) if impostor else None, "frr": fn / len(genuine) if genuine else None, "tnr": tn / len(impostor) if impostor else None}
    threshold_rows = [at(0.30), at(0.363)]
    candidates = [at(round(float(value), 6)) for value in scores] if len(scores) else []
    comparable = [row for row in candidates if row["far_fpr"] is not None and row["frr"] is not None]
    eer = min(comparable, key=lambda row: abs(float(row["far_fpr"]) - float(row["frr"])), default=None)
    def summary(values: list[float]) -> dict[str, float | int | None]:
        return {"count": len(values), "mean": statistics.mean(values) if values else None, "median": statistics.median(values) if values else None, "p95": float(np.percentile(values, 95)) if values else None, "max": max(values) if values else None}
    return {"pipeline": name, "config": {"detector": provider.detector_mode, "score_threshold": getattr(provider, "detector_score_threshold", None), "box_padding": provider.box_padding, "blur_threshold": provider.blur_threshold, "min_face_pixels": provider.min_face_pixels, "brightness_min": provider.brightness_min, "brightness_max": provider.brightness_max, "contrast_min": provider.contrast_min}, "total_pairs": len(pairs), "genuine_total": int(sum(labels == 1)), "impostor_total": int(sum(labels == 0)), "genuine_scored": len(genuine), "impostor_scored": len(impostor), "genuine_coverage": len(genuine) / int(sum(labels == 1)), "impostor_coverage": len(impostor) / int(sum(labels == 0)), "genuine_stats": summary(genuine), "impostor_stats": summary(impostor), "auc": auc, "eer_candidate": eer, "thresholds": threshold_rows, "stages": dict(stages), "failures": dict(failures), "alignment_outcomes": dict(traces), "latency_ms": {"overall": summary(timings), "successful": summary(successful), "unavailable": summary(unavailable)}}


def main() -> None:
    lfw = fetch_lfw_pairs(subset="10_folds", color=True, resize=2.0, funneled=True, download_if_missing=True, data_home="/tmp/trustid-lfw")
    started = time.perf_counter()
    haar = ProductionFaceVerificationProvider(MODEL, MODEL_SHA, "haar")
    haar_load = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    candidate = ProductionFaceVerificationProvider(MODEL, MODEL_SHA, "yunet", YUNET, YUNET_SHA, 0.9, 0.0, 6400, 5.0, 35.0, 225.0, 18.0)
    candidate_load = (time.perf_counter() - started) * 1000
    payload = {"kind": "phase24_full_untouched_lfw_rerun", "timestamp_utc": datetime.now(UTC).isoformat(), "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "dataset": {"name": "LFW", "protocol": "official 10-fold image-restricted pair protocol", "pairs": 6000, "genuine": 3000, "impostor": 3000, "resize": 2.0, "raw_data_committed": False}, "models": {"sface_sha256": hashlib.sha256(Path(MODEL).read_bytes()).hexdigest(), "yunet_sha256": hashlib.sha256(Path(YUNET).read_bytes()).hexdigest()}, "thresholds_unchanged": {"review": 0.30, "match": 0.363}, "selection": {"development_fold": 0, "selected_candidate": "YuNet score 0.90, blur threshold 5.0, all other quality gates unchanged", "selected_without_final_score_tuning": True}, "initialization_ms": {"haar": haar_load, "yunet_candidate": candidate_load}, "results": [run("haar_baseline", haar, lfw.pairs, lfw.target), run("yunet_candidate_blur_5", candidate, lfw.pairs, lfw.target)]}
    Path("benchmarks/phase24_full_lfw_results.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({"initialization_ms": payload["initialization_ms"], "results": payload["results"]}, indent=2))


if __name__ == "__main__":
    main()
