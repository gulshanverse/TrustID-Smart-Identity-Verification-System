from __future__ import annotations

import json
import statistics
from pathlib import Path

import cv2
import numpy as np
from sklearn.datasets import fetch_lfw_pairs


def main() -> None:
    data = fetch_lfw_pairs(subset="10_folds", color=True, resize=2.0, funneled=True, download_if_missing=True, data_home="/tmp/trustid-lfw")
    sample = data.pairs[:100].reshape(-1, *data.pairs.shape[2:])
    brightness = []
    contrast = []
    sharpness = []
    for image in sample:
        bgr = cv2.cvtColor(np.clip(image * 255, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        brightness.append(float(gray.mean()))
        contrast.append(float(gray.std()))
        sharpness.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
    def summary(values: list[float]) -> dict[str, float]:
        return {"mean": statistics.mean(values), "median": statistics.median(values), "min": min(values), "max": max(values), "p05": float(np.percentile(values, 5)), "p95": float(np.percentile(values, 95))}
    payload = {"sample_pairs": 100, "sample_images": len(sample), "source_dtype": str(data.pairs.dtype), "source_shape": list(data.pairs.shape[2:]), "channels": 3, "source_color_format": "RGB float32 normalized 0..1 from loader", "benchmark_decode_format": "JPEG bytes decoded by OpenCV as BGR uint8", "brightness_gray": summary(brightness), "contrast_gray": summary(contrast), "sharpness_laplacian_variance": summary(sharpness), "normalization": {"deterministic": True, "scale_float32_to_uint8": True, "encode_jpeg_quality": 95, "resize": "source loader resize=2.0 only; no sharpening, contrast enhancement, or identity-altering transform"}}
    Path("benchmarks/phase24_input_analysis.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
