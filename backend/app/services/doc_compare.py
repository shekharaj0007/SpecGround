"""Clause-level diff of two documents.

Shared clause numbers whose text differs are returned as changes.
Clause numbers present on only one side are returned separately.
Identical shared clauses are omitted.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from sqlalchemy.orm import Session

from app.models import Chunk, Document

_CLAUSE_NUM = re.compile(r"\d+(?:\.\d+)*")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _body(content: str) -> str:
    text = content or ""
    if text.startswith("["):
        text = text.split("\n", 1)[1] if "\n" in text else text
    return _norm(text)


def _sort_key(number: str) -> tuple:
    parts: list[Any] = []
    for part in number.split("."):
        parts.append(int(part) if part.isdigit() else part)
    return tuple(parts)


def _clause_number(value: str | None) -> str:
    raw = (value or "").strip()
    return raw if _CLAUSE_NUM.fullmatch(raw) else ""


def index_clauses(chunks: Iterable[Any]) -> dict[str, dict[str, Any]]:
    """Group chunks by clause number. Child text wins over the parent section."""
    grouped: dict[str, list[Any]] = {}
    for chunk in chunks:
        number = _clause_number(getattr(chunk, "section_number", None))
        if not number:
            continue
        grouped.setdefault(number, []).append(chunk)

    indexed: dict[str, dict[str, Any]] = {}
    for number, items in grouped.items():
        children = [chunk for chunk in items if not getattr(chunk, "is_parent", False)]
        use = children or items
        use.sort(key=lambda chunk: (getattr(chunk, "page_number", 1) or 1, 1 if getattr(chunk, "is_parent", False) else 0))
        parts = [_body(getattr(chunk, "content", "") or "") for chunk in use]
        text = _norm("\n".join(part for part in parts if part))
        page = getattr(use[0], "page_number", None) if use else None
        indexed[number] = {"text": text, "page": page}
    return indexed


def _as_entry(number: str, value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"clause_number": number, "text": _norm(value), "page": None}
    if isinstance(value, Mapping):
        return {
            "clause_number": number,
            "text": _norm(str(value.get("text") or "")),
            "page": value.get("page"),
        }
    return {"clause_number": number, "text": _norm(str(value)), "page": None}


def _side_map(side: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for key, value in side.items():
        number = _clause_number(str(key)) or str(key).strip()
        if not number:
            continue
        entry = _as_entry(number, value)
        entry["clause_number"] = number
        mapped[number] = entry
    return mapped


def compare_clause_maps(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Diff two clause maps.

    Values may be plain text or ``{"text", "page"}`` entries.
    """
    left_map = _side_map(left)
    right_map = _side_map(right)

    changed: list[dict[str, Any]] = []
    for number in sorted(set(left_map) & set(right_map), key=_sort_key):
        if left_map[number]["text"] == right_map[number]["text"]:
            continue
        changed.append(
            {
                "clause_number": number,
                "left_text": left_map[number]["text"],
                "right_text": right_map[number]["text"],
                "left_page": left_map[number]["page"],
                "right_page": right_map[number]["page"],
            }
        )
    only_left = [left_map[number] for number in sorted(set(left_map) - set(right_map), key=_sort_key)]
    only_right = [right_map[number] for number in sorted(set(right_map) - set(left_map), key=_sort_key)]
    return {"changed": changed, "only_left": only_left, "only_right": only_right}


def compare_documents(left_chunks: Iterable[Any], right_chunks: Iterable[Any]) -> dict[str, list[dict[str, Any]]]:
    """Compare clause text from two in-memory or ORM chunk lists."""
    return compare_clause_maps(index_clauses(left_chunks), index_clauses(right_chunks))


def compare_stored_documents(db: Session, left_id: str, right_id: str) -> dict[str, Any]:
    if not left_id or not right_id or left_id == right_id:
        raise ValueError("Choose two different documents")
    left = db.get(Document, left_id)
    right = db.get(Document, right_id)
    if not left or not right:
        missing = left_id if not left else right_id
        raise LookupError(missing)
    left_chunks = db.query(Chunk).filter(Chunk.document_id == left_id).all()
    right_chunks = db.query(Chunk).filter(Chunk.document_id == right_id).all()
    diff = compare_documents(left_chunks, right_chunks)
    return {
        "left_id": left.id,
        "right_id": right.id,
        "left_title": left.title or left.filename,
        "right_title": right.title or right.filename,
        **diff,
    }
