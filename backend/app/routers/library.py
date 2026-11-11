"""Collections, saved queries, clause watches, and notes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ClauseWatch, Collection, CollectionDocument, Document, Note, SavedQuery
from app.schemas import (
    ClauseWatchIn,
    ClauseWatchOut,
    CollectionIn,
    CollectionMembers,
    CollectionOut,
    NoteIn,
    NoteOut,
    SavedQueryIn,
    SavedQueryOut,
)
from app.services.clauses import evaluate_watch

router = APIRouter(prefix="/api", tags=["library"])


def _iso(value) -> str:
    return value.isoformat() if value else ""


def _collection_out(db: Session, collection: Collection) -> CollectionOut:
    rows = (
        db.query(CollectionDocument.document_id)
        .filter(CollectionDocument.collection_id == collection.id)
        .all()
    )
    return CollectionOut(
        id=collection.id,
        name=collection.name,
        document_ids=[row[0] for row in rows],
        created_at=_iso(collection.created_at),
    )


def _saved_out(row: SavedQuery) -> SavedQueryOut:
    return SavedQueryOut(
        id=row.id,
        question=row.question,
        answer=row.answer,
        citation_ids=list(row.citation_ids or []),
        collection_id=row.collection_id,
        created_at=_iso(row.created_at),
    )


def _watch_out(row: ClauseWatch) -> ClauseWatchOut:
    if row.changed:
        status = "changed"
    elif row.baseline_text:
        status = "watching"
    else:
        status = "waiting"
    return ClauseWatchOut(
        id=row.id,
        clause_key=row.clause_key,
        heading=row.heading,
        baseline_text=row.baseline_text or "",
        changed=bool(row.changed),
        status=status,
        latest_text=row.latest_text,
        latest_document_id=row.latest_document_id,
        baseline_document_id=row.baseline_document_id,
        created_at=_iso(row.created_at),
    )


@router.get("/collections", response_model=list[CollectionOut])
def list_collections(db: Session = Depends(get_db)):
    rows = db.query(Collection).order_by(Collection.created_at.desc()).all()
    return [_collection_out(db, row) for row in rows]


@router.post("/collections", response_model=CollectionOut)
def create_collection(body: CollectionIn, db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Collection name is required")
    row = Collection(name=name[:256])
    db.add(row)
    db.commit()
    db.refresh(row)
    return _collection_out(db, row)


@router.get("/collections/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: str, db: Session = Depends(get_db)):
    row = db.get(Collection, collection_id)
    if not row:
        raise HTTPException(404, "Collection not found")
    return _collection_out(db, row)


@router.put("/collections/{collection_id}/documents", response_model=CollectionOut)
def set_collection_documents(collection_id: str, body: CollectionMembers, db: Session = Depends(get_db)):
    row = db.get(Collection, collection_id)
    if not row:
        raise HTTPException(404, "Collection not found")
    db.query(CollectionDocument).filter(CollectionDocument.collection_id == collection_id).delete()
    seen: set[str] = set()
    for doc_id in body.document_ids:
        if doc_id in seen or not db.get(Document, doc_id):
            continue
        seen.add(doc_id)
        db.add(CollectionDocument(collection_id=collection_id, document_id=doc_id))
    db.commit()
    db.refresh(row)
    return _collection_out(db, row)


@router.delete("/collections/{collection_id}")
def delete_collection(collection_id: str, db: Session = Depends(get_db)):
    row = db.get(Collection, collection_id)
    if not row:
        raise HTTPException(404, "Collection not found")
    db.query(CollectionDocument).filter(CollectionDocument.collection_id == collection_id).delete()
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/saved-queries", response_model=list[SavedQueryOut])
def list_saved_queries(db: Session = Depends(get_db)):
    rows = db.query(SavedQuery).order_by(SavedQuery.created_at.desc()).all()
    return [_saved_out(row) for row in rows]


@router.post("/saved-queries", response_model=SavedQueryOut)
def create_saved_query(body: SavedQueryIn, db: Session = Depends(get_db)):
    question = body.question.strip()
    answer = body.answer.strip()
    if not question or not answer:
        raise HTTPException(400, "Question and answer are required")
    if body.collection_id and not db.get(Collection, body.collection_id):
        raise HTTPException(404, "Collection not found")
    row = SavedQuery(
        question=question,
        answer=answer,
        citation_ids=list(body.citation_ids),
        collection_id=body.collection_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _saved_out(row)


@router.delete("/saved-queries/{query_id}")
def delete_saved_query(query_id: str, db: Session = Depends(get_db)):
    row = db.get(SavedQuery, query_id)
    if not row:
        raise HTTPException(404, "Saved query not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/clause-watches", response_model=list[ClauseWatchOut])
def list_clause_watches(db: Session = Depends(get_db)):
    rows = db.query(ClauseWatch).order_by(ClauseWatch.created_at.desc()).all()
    return [_watch_out(row) for row in rows]


@router.post("/clause-watches", response_model=ClauseWatchOut)
def create_clause_watch(body: ClauseWatchIn, db: Session = Depends(get_db)):
    clause_key = body.clause_key.strip()
    if not clause_key:
        raise HTTPException(400, "Clause id or heading is required")
    heading = (body.heading or "").strip() or None
    row = ClauseWatch(clause_key=clause_key[:256], heading=heading[:512] if heading else None)
    db.add(row)
    db.flush()
    evaluate_watch(db, row)
    db.commit()
    db.refresh(row)
    return _watch_out(row)


@router.delete("/clause-watches/{watch_id}")
def delete_clause_watch(watch_id: str, db: Session = Depends(get_db)):
    row = db.get(ClauseWatch, watch_id)
    if not row:
        raise HTTPException(404, "Clause watch not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


def _note_out(row: Note) -> NoteOut:
    return NoteOut(
        id=row.id,
        body=row.body,
        author=row.author,
        document_id=row.document_id,
        saved_query_id=row.saved_query_id,
        created_at=_iso(row.created_at),
    )


@router.get("/notes", response_model=list[NoteOut])
def list_notes(
    document_id: str | None = None,
    saved_query_id: str | None = None,
    db: Session = Depends(get_db),
):
    if bool(document_id) == bool(saved_query_id):
        raise HTTPException(400, "Filter by a document or a saved query")
    query = db.query(Note)
    if document_id:
        query = query.filter(Note.document_id == document_id)
    else:
        query = query.filter(Note.saved_query_id == saved_query_id)
    rows = query.order_by(Note.created_at.desc()).all()
    return [_note_out(row) for row in rows]


@router.post("/notes", response_model=NoteOut)
def create_note(body: NoteIn, db: Session = Depends(get_db)):
    text = body.body.strip()
    if not text:
        raise HTTPException(400, "Note text is required")
    if len(text) > 1000:
        raise HTTPException(400, "Note is too long")
    author = (body.author or "local").strip() or "local"
    if len(author) > 128:
        raise HTTPException(400, "Author is too long")
    document_id = (body.document_id or "").strip() or None
    saved_query_id = (body.saved_query_id or "").strip() or None
    if bool(document_id) == bool(saved_query_id):
        raise HTTPException(400, "Attach the note to a document or a saved query")
    if document_id and not db.get(Document, document_id):
        raise HTTPException(404, "Document not found")
    if saved_query_id and not db.get(SavedQuery, saved_query_id):
        raise HTTPException(404, "Saved query not found")
    row = Note(body=text, author=author, document_id=document_id, saved_query_id=saved_query_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _note_out(row)


@router.delete("/notes/{note_id}")
def delete_note(note_id: str, db: Session = Depends(get_db)):
    row = db.get(Note, note_id)
    if not row:
        raise HTTPException(404, "Note not found")
    db.delete(row)
    db.commit()
    return {"ok": True}
