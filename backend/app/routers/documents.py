from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.models import Document
from app.schemas import DocumentOut
from app.services.ingest import ensure_upload_dir, ingest_document
from app.services.insights import ensure_insights
from app.services.sample_docs import generate_all

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _ingest_job(document_id: str) -> None:
    db = SessionLocal()
    try:
        ingest_document(db, document_id)
    finally:
        db.close()


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    for d in docs:
        if d.status == "ready" and not d.insights:
            try:
                ensure_insights(db, d)
            except Exception:
                pass
    return docs


@router.post("/seed", response_model=list[DocumentOut])
def seed_sample_documents(background: BackgroundTasks, db: Session = Depends(get_db)):
    """Generate and ingest three fictional engineering PDFs for the demo."""
    existing = {d.filename for d in db.query(Document).all()}
    created: list[Document] = []
    sample_dir = ensure_upload_dir() / "samples"
    paths = generate_all(sample_dir)
    for path in paths:
        if path.name in existing:
            continue
        doc_id = str(uuid4())
        dest = ensure_upload_dir() / f"{doc_id}.pdf"
        shutil.copyfile(path, dest)
        doc = Document(
            id=doc_id,
            filename=path.name,
            title=path.stem.replace("_", " "),
            status="processing",
            storage_path=str(dest),
        )
        db.add(doc)
        created.append(doc)
    db.commit()
    for doc in created:
        db.refresh(doc)
        background.add_task(_ingest_job, doc.id)
    if not created:
        return db.query(Document).order_by(Document.created_at.desc()).all()
    return created


@router.post("", response_model=DocumentOut)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")
    upload_dir = ensure_upload_dir()
    doc_id = str(uuid4())
    dest = upload_dir / f"{doc_id}.pdf"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    doc = Document(
        id=doc_id,
        filename=file.filename,
        title=file.filename,
        status="processing",
        storage_path=str(dest),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    background.add_task(_ingest_job, doc_id)
    return doc


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/{document_id}/file")
def get_document_file(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or not Path(doc.storage_path).exists():
        raise HTTPException(404, "File not found")
    return FileResponse(doc.storage_path, media_type="application/pdf", filename=doc.filename)


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    path = Path(doc.storage_path)
    db.delete(doc)
    db.commit()
    if path.exists():
        path.unlink()
    return {"ok": True}
