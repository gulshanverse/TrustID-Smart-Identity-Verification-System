from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import time
from pathlib import Path

import cv2
import numpy as np

from app.domain.face import ProductionFaceVerificationProvider


def write_variant(source: Path, destination: Path, kind: str) -> None:
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"could not read {source}")
    if kind == "brightness":
        image = cv2.convertScaleAbs(image, alpha=1.0, beta=18)
    elif kind == "blur":
        image = cv2.GaussianBlur(image, (9, 9), 0)
    elif kind == "rotate":
        height, width = image.shape[:2]
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), 4, 1)
        image = cv2.warpAffine(image, matrix, (width, height), borderMode=cv2.BORDER_REPLICATE)
    elif kind == "dark":
        image = cv2.convertScaleAbs(image, alpha=0.55, beta=0)
    elif kind == "small":
        image = cv2.resize(image, (320, 426), interpolation=cv2.INTER_AREA)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(destination), image, [cv2.IMWRITE_JPEG_QUALITY, 88]):
        raise RuntimeError(f"could not write {destination}")


def percentile(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values), percentage))


def summary(values: list[float], decisions: list[str]) -> dict[str, object]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "stddev": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "p05": percentile(values, 5),
        "p95": percentile(values, 95),
        "decisions": {decision: decisions.count(decision) for decision in sorted(set(decisions))},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/face_recognition_sface_2021dec.onnx")
    parser.add_argument("--expected-sha256", default=None)
    parser.add_argument("--corpus", default="benchmarks/synthetic_faces")
    parser.add_argument("--output", default="benchmarks/phase2_face_benchmark.json")
    args = parser.parse_args()
    corpus = Path(args.corpus)
    references = sorted(corpus.glob("person_*_reference.png"))
    if len(references) < 5:
        raise RuntimeError("at least five fictional reference faces are required")
    for reference in references:
        identity = reference.stem.replace("_reference", "")
        for kind in ("brightness", "blur", "rotate", "dark", "small"):
            write_variant(reference, corpus / identity / f"{kind}.jpg", kind)
        cv2.imwrite(str(corpus / identity / "reference.jpg"), cv2.imread(str(reference)))

    start_load = time.perf_counter()
    provider = ProductionFaceVerificationProvider(args.model, args.expected_sha256)
    load_ms = (time.perf_counter() - start_load) * 1000
    embedding_dimension = None
    rows: list[dict[str, object]] = []
    genuine_scores: list[float] = []
    genuine_decisions: list[str] = []
    impostor_scores: list[float] = []
    impostor_decisions: list[str] = []
    identity_files = {reference.stem.replace("_reference", ""): sorted((corpus / reference.stem.replace("_reference", "")).glob("*.jpg")) for reference in references}
    for reference in references:
        reference_id = reference.stem.replace("_reference", "")
        for presented_id, files in identity_files.items():
            if not files:
                continue
            for presented in files:
                same_identity = reference_id == presented_id
                started = time.perf_counter()
                try:
                    outcome, similarity, _, _, failure, quality, face_count = provider.compare(reference.read_bytes(), presented.read_bytes())
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    decision = outcome.value
                    if similarity is not None:
                        (genuine_scores if same_identity else impostor_scores).append(similarity)
                        (genuine_decisions if same_identity else impostor_decisions).append(decision)
                    rows.append({"reference_id": reference_id, "presented_id": presented_id, "same_identity": same_identity, "quality": quality.value, "face_count": face_count, "similarity": similarity, "decision": decision, "failure": failure, "processing_ms": elapsed_ms})
                except Exception as exc:
                    rows.append({"reference_id": reference_id, "presented_id": presented_id, "same_identity": same_identity, "quality": "ERROR", "face_count": None, "similarity": None, "decision": "ERROR", "failure": type(exc).__name__, "processing_ms": (time.perf_counter() - started) * 1000})
    embedding_dimension = getattr(provider, "embedding_dimension", None)
    timings = [float(row["processing_ms"]) for row in rows]
    payload = {"label": "CONTROLLED SYNTHETIC VALIDATION", "model": {"filename": Path(args.model).name, "size_bytes": Path(args.model).stat().st_size, "sha256": provider.model_sha256, "opencv_version": cv2.__version__, "runtime": "OpenCV DNN FaceRecognizerSF on CPU", "input": "BGR crop resized to 112x112; Haar single-face detection; no landmark alignment", "embedding_dimension": embedding_dimension}, "load_ms": load_ms, "timing_ms": summary(timings, []), "error_rows": sum(row["decision"] == "ERROR" for row in rows), "thresholds": {"match": provider.threshold, "review": provider.review_threshold}, "genuine": summary(genuine_scores, genuine_decisions), "impostor": summary(impostor_scores, impostor_decisions), "rows": rows}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2))
    with output.with_suffix(".csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({key: payload[key] for key in ("model", "load_ms", "timing_ms", "error_rows", "thresholds", "genuine", "impostor")}, indent=2))


if __name__ == "__main__":
    main()
