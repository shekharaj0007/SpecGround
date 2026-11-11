"""Clause watch: flag a clause when a newer upload changes its text."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models import Chunk, ClauseWatch, Document

_CLAUSE_NUM = re.compile(r"\d+(?:\.\d+)*")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _body(content: str) -> str:
    text = content or ""
    if text.startswith("["):
        text = text.split("\n", 1)[1] if "\n" in text else text
    return _norm(text)


def _clause_number(clause_key: str) -> str:
    raw = (clause_key or "").strip()
    raw = re.sub(r"^(?:§|section|clause)\s*", "", raw, flags=re.I).strip()
    match = _CLAUSE_NUM.fullmatch(raw)
    return match.group(0) if match else ""


def _heading(clause_key: str, heading: str | None) -> str:
    head = (heading or "").strip()
    if head:
        return head
    if not _clause_number(clause_key):
        return (clause_key or "").strip()
    return ""


def _matches(chunk: Chunk, number: str, heading: str) -> bool:
    if number:
        return (chunk.section_number or "").strip() == number
    if heading:
        return heading.lower() in (chunk.content or "").lower()
    return False


def clause_text(db: Session, document_id: str, clause_key: str, heading: str | None) -> str | None:
    number = _clause_number(clause_key)
    head = _heading(clause_key, heading)
    if not number and not head:
        return None
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
    matched = [chunk for chunk in chunks if _matches(chunk, number, head)]
    children = [chunk for chunk in matched if not chunk.is_parent]
    use = children or matched
    if not use:
        return None
    use.sort(key=lambda chunk: (chunk.page_number, 1 if chunk.is_parent else 0))
    return _norm("\n".join(_body(chunk.content) for chunk in use if _body(chunk.content)))


def evaluate_watch(db: Session, watch: ClauseWatch) -> None:
    docs = db.query(Document).filter(Document.status == "ready").all()
    docs.sort(key=lambda doc: ((doc.created_at.isoformat() if doc.created_at else ""), doc.id))
    baseline = ""
    baseline_id: str | None = None
    changed = False
    latest_text: str | None = None
    latest_id: str | None = None
    for doc in docs:
        text = clause_text(db, doc.id, watch.clause_key, watch.heading)
        if not text:
            continue
        if not baseline:
            baseline = text
            baseline_id = doc.id
            continue
        if text != baseline:
            changed = True
            latest_text = text
            latest_id = doc.id
    watch.baseline_text = baseline
    watch.baseline_document_id = baseline_id
    watch.changed = changed
    watch.latest_text = latest_text
    watch.latest_document_id = latest_id


def refresh_all_watches(db: Session) -> None:
    for watch in db.query(ClauseWatch).all():
        evaluate_watch(db, watch)
