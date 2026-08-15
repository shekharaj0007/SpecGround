from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Conversation, Document, Message
from app.schemas import (
    ChatRequest,
    ChatResponse,
    CompareRequest,
    CompareResponse,
    ConversationOut,
    DocumentOut,
    MessageOut,
)
from app.services.conflicts import find_conflicts
from app.services.generation import generate_answer
from app.services.query_router import route_query
from app.services.retrieval import retrieve

router = APIRouter(prefix="/api", tags=["chat"])


def _ready_ids(db: Session, requested: list[str]) -> list[str]:
    if requested:
        found = db.query(Document.id).filter(Document.id.in_(requested), Document.status == "ready").all()
        return [r[0] for r in found]
    return [d.id for d in db.query(Document).filter(Document.status == "ready").all()]


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

    doc_ids = _ready_ids(db, req.document_ids)
    history = [(m.role, m.content) for m in (convo.messages or [])][-8:]
    docs = db.query(Document).filter(Document.id.in_(doc_ids)).all() if doc_ids else []
    insights = [(d.id, d.title or d.filename, d.insights or {}) for d in docs]

    try:
        routed = route_query(req.question, len(doc_ids), has_history=bool(history))
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

    db.add(Message(conversation_id=convo.id, role="user", content=req.question, query_type=routed.query_type))
    db.add(
        Message(
            conversation_id=convo.id,
            role="assistant",
            content=result.answer,
            citations=[c.model_dump() for c in result.citations],
            confidence=result.confidence,
            grounded=result.grounded,
            query_type=result.query_type,
        )
    )
    db.commit()
    return result


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
