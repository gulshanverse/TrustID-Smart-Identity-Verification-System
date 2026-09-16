from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np


def auc(labels: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(-scores)
    ordered = labels[order]
    positives = float(labels.sum())
    negatives = float(len(labels) - positives)
    if positives == 0 or negatives == 0:
        return float("nan")
    tp = np.cumsum(ordered == 1) / positives
    fp = np.cumsum(ordered == 0) / negatives
    return float(np.trapezoid(np.r_[0.0, tp], np.r_[0.0, fp]))


def main() -> None:
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    payload = json.loads(input_path.read_text())
    genuine = np.asarray([r["similarity"] for r in payload["rows"] if r["same_identity"] and r["similarity"] is not None], dtype=float)
    impostor = np.asarray([r["similarity"] for r in payload["rows"] if not r["same_identity"] and r["similarity"] is not None], dtype=float)
    scores = np.r_[genuine, impostor]
    labels = np.r_[np.ones(len(genuine)), np.zeros(len(impostor))]
    rows = []
    for threshold in [round(x, 3) for x in np.arange(0.20, 0.901, 0.025)] + [0.363]:
        tpr = float(np.mean(genuine >= threshold)) if len(genuine) else float("nan")
        fpr = float(np.mean(impostor >= threshold)) if len(impostor) else float("nan")
        rows.append({"threshold": threshold, "tpr": tpr, "fpr": fpr, "tar": tpr, "far": fpr, "frr": 1.0 - tpr, "accuracy": float(np.mean((scores >= threshold) == labels))})
    eer_row = min(rows, key=lambda row: abs(row["far"] - row["frr"])) if rows else None
    result = {"source": input_path.name, "genuine_scored": len(genuine), "impostor_scored": len(impostor), "auc": auc(labels, scores), "eer_approx": eer_row, "reference_threshold": next(row for row in rows if math.isclose(row["threshold"], 0.363)), "trustid_review_floor": 0.30, "thresholds": rows}
    output_path.write_text(json.dumps(result, indent=2))
    with output_path.with_suffix(".csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"auc": result["auc"], "eer_approx": result["eer_approx"], "reference_threshold": result["reference_threshold"]}, indent=2))


if __name__ == "__main__":
    main()
