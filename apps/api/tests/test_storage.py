from unittest.mock import MagicMock, patch

import pytest

from app.domain.documents import S3ObjectStorage


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
