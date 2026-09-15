from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app import main
from app.domain.documents import S3ObjectStorage, safe_exception_message


def test_s3_storage_forces_path_style_addressing() -> None:
    fake_client = MagicMock()
    with patch("boto3.client", return_value=fake_client) as client_factory:
        storage = S3ObjectStorage(
            "https://storage.example.test/storage/v1/s3",
            "trustid-documents",
            "access-key",
            "secret-key",
            "ap-south-1",
        )

    client_factory.assert_called_once()
    config = client_factory.call_args.kwargs["config"]
    assert config.s3["addressing_style"] == "path"
    assert storage.bucket == "trustid-documents"


def test_s3_put_object_omits_unsupported_encryption_header() -> None:
    fake_client = MagicMock()
    with patch("boto3.client", return_value=fake_client):
        storage = S3ObjectStorage(
            "https://storage.example.test/storage/v1/s3",
            "trustid-documents",
            "access-key",
            "secret-key",
            "ap-south-1",
        )

    storage.put("verifications/demo/documents/file.pdf", b"%PDF-demo", "application/pdf")

    request = fake_client.put_object.call_args.kwargs
    assert request["Bucket"] == "trustid-documents"
    assert request["Key"] == "verifications/demo/documents/file.pdf"
    assert request["ContentType"] == "application/pdf"
    assert request["Body"].read() == b"%PDF-demo"
    assert "ServerSideEncryption" not in request


def test_s3_storage_logs_sanitized_operation_errors(caplog: pytest.LogCaptureFixture) -> None:
    with patch("boto3.client", return_value=MagicMock()) as client_factory:
        storage = S3ObjectStorage(
            "https://storage.example.test/storage/v1/s3",
            "trustid-documents",
            "access-key",
            "secret-key",
            "ap-south-1",
        )
    client = client_factory.return_value
    client.put_object.side_effect = RuntimeError(
        "request failed https://storage.example.test/x?access_key=access-key secret_key=secret-key"
    )

    with caplog.at_level("WARNING", logger="trustid.storage"), pytest.raises(RuntimeError):
        storage.put("verifications/demo/documents/file.pdf", b"%PDF-demo", "application/pdf")

    record = next(record for record in caplog.records if record.name == "trustid.storage")
    assert "s3_storage_operation_failed" in record.message
    assert "operation=put" in record.message
    assert "storage_key=verifications/demo/documents/file.pdf" in record.message
    assert "error_type=RuntimeError" in record.message
    assert "access-key" not in record.message
    assert "secret-key" not in record.message
    assert "https://" not in record.message


def test_production_storage_initialization_does_not_downgrade_silently(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        app_env="production",
        object_storage_endpoint="https://storage.example.test/s3",
        object_storage_bucket="trustid-documents",
        object_storage_access_key="configured-access-key",
        object_storage_secret_key="configured-secret-key",
        object_storage_region="ap-south-1",
    )
    monkeypatch.setattr(main, "settings", settings)
    with patch.object(main, "S3ObjectStorage", side_effect=RuntimeError("client unavailable")), pytest.raises(RuntimeError, match="Production object storage"):
        main.initialize_storage()


def test_exception_chain_preserves_sanitized_root_cause() -> None:
    try:
        raise ValueError("database_url=postgresql://user:password@db.example.test/app user@example.test")
    except ValueError as cause:
        wrapped = RuntimeError("Document metadata could not be saved.")
        wrapped.__cause__ = cause

    message = safe_exception_message(wrapped)

    assert "RuntimeError: Document metadata could not be saved." in message
    assert "ValueError:" in message
    assert "password" not in message
    assert "user@example.test" not in message
    assert "postgresql://" not in message
