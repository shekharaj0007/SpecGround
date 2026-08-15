from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Chunk, Document, Element
from app.services.chunker import chunk_document
from app.services.embeddings import embed_texts
from app.services.insights import build_insights
from app.services.parser import parse_pdf


def ingest_document(db: Session, document_id: str) -> None:
    doc = db.get(Document, document_id)
    if not doc:
        return
    try:
        parsed = parse_pdf(doc.storage_path)
        doc.title = parsed.title
        doc.page_count = parsed.page_count
        doc.standard_code = parsed.standard_code
        doc.doc_type = parsed.doc_type

        db.query(Element).filter(Element.document_id == document_id).delete()
        db.execute(text("UPDATE chunks SET parent_id = NULL WHERE document_id = :id"), {"id": document_id})
        db.query(Chunk).filter(Chunk.document_id == document_id).delete()
        db.flush()

        for el in parsed.elements:
            db.add(
                Element(
                    document_id=document_id,
                    page_number=el.page_number,
                    element_type=el.element_type,
                    section_number=el.section_number,
                    content=el.content,
                    table_json=el.table_json,
                    bbox=el.bbox,
                    reading_order=el.reading_order,
                )
            )

        drafts = chunk_document(parsed)
        children = [d for d in drafts if not d.is_parent]
        parents = [d for d in drafts if d.is_parent]
        parent_vecs = embed_texts([d.content for d in parents])
        child_vecs = embed_texts([d.content for d in children])

        for draft, vec in zip(parents, parent_vecs):
            db.add(
                Chunk(
                    id=draft.id,
                    document_id=document_id,
                    parent_id=None,
                    content=draft.content,
                    element_type=draft.element_type,
                    section_number=draft.section_number,
                    page_number=draft.page_number,
                    bbox=draft.bbox,
                    is_parent=True,
                    embedding=vec,
                )
            )
        db.flush()
        for draft, vec in zip(children, child_vecs):
            db.add(
                Chunk(
                    id=draft.id,
                    document_id=document_id,
                    parent_id=draft.parent_id,
                    content=draft.content,
                    element_type=draft.element_type,
                    section_number=draft.section_number,
                    page_number=draft.page_number,
                    bbox=draft.bbox,
                    is_parent=False,
                    embedding=vec,
                )
            )
        db.flush()
        if settings.database_url.startswith("postgresql"):
            db.execute(
                text(
                    """
                    UPDATE chunks
                    SET tsv = to_tsvector('english', coalesce(content, ''))
                    WHERE document_id = :doc_id
                    """
                ),
                {"doc_id": document_id},
            )
        doc.insights = build_insights(parsed)
        doc.status = "ready"
        doc.error = None
        db.commit()
    except Exception as exc:
        db.rollback()
        doc = db.get(Document, document_id)
        if doc:
            doc.status = "error"
            doc.error = str(exc)[:2000]
            db.commit()
        raise


def ensure_upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
