from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import AuditEventModel, Base, ReportModel
from app.domain.documents import DocumentType, InMemoryObjectStorage
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.services.analytics_service import AnalyticsFilters, AnalyticsService
from app.services.document_service import DocumentService
from app.services.report_service import ReportService


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def test_empty_analytics_distinguishes_no_data_from_unavailable(db: Session) -> None:
    now = datetime.now(UTC)
    result = AnalyticsService(db).overview(AnalyticsFilters(now - timedelta(days=7), now))
    assert result["verification"] == {"total": 0, "completed": 0, "failed": 0, "pending": 0, "completion_rate": None}
    assert result["risk"]["average_score"] is None
    assert result["demo"] is False


def test_analytics_filters_are_utc_and_trends_are_empty(db: Session) -> None:
    now = datetime.now(UTC)
    filters = AnalyticsFilters(now - timedelta(days=30), now)
    assert AnalyticsService(db).trends(filters) == []
    assert filters.start.tzinfo is not None and filters.end.tzinfo is not None


def test_report_requires_authorized_persisted_verification(db: Session) -> None:
    actor = uuid4()
    documents = DocumentService(InMemoryObjectStorage(), SqlAlchemyDocumentRepository(db))
    verification = documents.create_verification(actor, f"report-{actor}@example.test", "Officer")
    documents.upload(verification.id, actor, "report.pdf", "application/pdf", b"%PDF-1.7", DocumentType.PASSPORT)
    content, report_id = ReportService(db).verification_report(verification.id, actor)
    assert content.startswith(b"%PDF")
    assert db.scalar(select(ReportModel).where(ReportModel.id == report_id)) is not None
    assert db.scalar(select(AuditEventModel).where(AuditEventModel.event_type == "REPORT_GENERATED")) is not None
    with pytest.raises(LookupError): ReportService(db).verification_report(verification.id, uuid4())
