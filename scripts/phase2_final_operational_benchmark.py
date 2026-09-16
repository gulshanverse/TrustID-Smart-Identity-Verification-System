from __future__ import annotations

import json
import resource
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from app.domain.face import FaceScenario, ProductionFaceVerificationProvider

MODEL = "models/face_recognition_sface_2021dec.onnx"
MODEL_SHA = "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"
YUNET = "models/face_detection_yunet_2023mar.onnx"
YUNET_SHA = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
REFERENCE = Path("benchmarks/synthetic_faces/person_001_reference.png")
SECOND = Path("benchmarks/synthetic_faces/person_002_reference.png")


def jpg(image: np.ndarray, quality: int = 95) -> bytes:
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("could not encode synthetic operational image")
    return encoded.tobytes()


def operational_cases() -> dict[str, bytes]:
    image = cv2.imdecode(np.frombuffer(REFERENCE.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    second = cv2.imdecode(np.frombuffer(SECOND.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    blurred = cv2.GaussianBlur(image, (0, 0), 2.0)
    heavy_blur = cv2.GaussianBlur(image, (0, 0), 9.0)
    dark = np.clip(image.astype(np.float32) * 0.35, 0, 255).astype(np.uint8)
    bright = np.clip(image.astype(np.float32) * 1.65, 0, 255).astype(np.uint8)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    low_contrast = cv2.cvtColor(cv2.normalize(gray, None, 100, 155, cv2.NORM_MINMAX), cv2.COLOR_GRAY2BGR)
    rotated = cv2.warpAffine(image, cv2.getRotationMatrix2D((image.shape[1] / 2, image.shape[0] / 2), 12, 1), (image.shape[1], image.shape[0]))
    cropped = image[0 : image.shape[0] // 2, :]
    small = cv2.resize(image, (max(1, image.shape[1] // 3), max(1, image.shape[0] // 3)))
    canvas = np.zeros((max(image.shape[0], second.shape[0]), image.shape[1] + second.shape[1], 3), dtype=np.uint8)
    canvas[: image.shape[0], : image.shape[1]] = image
    canvas[: second.shape[0], image.shape[1] :] = second
    return {"good_frontal": jpg(image), "mild_blur": jpg(blurred), "heavy_blur": jpg(heavy_blur), "low_light": jpg(dark), "overexposure": jpg(bright), "low_contrast": jpg(low_contrast), "compression": jpg(image, 20), "rotation": jpg(rotated), "partial_crop": jpg(cropped), "face_too_small": jpg(small), "multiple_faces": jpg(canvas), "no_face": jpg(np.zeros_like(image)), "corrupted": b"not-an-image", "unsupported_format": b"RIFF\x00\x00\x00\x00WEBP"}


def classify(provider: ProductionFaceVerificationProvider, reference: bytes, presented: bytes) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        outcome, score, confidence, _summary, reason, quality, face_count = provider.compare(reference, presented, FaceScenario.MATCH)
        return {"status": "scored" if score is not None else "unavailable", "outcome": outcome.value, "score": score, "confidence": confidence, "quality": quality.value, "face_count": face_count, "reason": reason, "elapsed_ms": (time.perf_counter() - started) * 1000}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error_type": type(exc).__name__, "reason": str(exc), "elapsed_ms": (time.perf_counter() - started) * 1000}


def concurrency(provider: ProductionFaceVerificationProvider, reference: bytes, presented: bytes, level: int) -> dict[str, Any]:
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=level) as executor:
        rows = list(executor.map(lambda _: classify(provider, reference, presented), range(level)))
    elapsed = (time.perf_counter() - started) * 1000
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    latencies = [row["elapsed_ms"] for row in rows]
    successful = sum(row["status"] == "scored" for row in rows)
    return {"concurrency": level, "requests": level, "successes": successful, "failures": level - successful, "success_rate": successful / level, "p50_ms": statistics.median(latencies), "p95_ms": float(np.percentile(latencies, 95)), "p99_ms": float(np.percentile(latencies, 99)), "wall_ms": elapsed, "peak_rss_kb": after, "rss_growth_kb": max(0, after - before)}


def main() -> None:
    reference = REFERENCE.read_bytes()
    cases = operational_cases()
    provider_specs = {
        "haar_current_default": ("haar", ProductionFaceVerificationProvider(MODEL, MODEL_SHA, "haar")),
        "yunet_candidate": ("yunet", ProductionFaceVerificationProvider(MODEL, MODEL_SHA, "yunet", YUNET, YUNET_SHA, 0.9, 0.0, 6400, 5.0, 35.0, 225.0, 18.0)),
    }
    pipelines = {}
    for name, (detector, provider) in provider_specs.items():
        operational = {case: classify(provider, reference, image) for case, image in cases.items()}
        load = [concurrency(provider, reference, cases["good_frontal"], level) for level in (1, 5, 10, 20)]
        pipelines[name] = {"detector": detector, "operational_cases": operational, "concurrency": load}
    payload = {"environment": "LOCAL", "dataset": "fictional synthetic operational corpus already present in repository; no real subjects", "models": {"sface_sha256": MODEL_SHA, "yunet_sha256": YUNET_SHA}, "configuration": {"detector_score_threshold": 0.9, "blur_threshold": 5.0, "min_face_pixels": 6400, "brightness": [35.0, 225.0], "contrast_min": 18.0, "alignment": "alignCrop", "verification_threshold": 0.363}, "pipelines": pipelines, "raw_images_committed": False, "render_numbers": False, "peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    Path("benchmarks/phase2_final_operational_benchmark.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
