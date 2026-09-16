from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
from app.domain.face import (
    FaceScenario,
    ProductionFaceVerificationProvider,
)
from sklearn.datasets import fetch_lfw_pairs


def percentile(values: list[float], p: float) -> float | None:
    return float(np.percentile(np.asarray(values), p)) if values else None


def stats(values: list[float]) -> dict[str, float | int | None]:
    return {"count": len(values), "min": min(values) if values else None, "mean": statistics.mean(values) if values else None, "median": statistics.median(values) if values else None, "p05": percentile(values, 5), "p95": percentile(values, 95), "max": max(values) if values else None}


def histogram(values: list[float]) -> list[dict[str, float | int]]:
    edges = [round(index / 20, 2) for index in range(21)]
    return [{"lower": edges[index], "upper": edges[index + 1], "count": sum(edges[index] <= value < edges[index + 1] for value in values)} for index in range(20)]


def metric_rows(genuine: list[float], impostor: list[float], thresholds: list[float]) -> list[dict[str, float | int | None]]:
    rows = []
    for threshold in thresholds:
        tp = sum(score >= threshold for score in genuine)
        fn = len(genuine) - tp
        fp = sum(score >= threshold for score in impostor)
        tn = len(impostor) - fp
        tpr = tp / len(genuine) if genuine else None
        far = fp / len(impostor) if impostor else None
        frr = fn / len(genuine) if genuine else None
        tnr = tn / len(impostor) if impostor else None
        precision = tp / (tp + fp) if tp + fp else None
        accuracy = (tp + tn) / (len(genuine) + len(impostor)) if genuine or impostor else None
        balanced = ((tpr or 0) + (tnr or 0)) / 2 if tpr is not None and tnr is not None else None
        rows.append({"threshold": threshold, "tp": tp, "tn": tn, "fp": fp, "fn": fn, "tpr_tar": tpr, "far_fpr": far, "frr": frr, "tnr": tnr, "precision": precision, "accuracy": accuracy, "balanced_accuracy": balanced})
    return rows


def auc_eer(genuine: list[float], impostor: list[float]) -> tuple[float | None, dict[str, float] | None]:
    if not genuine or not impostor:
        return None, None
    scores = np.asarray(genuine + impostor, dtype=float)
    labels = np.asarray([1] * len(genuine) + [0] * len(impostor), dtype=int)
    order = np.argsort(-scores)
    ordered = labels[order]
    tpr = np.cumsum(ordered == 1) / len(genuine)
    fpr = np.cumsum(ordered == 0) / len(impostor)
    auc_value = float(np.trapezoid(np.r_[0.0, tpr], np.r_[0.0, fpr]))
    candidate_thresholds = sorted(set([0.30, 0.363] + [round(float(s), 6) for s in scores]))
    sweep = metric_rows(genuine, impostor, candidate_thresholds)
    eer_row = min((row for row in sweep if row["far_fpr"] is not None and row["frr"] is not None), key=lambda row: abs(float(row["far_fpr"]) - float(row["frr"])), default=None)
    return auc_value, eer_row


def encode_image(image: np.ndarray) -> bytes:
    if image.dtype != np.uint8:
        image = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    ok, encoded = cv2.imencode(".jpg", cv2.cvtColor(image, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ok:
        raise RuntimeError("Could not encode LFW image for TrustID provider.")
    return encoded.tobytes()


def run_path(name: str, provider: ProductionFaceVerificationProvider, images: np.ndarray, labels: np.ndarray) -> dict[str, object]:
    genuine: list[float] = []
    impostor: list[float] = []
    latencies: list[float] = []
    successful_latencies: list[float] = []
    unavailable_latencies: list[float] = []
    outcomes: dict[str, int] = {}
    failures: dict[str, int] = {}
    total = len(images)
    for index, pair in enumerate(images):
        started = time.perf_counter()
        try:
            first = encode_image(pair[0])
            second = encode_image(pair[1])
            outcome, score, _, _, reason, quality, face_count = provider.compare(first, second, FaceScenario.MATCH)
            latencies.append((time.perf_counter() - started) * 1000)
            outcomes[outcome.value] = outcomes.get(outcome.value, 0) + 1
            if score is not None:
                successful_latencies.append(latencies[-1])
                (genuine if int(labels[index]) == 1 else impostor).append(float(score))
            elif reason:
                unavailable_latencies.append(latencies[-1])
                failures[quality.value] = failures.get(quality.value, 0) + 1
            _ = face_count
        except Exception as exc:  # noqa: BLE001
            latencies.append((time.perf_counter() - started) * 1000)
            unavailable_latencies.append(latencies[-1])
            message = str(exc)
            if "dimensions are not suitable" in message:
                reason = "IMAGE_DIMENSIONS"
            elif "Reference face unavailable" in message:
                reason = "REFERENCE_" + message.split(":", 1)[-1].strip().replace(" ", "_").upper().replace(".", "")
            else:
                reason = type(exc).__name__
            failures[reason] = failures.get(reason, 0) + 1
    auc_value, eer = auc_eer(genuine, impostor)
    thresholds = metric_rows(genuine, impostor, [0.30, 0.363, 0.40, 0.45, 0.475, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80])
    def latency_summary(values: list[float]) -> dict[str, float | int | None]:
        return {"count": len(values), "mean": statistics.mean(values) if values else None, "median": statistics.median(values) if values else None, "p95": percentile(values, 95), "max": max(values) if values else None}
    return {"pipeline": name, "total_pairs": total, "genuine_total": int(sum(labels == 1)), "impostor_total": int(sum(labels == 0)), "genuine_scored": len(genuine), "impostor_scored": len(impostor), "genuine_coverage": len(genuine) / int(sum(labels == 1)), "impostor_coverage": len(impostor) / int(sum(labels == 0)), "genuine": stats(genuine), "impostor": stats(impostor), "score_histogram": {"genuine": histogram(genuine), "impostor": histogram(impostor)}, "auc": auc_value, "eer": eer, "thresholds": thresholds, "outcomes": outcomes, "failures": failures, "latency_ms": {"overall": latency_summary(latencies), "successful": latency_summary(successful_latencies), "unavailable": latency_summary(unavailable_latencies)}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", default="/tmp/trustid-lfw")
    parser.add_argument("--model", default="models/face_recognition_sface_2021dec.onnx")
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--yunet-model", default="models/face_detection_yunet_2023mar.onnx")
    parser.add_argument("--yunet-sha256", required=True)
    parser.add_argument("--output", default="benchmarks/phase23_lfw_results.json")
    args = parser.parse_args()
    lfw = fetch_lfw_pairs(subset="10_folds", color=True, resize=2.0, funneled=True, download_if_missing=True, data_home=args.cache)
    model_hash = hashlib.sha256(Path(args.model).read_bytes()).hexdigest()
    yunet_hash = hashlib.sha256(Path(args.yunet_model).read_bytes()).hexdigest()
    if model_hash.lower() != args.model_sha256.lower() or yunet_hash.lower() != args.yunet_sha256.lower():
        raise RuntimeError("Model integrity check failed before benchmark execution.")
    provider_load_started = time.perf_counter()
    haar = ProductionFaceVerificationProvider(args.model, args.model_sha256, "haar")
    haar_load_ms = (time.perf_counter() - provider_load_started) * 1000
    provider_load_started = time.perf_counter()
    yunet = ProductionFaceVerificationProvider(args.model, args.model_sha256, "yunet", args.yunet_model, args.yunet_sha256, 0.9)
    yunet_load_ms = (time.perf_counter() - provider_load_started) * 1000
    payload = {"dataset": {"name": "LFW", "source": "Official UMass LFW project via scikit-learn's official-source loader", "protocol": "10-fold image-restricted pair protocol; funneled images; no threshold tuning during scoring", "pairs": len(lfw.target), "genuine_pairs": int(sum(lfw.target == 1)), "impostor_pairs": int(sum(lfw.target == 0)), "cache": args.cache, "raw_data_committed": False}, "reproducibility": {"git_sha": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "python": sys.version, "opencv": cv2.__version__, "os": platform.platform(), "model_sha256": model_hash, "yunet_sha256": yunet_hash, "random_seed": None, "timestamp_utc": datetime.now(UTC).isoformat()}, "models": {"sface": "face_recognition_sface_2021dec.onnx", "yunet": "face_detection_yunet_2023mar.onnx"}, "load_ms": {"haar": haar_load_ms, "yunet": yunet_load_ms}, "results": [run_path("haar", haar, lfw.pairs, lfw.target), run_path("yunet_align", yunet, lfw.pairs, lfw.target)]}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2))
    print(json.dumps({"dataset": payload["dataset"], "load_ms": payload["load_ms"], "results": [{k: value[k] for k in ("pipeline", "genuine_scored", "impostor_scored", "genuine_coverage", "impostor_coverage", "auc", "eer", "latency_ms", "failures")} for value in payload["results"]]}, indent=2))


if __name__ == "__main__":
    main()
