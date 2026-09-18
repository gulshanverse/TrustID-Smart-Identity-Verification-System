from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from phase9_validate import build_report, correlation_benchmark


def test_phase9_report_is_secret_safe_and_truthful(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret-user:secret-password@db.example.test/trustid")
    report = build_report()
    encoded = json.dumps(report)
    assert "secret-password" not in encoded
    assert "secret-user" not in encoded
    assert report["configuration"]["secret_values_exposed"] is False
    assert report["capabilities"]["live_postgresql"] == "EXTERNAL_VALIDATION_PENDING"
    assert report["capabilities"]["liveness"]["status"] == "NOT_IMPLEMENTED"
    assert report["fixture_evaluation"]["production_accuracy_claim"] is False


def test_phase9_correlation_benchmark_is_deterministic() -> None:
    first = correlation_benchmark(iterations=5)
    second = correlation_benchmark(iterations=5)
    assert first["finding_count"] == 4
    assert first["finding_fingerprint"] == second["finding_fingerprint"]
    assert first["production_performance_claim"] is False
