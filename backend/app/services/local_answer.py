"""Extractive answers when no model API key is configured.

Quotes retrieved chunks and refuses when the question is not supported.
"""

from __future__ import annotations

import re

from app.schemas import BBox, ChatResponse, Citation
from app.services.query_router import RoutedQuery
from app.services.retrieval import RetrievedChunk
from app.services.units import dual_conversions

_WORD = re.compile(r"[a-z0-9.]+")
_STOP = {
    "a",
    "an",
    "the",
    "of",
    "for",
    "to",
    "in",
    "on",
    "at",
    "is",
    "are",
    "was",
    "what",
    "how",
    "with",
    "and",
    "or",
    "by",
    "from",
    "that",
    "this",
    "be",
    "does",
    "do",
    "it",
    "its",
    "as",
    "per",
    "into",
    "about",
    "which",
    "when",
    "where",
    "who",
    "whom",
    "than",
    "then",
    "not",
}
_COMMON_LONG = {
    "allowable",
    "pressure",
    "temperature",
    "minimum",
    "maximum",
    "required",
    "internal",
    "external",
    "thickness",
    "corrosion",
    "material",
    "materials",
    "category",
    "seamless",
    "document",
    "documents",
    "selected",
    "compare",
    "difference",
    "between",
    "working",
    "design",
    "straight",
    "formula",
    "conversion",
    "convert",
    "stresses",
    "strength",
    "tensile",
    "performance",
    "datasheet",
    "standard",
    "piping",
    "process",
    "carbon",
    "schedule",
    "nominal",
    "diameter",
    "outside",
    "quality",
    "factor",
    "reduction",
    "coefficient",
    "mechanical",
    "allowances",
    "permitted",
    "information",
    "excerpt",
    "training",
    "fictional",
    "centrifugal",
    "connections",
}


def not_found_response(
    conversation_id: str,
    routed: RoutedQuery,
    detail: str,
    retrieved_count: int = 0,
) -> ChatResponse:
    return ChatResponse(
        conversation_id=conversation_id,
        answer=f"Not found in document. {detail}",
        citations=[],
        confidence=0.0,
        grounded=False,
        query_type=routed.query_type,
        retrieved_count=retrieved_count,
        expanded_query=routed.expanded_query or None,
    )


def _terms(question: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for token in _WORD.findall(question.lower()):
        if token in _STOP or len(token) <= 1 or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _term_weight(term: str) -> int:
    return 3 if any(ch.isdigit() for ch in term) else 1


def _excerpt(content: str, terms: list[str], limit: int = 520) -> str:
    lines = [ln.strip() for ln in (content or "").splitlines() if ln.strip()]
    if not lines:
        return (content or "")[:limit].strip()

    def score(line: str) -> int:
        low = line.lower()
        return sum(_term_weight(term) for term in terms if term in low)

    best = max(range(len(lines)), key=lambda index: score(lines[index]))
    chosen: list[str] = []
    for index in range(max(0, best - 3), best):
        line = lines[index]
        if line.startswith("|") or line.lower().startswith("table") or line.startswith("["):
            chosen.append(line)
    chosen.extend(lines[best : best + 3])
    ordered: list[str] = []
    seen: set[str] = set()
    for line in chosen:
        if line not in seen:
            seen.add(line)
            ordered.append(line)
    return "\n".join(ordered)[:limit].strip()


def _citation(chunk: RetrievedChunk) -> Citation:
    bbox = chunk.bbox or {}
    return Citation(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        document_name=chunk.document_name,
        page=chunk.page_number,
        section=chunk.section_number,
        bbox=BBox(
            x=float(bbox.get("x", 0)),
            y=float(bbox.get("y", 0)),
            w=float(bbox.get("w", 1)),
            h=float(bbox.get("h", 0.05)),
        ),
        snippet=(chunk.content or "")[:280],
        element_type=chunk.element_type,
    )


def answer_from_chunks(
    question: str,
    chunks: list[RetrievedChunk],
    routed: RoutedQuery,
    conversation_id: str,
) -> ChatResponse:
    if not chunks:
        return not_found_response(
            conversation_id,
            routed,
            "No relevant sections were retrieved from the selected documents.",
        )

    terms = _terms(question)
    question_l = question.lower()
    sections = {(c.section_number or "") for c in chunks}
    blob_all = "\n".join((c.content or "").lower() for c in chunks)
    if routed.clauses and not any(
        clause in sections or clause.lower() in blob_all for clause in routed.clauses
    ):
        return not_found_response(
            conversation_id,
            routed,
            "That clause number is not in the selected documents.",
            retrieved_count=len(chunks),
        )

    scored: list[tuple[int, float, RetrievedChunk]] = []
    for chunk in chunks:
        text = (chunk.content or "").lower()
        section = (chunk.section_number or "").lower()
        overlap = sum(_term_weight(term) for term in terms if term in text or term == section)
        if section and section in question_l:
            overlap += 3
        scored.append((overlap, chunk.score, chunk))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

    picked = [chunk for overlap, _, chunk in scored if overlap > 0][:3]
    if routed.clauses:
        clause_chunks = [
            chunk
            for chunk in chunks
            if (chunk.section_number or "") in routed.clauses
            or any(clause.lower() in (chunk.content or "").lower() for clause in routed.clauses)
        ]
        if clause_chunks:
            # Keep clause hits first, then other overlapping chunks.
            seen: set[str] = set()
            ordered: list[RetrievedChunk] = []
            for chunk in clause_chunks + picked:
                if chunk.id not in seen:
                    seen.add(chunk.id)
                    ordered.append(chunk)
            picked = ordered[:3]

    if not picked:
        return not_found_response(
            conversation_id,
            routed,
            "The selected documents do not contain a supported answer to this question.",
            retrieved_count=len(chunks),
        )

    picked_blob = "\n".join((chunk.content or "").lower() for chunk in picked)
    rare = [term for term in terms if len(term) >= 8 and term not in _COMMON_LONG]
    if rare and not any(term in picked_blob or term in blob_all for term in rare):
        return not_found_response(
            conversation_id,
            routed,
            "The selected documents do not contain a supported answer to this question.",
            retrieved_count=len(chunks),
        )

    parts = []
    citations: list[Citation] = []
    for index, chunk in enumerate(picked, start=1):
        parts.append(f"{_excerpt(chunk.content, terms)} [{index}]")
        citations.append(_citation(chunk))
    answer = "\n\n".join(parts)
    try:
        conversions = dual_conversions(answer)
    except Exception:
        conversions = []
    best = scored[0][0] if scored else 1
    confidence = min(0.8, 0.4 + 0.08 * best)
    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer,
        citations=citations,
        confidence=round(confidence, 2),
        grounded=True,
        query_type=routed.query_type,
        retrieved_count=len(chunks),
        expanded_query=routed.expanded_query or None,
        conversions=conversions,
    )
