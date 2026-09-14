from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    roles: Mapped[list[RoleModel]] = relationship(secondary=user_roles, back_populates="users")


class RoleModel(Base):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")


class VerificationModel(Base):
    __tablename__ = "verifications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    documents: Mapped[list[DocumentModel]] = relationship(back_populates="verification", cascade="all, delete-orphan")
    risk_assessments: Mapped[list[RiskAssessmentModel]] = relationship(back_populates="verification", cascade="all, delete-orphan")
    cases: Mapped[list[CaseModel]] = relationship(back_populates="verification", cascade="all, delete-orphan")


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    verification_id: Mapped[UUID] = mapped_column(ForeignKey("verifications.id", ondelete="CASCADE"), index=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(180), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    verification: Mapped[VerificationModel] = relationship(back_populates="documents")
    ocr_results: Mapped[list[OCRResultModel]] = relationship(back_populates="document", cascade="all, delete-orphan")
    tampering_results: Mapped[list[TamperingResultModel]] = relationship(back_populates="document", cascade="all, delete-orphan")
    face_verifications: Mapped[list[FaceVerificationModel]] = relationship(back_populates="document", cascade="all, delete-orphan")


class OCRResultModel(Base):
    __tablename__ = "ocr_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_text: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    overall_confidence: Mapped[float] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    document: Mapped[DocumentModel] = relationship(back_populates="ocr_results")
    fields: Mapped[list[OCRFieldModel]] = relationship(back_populates="result", cascade="all, delete-orphan")


class OCRFieldModel(Base):
    __tablename__ = "ocr_fields"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ocr_result_id: Mapped[UUID] = mapped_column(ForeignKey("ocr_results.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    normalized_value: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    source_text: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[OCRResultModel] = relationship(back_populates="fields")
    evidence: Mapped[list[OCREvidenceModel]] = relationship(back_populates="field", cascade="all, delete-orphan")


class OCREvidenceModel(Base):
    __tablename__ = "ocr_evidence"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ocr_field_id: Mapped[UUID] = mapped_column(ForeignKey("ocr_fields.id", ondelete="CASCADE"), index=True)
    page: Mapped[int | None] = mapped_column(nullable=True)
    text: Mapped[str | None] = mapped_column(String, nullable=True)
    start_offset: Mapped[int | None] = mapped_column(nullable=True)
    end_offset: Mapped[int | None] = mapped_column(nullable=True)
    line_index: Mapped[int | None] = mapped_column(nullable=True)
    field: Mapped[OCRFieldModel] = relationship(back_populates="evidence")


class TamperingResultModel(Base):
    __tablename__ = "tampering_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    technical_signal_score: Mapped[float] = mapped_column(nullable=False)
    overall_confidence: Mapped[float] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    document: Mapped[DocumentModel] = relationship(back_populates="tampering_results")
    findings: Mapped[list[TamperingFindingModel]] = relationship(back_populates="result", cascade="all, delete-orphan")


class TamperingFindingModel(Base):
    __tablename__ = "tampering_findings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tampering_result_id: Mapped[UUID] = mapped_column(ForeignKey("tampering_results.id", ondelete="CASCADE"), index=True)
    finding_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    related_ocr_field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[TamperingResultModel] = relationship(back_populates="findings")
    evidence: Mapped[list[TamperingEvidenceModel]] = relationship(back_populates="finding", cascade="all, delete-orphan")


class TamperingEvidenceModel(Base):
    __tablename__ = "tampering_evidence"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tampering_finding_id: Mapped[UUID] = mapped_column(ForeignKey("tampering_findings.id", ondelete="CASCADE"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    page: Mapped[int | None] = mapped_column(nullable=True)
    region: Mapped[str | None] = mapped_column(String(160), nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    technical_signal: Mapped[str] = mapped_column(String(160), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    finding: Mapped[TamperingFindingModel] = relationship(back_populates="evidence")


class FaceVerificationModel(Base):
    __tablename__ = "face_verifications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    verification_id: Mapped[UUID] = mapped_column(ForeignKey("verifications.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    document_face_quality: Mapped[str] = mapped_column(String(32), nullable=False)
    presented_face_quality: Mapped[str] = mapped_column(String(32), nullable=False)
    face_count: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    document: Mapped[DocumentModel] = relationship(back_populates="face_verifications")
    evidence: Mapped[list[FaceVerificationEvidenceModel]] = relationship(back_populates="result", cascade="all, delete-orphan")


class FaceVerificationEvidenceModel(Base):
    __tablename__ = "face_verification_evidence"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    face_verification_id: Mapped[UUID] = mapped_column(ForeignKey("face_verifications.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(String(160), nullable=False)
    explanation: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[FaceVerificationModel] = relationship(back_populates="evidence")


class DocumentValidationModel(Base):
    __tablename__ = "document_validations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    document: Mapped[DocumentModel] = relationship()
    findings: Mapped[list[DocumentValidationFindingModel]] = relationship(back_populates="validation", cascade="all, delete-orphan")


class DocumentValidationFindingModel(Base):
    __tablename__ = "document_validation_findings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    validation_id: Mapped[UUID] = mapped_column(ForeignKey("document_validations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    passed: Mapped[bool] = mapped_column(nullable=False)
    explanation: Mapped[str] = mapped_column(String, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    validation: Mapped[DocumentValidationModel] = relationship(back_populates="findings")


class RiskAssessmentModel(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    verification_id: Mapped[UUID] = mapped_column(ForeignKey("verifications.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    recommendation: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    assessment_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    verification: Mapped[VerificationModel] = relationship(back_populates="risk_assessments")
    factors: Mapped[list[RiskFactorModel]] = relationship(back_populates="assessment", cascade="all, delete-orphan")


class RiskFactorModel(Base):
    __tablename__ = "risk_factors"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    risk_assessment_id: Mapped[UUID] = mapped_column(ForeignKey("risk_assessments.id", ondelete="CASCADE"), index=True)
    factor_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_module: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    contribution: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(String, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    assessment: Mapped[RiskAssessmentModel] = relationship(back_populates="factors")


class CaseModel(Base):
    __tablename__ = "cases"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    verification_id: Mapped[UUID] = mapped_column(ForeignKey("verifications.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_supervisor: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    resolved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification: Mapped[VerificationModel] = relationship(back_populates="cases")
    evidence: Mapped[list[CaseEvidenceModel]] = relationship(back_populates="case", cascade="all, delete-orphan")
    notes: Mapped[list[CaseNoteModel]] = relationship(back_populates="case", cascade="all, delete-orphan")
    decisions: Mapped[list[CaseDecisionModel]] = relationship(back_populates="case", cascade="all, delete-orphan")


class CaseEvidenceModel(Base):
    __tablename__ = "case_evidence"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    case: Mapped[CaseModel] = relationship(back_populates="evidence")


class CaseNoteModel(Base):
    __tablename__ = "case_notes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    case: Mapped[CaseModel] = relationship(back_populates="notes")


class CaseDecisionModel(Base):
    __tablename__ = "case_decisions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    decided_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    case: Mapped[CaseModel] = relationship(back_populates="decisions")


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    verification_id: Mapped[UUID] = mapped_column(ForeignKey("verifications.id", ondelete="RESTRICT"), index=True)
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id", ondelete="RESTRICT"), nullable=True, index=True)
    ocr_result_id: Mapped[UUID | None] = mapped_column(ForeignKey("ocr_results.id", ondelete="SET NULL"), nullable=True, index=True)
    tampering_result_id: Mapped[UUID | None] = mapped_column(ForeignKey("tampering_results.id", ondelete="SET NULL"), nullable=True, index=True)
    face_verification_id: Mapped[UUID | None] = mapped_column(ForeignKey("face_verifications.id", ondelete="SET NULL"), nullable=True, index=True)
    validation_id: Mapped[UUID | None] = mapped_column(ForeignKey("document_validations.id", ondelete="SET NULL"), nullable=True, index=True)
    risk_assessment_id: Mapped[UUID | None] = mapped_column(ForeignKey("risk_assessments.id", ondelete="SET NULL"), nullable=True, index=True)
    case_id: Mapped[UUID | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
