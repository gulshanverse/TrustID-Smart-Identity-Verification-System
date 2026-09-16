from __future__ import annotations

import csv
import json
from pathlib import Path


def main() -> None:
    payload = json.loads(Path("benchmarks/phase24_full_lfw_results.json").read_text())
    root = Path("benchmarks/results/phase24")
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    failures = []
    for result in payload["results"]:
        for threshold in result["thresholds"]:
            rows.append({"pipeline": result["pipeline"], **threshold})
        for failure, count in result["failures"].items():
            failures.append({"pipeline": result["pipeline"], "failure_type": failure, "count": count, "percentage_of_pairs": count / result["total_pairs"]})
    for path, values in ((root / "thresholds.csv", rows), (root / "failure_breakdown.csv", failures)):
        with path.open("w", newline="") as handle:
            values = [{key: ("UNDEFINED" if value is None else value) for key, value in row.items()} for row in values]
            writer = csv.DictWriter(handle, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)
    comparison = []
    for result in payload["results"]:
        by_threshold = {row["threshold"]: row for row in result["thresholds"]}
        comparison.append({"pipeline": result["pipeline"], "detector": result["config"]["detector"], "alignment": "alignCrop" if result["pipeline"].startswith("yunet") else "crop_resize", "genuine_coverage": result["genuine_coverage"], "impostor_coverage": result["impostor_coverage"], "scored_genuine": result["genuine_scored"], "scored_impostor": result["impostor_scored"], "auc": "UNDEFINED" if result["auc"] is None else result["auc"], "eer": "UNDEFINED" if result["eer_candidate"] is None else result["eer_candidate"]["threshold"], "tpr_at_363": "UNDEFINED" if by_threshold[0.363]["tpr_tar"] is None else by_threshold[0.363]["tpr_tar"], "far_at_363": "UNDEFINED" if by_threshold[0.363]["far_fpr"] is None else by_threshold[0.363]["far_fpr"], "frr_at_363": "UNDEFINED" if by_threshold[0.363]["frr"] is None else by_threshold[0.363]["frr"], "tpr_at_30": "UNDEFINED" if by_threshold[0.3]["tpr_tar"] is None else by_threshold[0.3]["tpr_tar"], "far_at_30": "UNDEFINED" if by_threshold[0.3]["far_fpr"] is None else by_threshold[0.3]["far_fpr"], "frr_at_30": "UNDEFINED" if by_threshold[0.3]["frr"] is None else by_threshold[0.3]["frr"], "successful_mean_ms": result["latency_ms"]["successful"]["mean"], "successful_p95_ms": result["latency_ms"]["successful"]["p95"]})
    with (root / "comparison.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison[0]))
        writer.writeheader()
        writer.writerows(comparison)


if __name__ == "__main__":
    main()
