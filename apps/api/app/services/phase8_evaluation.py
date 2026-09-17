from __future__ import annotations

"""Small, dependency-free evaluation harness for labeled fixtures."""

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class FieldMetric:
    field: str
    samples: int
    exact_matches: int
    accuracy: float | None


def field_metrics(rows: Iterable[Mapping[str, Any]], field: str) -> FieldMetric:
    values = list(rows)
    comparable = [row for row in values if row.get("expected") is not None and row.get("actual") is not None]
    matches = sum(str(row["expected"]).strip().upper() == str(row["actual"]).strip().upper() for row in comparable)
    return FieldMetric(field, len(comparable), matches, None if not comparable else matches / len(comparable))


def reproducible_report(dataset_id: str, rows: Iterable[Mapping[str, Any]], *, model_version: str = "NOT_AVAILABLE", threshold: float | None = None) -> dict[str, Any]:
    materialized = [dict(row) for row in rows]
    encoded = json.dumps(materialized, sort_keys=True, separators=(",", ":")).encode()
    metrics = [field_metrics(materialized, field) for field in sorted({str(row.get("field", "unknown")) for row in materialized})]
    return {
        "status": "MEASURED" if materialized else "DATASET_VALIDATION_PENDING",
        "dataset_id": dataset_id,
        "sample_count": len(materialized),
        "field_metrics": [metric.__dict__ for metric in metrics],
        "dataset_fingerprint": hashlib.sha256(encoded).hexdigest(),
        "commit_sha": _commit_sha(),
        "environment": {"python": sys.version.split()[0], "platform": os.name},
        "model_version": model_version,
        "threshold": threshold,
        "timestamp": datetime.now(UTC).isoformat(),
        "limitations": ["Metrics apply only to supplied labeled fixtures.", "No production accuracy or demographic fairness claim is made."],
    }


def _commit_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "NOT_AVAILABLE"


def write_report(path: str, report: Mapping[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")


__all__ = ["FieldMetric", "field_metrics", "reproducible_report", "write_report"]
