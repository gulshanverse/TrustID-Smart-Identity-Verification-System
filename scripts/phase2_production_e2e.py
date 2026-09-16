from __future__ import annotations

import json
import resource
import time
from pathlib import Path
from uuid import uuid4

from app.db.models import AuditEventModel, Base, FaceVerificationModel
from app.domain.documents import DocumentType, InMemoryObjectStorage
from app.domain.face import ProductionFaceVerificationProvider
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.repositories.face_repository import SqlAlchemyFaceRepository
from app.services.document_service import DocumentService
from app.services.face_service import FaceVerificationService
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


def run() -> dict[str, object]:
    root = Path("benchmarks/synthetic_faces")
    reference = (root / "person_001_reference.png").read_bytes()
    genuine = (root / "person_001" / "brightness.jpg").read_bytes()
    impostor = (root / "person_002" / "reference.jpg").read_bytes()
    model = "models/face_recognition_sface_2021dec.onnx"
    sha256 = "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    storage = InMemoryObjectStorage()
    actor = uuid4()
    with Session(engine) as db:
        documents = DocumentService(storage, SqlAlchemyDocumentRepository(db))
        verification = documents.create_verification(actor, "synthetic-officer@example.test", "Synthetic Officer")
        document = documents.upload(verification.id, actor, "fictional-passport.png", "image/png", reference, DocumentType.PASSPORT)
        provider = ProductionFaceVerificationProvider(model, sha256)
        service = FaceVerificationService(storage, SqlAlchemyFaceRepository(db), provider)
        results = []
        start = time.perf_counter()
        for label, presented in (("genuine", genuine), ("impostor", impostor)):
            result = service.process(document.id, actor, presented, "image/jpeg")
            results.append({"label": label, "outcome": result.outcome.value, "similarity": result.similarity_score, "provider": result.provider, "face_count": result.face_count, "quality": result.presented_face_quality.value})
        elapsed_ms = (time.perf_counter() - start) * 1000
        persisted = db.scalars(select(FaceVerificationModel).where(FaceVerificationModel.document_id == document.id)).all()
        audit = db.scalars(select(AuditEventModel).where(AuditEventModel.document_id == document.id)).all()
        return {"provider_initialized": True, "model_sha256": provider.model_sha256, "results": results, "persisted_result_count": len(persisted), "audit_events": [event.event_type for event in audit], "embeddings_persisted": any(hasattr(row, "embedding") for row in persisted), "elapsed_ms": elapsed_ms, "peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


if __name__ == "__main__":
    output = run()
    Path("benchmarks/phase2_production_e2e.json").write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
