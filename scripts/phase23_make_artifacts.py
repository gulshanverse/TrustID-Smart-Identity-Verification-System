from __future__ import annotations

import csv
import json
from pathlib import Path


def main() -> None:
    source = Path("benchmarks/phase23_lfw_results.json")
    payload = json.loads(source.read_text())
    root = Path("benchmarks/results/lfw")
    root.mkdir(parents=True, exist_ok=True)
    (root / "results.json").write_text(json.dumps(payload, indent=2))
    threshold_rows = []
    roc_rows = []
    histogram_rows = []
    for result in payload["results"]:
        pipeline = result["pipeline"]
        for row in result["thresholds"]:
            threshold_rows.append({"pipeline": pipeline, **row})
            if row["tpr_tar"] is not None and row["far_fpr"] is not None:
                roc_rows.append({"pipeline": pipeline, "threshold": row["threshold"], "fpr": row["far_fpr"], "tpr": row["tpr_tar"]})
        for kind, bins in result["score_histogram"].items():
            for row in bins:
                histogram_rows.append({"pipeline": pipeline, "score_type": kind, **row})
    for path, rows in ((root / "threshold_analysis.csv", threshold_rows), (root / "roc.csv", roc_rows), (root / "score_distribution.csv", histogram_rows)):
        rows = [{key: ("NA" if value is None else value) for key, value in row.items()} for row in rows]
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["pipeline"])
            writer.writeheader()
            writer.writerows(rows)
    try:
        import matplotlib.pyplot as plt
        fig, axis = plt.subplots(figsize=(6, 5))
        for result in payload["results"]:
            points = [row for row in result["thresholds"] if row["tpr_tar"] is not None and row["far_fpr"] is not None]
            if points:
                axis.plot([row["far_fpr"] for row in points], [row["tpr_tar"] for row in points], marker="o", label=result["pipeline"])
        axis.plot([0, 1], [0, 1], linestyle="--", color="gray", label="chance")
        axis.set(xlim=(0, 1), ylim=(0, 1), xlabel="False acceptance rate (FAR/FPR)", ylabel="True acceptance rate (TPR/TAR)", title="LFW aggregate threshold ROC points")
        axis.legend()
        fig.tight_layout()
        fig.savefig(root / "roc.png", dpi=160)
        plt.close(fig)
        fig, axis = plt.subplots(figsize=(7, 5))
        for result in payload["results"]:
            for kind, bins in result["score_histogram"].items():
                nonzero = [row for row in bins if row["count"]]
                if nonzero:
                    centers = [(row["lower"] + row["upper"]) / 2 for row in nonzero]
                    axis.plot(centers, [row["count"] for row in nonzero], marker="o", label=f"{result['pipeline']} {kind}")
        axis.axvline(0.30, linestyle="--", color="orange", label="policy 0.30")
        axis.axvline(0.363, linestyle="--", color="red", label="reference 0.363")
        axis.set(xlim=(0, 1), xlabel="Cosine similarity", ylabel="Aggregate scored-pair count", title="LFW aggregate score distributions")
        axis.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(root / "score_distribution.png", dpi=160)
        plt.close(fig)
    except ImportError:
        (root / "plots.blocked.txt").write_text("matplotlib unavailable; CSV aggregate artifacts were still produced.\n")


if __name__ == "__main__":
    main()
