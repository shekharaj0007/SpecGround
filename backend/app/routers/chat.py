from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Collection, CollectionDocument, Conversation, Document, LastCitationExport, Message
from app.schemas import (
    ChatRequest,
    ChatResponse,
    CitationExportOut,
    CompareRequest,
    CompareResponse,
    ConversationOut,
    DocumentOut,
    MessageOut,
)
from app.services.bibliography import store_last_citations
from app.services.conflicts import find_conflicts
from app.services.generation import generate_answer
from app.services.query_router import route_query
from app.services.retrieval import retrieve

router = APIRouter(prefix="/api", tags=["chat"])


def _ready_ids(db: Session, requested: list[str], collection_id: str | None = None) -> list[str]:
    scoped = requested
    if collection_id:
        collection = db.get(Collection, collection_id)
        if not collection:
            raise HTTPException(404, "Collection not found")
        members = {
            row[0]
            for row in db.query(CollectionDocument.document_id)
            .filter(CollectionDocument.collection_id == collection_id)
            .all()
        }
        scoped = [doc_id for doc_id in requested if doc_id in members] if requested else list(members)
        if not scoped:
            return []
    if scoped:
        found = db.query(Document.id).filter(Document.id.in_(scoped), Document.status == "ready").all()
        return [row[0] for row in found]
    return [doc.id for doc in db.query(Document).filter(Document.status == "ready").all()]


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    if not req.question.strip():
        raise HTTPException(400, "Question is required")

    if req.conversation_id:
        convo = db.get(Conversation, req.conversation_id)
        if not convo:
            raise HTTPException(404, "Conversation not found")
    else:
        convo = Conversation()
        db.add(convo)
        db.flush()

    doc_ids = _ready_ids(db, req.document_ids, req.collection_id)
    history = [(m.role, m.content) for m in (convo.messages or [])][-8:]
    docs = db.query(Document).filter(Document.id.in_(doc_ids)).all() if doc_ids else []
    insights = [(d.id, d.title or d.filename, d.insights or {}) for d in docs]

    try:
        routed = route_query(req.question, len(doc_ids), has_history=bool(history))
        # An empty collection must not fall through to every document.
        if req.collection_id and not doc_ids:
            chunks = []
        else:
            chunks = retrieve(db, req.question, routed, doc_ids)
        result = generate_answer(
            req.question,
            chunks,
            routed,
            convo.id,
            history=history,
            doc_insights=insights,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    citation_payload = [c.model_dump() for c in result.citations]
    assistant_id = str(uuid4())
    db.add(Message(conversation_id=convo.id, role="user", content=req.question, query_type=routed.query_type))
    db.add(
        Message(
            id=assistant_id,
            conversation_id=convo.id,
            role="assistant",
            content=result.answer,
            citations=citation_payload,
            confidence=result.confidence,
            grounded=result.grounded,
            query_type=result.query_type,
        )
    )
    store_last_citations(db, assistant_id, citation_payload)
    db.commit()
    return result


@router.get("/citations/export", response_model=None)
def export_citations(
    export_format: str = Query("json", alias="format"),
    db: Session = Depends(get_db),
):
    """Last answer's citations as JSON, including a plain-text bibliography.

    `?format=text` returns the bibliography alone.
    """
    row = db.get(LastCitationExport, "last")
    citations = list(row.citations or []) if row else []
    bibliography = row.bibliography if row and row.bibliography else "No citations for the last answer."
    if export_format == "text":
        return PlainTextResponse(bibliography)
    return CitationExportOut(
        citations=citations,
        bibliography=bibliography,
        message_id=row.message_id if row else None,
    )


@router.post("/compare", response_model=CompareResponse)
def compare_docs(req: CompareRequest, db: Session = Depends(get_db)):
    ids = _ready_ids(db, req.document_ids)
    docs = db.query(Document).filter(Document.id.in_(ids)).all()
    if len(docs) < 2:
        raise HTTPException(400, "Select at least two ready documents to compare")
    triples = [(d.id, d.title or d.filename, d.insights or {}) for d in docs]
    conflicts = find_conflicts(triples)
    specs = []
    risks = []
    for d in docs:
        ins = d.insights or {}
        for s in ins.get("specs") or []:
            specs.append({**s, "document_id": d.id, "document_name": d.title or d.filename})
        for r in ins.get("risks") or []:
            risks.append({**r, "document_id": d.id, "document_name": d.title or d.filename})
    return CompareResponse(
        specs=specs,
        conflicts=conflicts,
        risks=risks,
        documents=[DocumentOut.model_validate(d) for d in docs],
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    convo = db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(404, "Conversation not found")
    return ConversationOut(
        id=convo.id,
        messages=[MessageOut.model_validate(m) for m in convo.messages],
    )
