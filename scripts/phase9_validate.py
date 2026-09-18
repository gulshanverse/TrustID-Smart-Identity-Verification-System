"""Generate a truthful, secret-safe Phase 9 local validation report.

This runner only reports checks that can be executed in the current environment.
It never prints environment values, uploads data, or labels fixtures as production
accuracy. Live infrastructure and provider validation remain explicitly pending.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from subprocess import CalledProcessError, check_output

from app.domain.advanced_document_intelligence import (
    advanced_forensics_boundary,
    correlate_documents,
    liveness_boundary,
)
from app.services.phase8_evaluation import reproducible_report

REPO_ROOT = Path(__file__).resolve().parents[1]


def commit_sha() -> str:
    try:
        return check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, stderr=open(os.devnull, "w")).strip()
    except (OSError, CalledProcessError):
        return "NOT_AVAILABLE"


def env_status() -> dict[str, object]:
    names = (
        "APP_ENV",
        "DATABASE_URL",
        "REDIS_URL",
        "OBJECT_STORAGE_ENDPOINT",
        "OBJECT_STORAGE_BUCKET",
        "OCR_PROVIDER",
        "TAMPERING_PROVIDER",
        "FACE_PROVIDER",
        "CORS_ORIGINS",
        "NEXT_PUBLIC_API_URL",
    )
    configured = {name: bool(os.getenv(name, "").strip()) for name in names}
    return {
        "status": "LOCALLY_VALIDATED",
        "configured_variables": configured,
        "secret_values_exposed": False,
        "production_deployment": "EXTERNAL_VALIDATION_PENDING",
    }


def fixture_evaluation() -> dict[str, object]:
    rows = [
        {"field": "full_name", "expected": "FICTIONAL APPLICANT", "actual": "FICTIONAL APPLICANT"},
        {"field": "date_of_birth", "expected": "1990-01-01", "actual": "1990-01-01"},
    ]
    report = reproducible_report("phase9-fixture-v1", rows, model_version="DETERMINISTIC_FIXTURE_RULES")
    report["validation_scope"] = "FIXTURE_VALIDATION_ONLY"
    report["production_accuracy_claim"] = False
    return report


def correlation_benchmark(iterations: int = 1000) -> dict[str, object]:
    documents = [
        ("PASSPORT:fixture-a", {"full_name": "FICTIONAL APPLICANT", "date_of_birth": "1990-01-01", "visa_reference": "REF-001", "expiry_date": "2030-01-01"}),
        ("VISA:fixture-b", {"full_name": "FICTIONAL OTHER", "date_of_birth": "1991-01-01", "visa_reference": "REF-002", "expiry_date": "2029-01-01"}),
    ]
    start = time.perf_counter()
    findings = ()
    for _ in range(iterations):
        findings = correlate_documents(documents)
    elapsed_ms = (time.perf_counter() - start) * 1000
    material = json.dumps([item.__dict__ for item in findings], sort_keys=True).encode()
    return {
        "status": "LOCALLY_VALIDATED",
        "scope": "SYNTHETIC_FIXTURE_MICROBENCHMARK_ONLY",
        "iterations": iterations,
        "finding_count": len(findings),
        "finding_fingerprint": sha256(material).hexdigest(),
        "elapsed_ms": round(elapsed_ms, 3),
        "mean_ms": round(elapsed_ms / iterations, 6),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "commit_sha": commit_sha(),
        "production_performance_claim": False,
    }


def build_report() -> dict[str, object]:
    return {
        "report_type": "PHASE_9_LOCAL_VALIDATION",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_sha": commit_sha(),
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "configuration": env_status(),
        "capabilities": {
            "cross_document_correlation": "LOCALLY_VALIDATED",
            "risk_authority": "LOCALLY_VALIDATED",
            "advanced_forensics": advanced_forensics_boundary(),
            "liveness": liveness_boundary(),
            "live_postgresql": "EXTERNAL_VALIDATION_PENDING",
            "live_redis": "EXTERNAL_VALIDATION_PENDING",
            "live_object_storage": "EXTERNAL_VALIDATION_PENDING",
            "production_ocr": "EXTERNAL_VALIDATION_PENDING",
            "production_face": "EXTERNAL_VALIDATION_PENDING",
        },
        "fixture_evaluation": fixture_evaluation(),
        "benchmark": correlation_benchmark(),
        "limitations": [
            "No live credentials or managed services were contacted.",
            "Fixture measurements are not production accuracy.",
            "Liveness/PAD remains NOT_IMPLEMENTED.",
            "No sensitive identity or biometric data was processed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="JSON output path")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build_report(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote secret-safe Phase 9 validation report to {args.output}")


if __name__ == "__main__":
    main()
