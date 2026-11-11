"""Plain-text bibliography for the last grounded answer."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import LastCitationExport


def format_bibliography(citations: list[dict] | None) -> str:
    if not citations:
        return "No citations for the last answer."
    lines = ["SpecGround bibliography", ""]
    for index, cite in enumerate(citations, start=1):
        name = cite.get("document_name") or "document"
        page = cite.get("page")
        section = cite.get("section")
        loc = f"{name}, p. {page}"
        if section:
            loc += f", §{section}"
        lines.append(f"[{index}] {loc}.")
        chunk_id = cite.get("chunk_id") or ""
        if chunk_id:
            lines.append(f"    chunk: {chunk_id}")
        snippet = " ".join(str(cite.get("snippet") or "").split())
        if snippet:
            lines.append(f"    {snippet}")
    return "\n".join(lines)


def store_last_citations(db: Session, message_id: str, citations: list[dict]) -> None:
    row = db.get(LastCitationExport, "last")
    if row is None:
        row = LastCitationExport(id="last")
        db.add(row)
    row.message_id = message_id
    row.citations = citations
    row.bibliography = format_bibliography(citations)
