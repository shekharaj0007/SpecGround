from __future__ import annotations

import re

from app.config import settings
from app.schemas import BBox, ChatResponse, Citation
from app.services.guardrails import check_faithfulness, refusal_message
from app.services.llm import complete_json
from app.services.query_router import RoutedQuery
from app.services.retrieval import RetrievedChunk
from app.services.conflicts import find_conflicts
from app.services.units import dual_conversions, unit_context_note

SYSTEM = """You are SpecGround, an assistant for mechanical engineering standards, datasheets, and equipment manuals.

Rules:
- Answer ONLY from the provided source chunks. Never use outside code knowledge.
- Every factual sentence must include a citation marker like [1], [2] matching the source list.
- Preserve units exactly as written. If you convert, show original and converted values.
- Quote clause/section numbers when they appear (e.g. §4.1.1).
- For tables, cite the table chunk and state the row you used.
- If sources do not contain the answer, say so clearly. Never invent allowable stresses, MAWP, schedules, or safety factors.
- For comparisons, use a compact markdown table of differences.
- If this is a follow-up, resolve pronouns from the prior turns but still cite current sources.
- Call out numeric disagreements across documents explicitly.
- Be concise and technically precise.
"""


def _sources_block(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        loc = f"{c.document_name}, p.{c.page_number}"
        if c.section_number:
            loc += f", §{c.section_number}"
        body = c.content
        if c.parent_content and c.element_type != "section":
            body = c.content + "\n\n[Parent section]\n" + c.parent_content[:2500]
        parts.append(f"[{i}] ({loc}, type={c.element_type})\n{body}")
    return "\n\n".join(parts)


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    routed: RoutedQuery,
    conversation_id: str,
    history: list[tuple[str, str]] | None = None,
    doc_insights: list[tuple[str, str, dict]] | None = None,
) -> ChatResponse:
    if not chunks:
        return ChatResponse(
            conversation_id=conversation_id,
            answer="Not found in the selected documents. No relevant sections were retrieved.",
            citations=[],
            confidence=0.0,
            grounded=False,
            query_type=routed.query_type,
            retrieved_count=0,
        )

    sources = _sources_block(chunks)
    unit_note = unit_context_note(question, sources)
    hist = ""
    if history:
        turns = "\n".join(f"{role}: {text[:400]}" for role, text in history[-6:])
        hist = f"Prior turns:\n{turns}\n\n"
    user = (
        f"Query type: {routed.query_type}\n"
        f"{unit_note}\n\n"
        f"{hist}"
        f"Question: {question}\n\n"
        f"Sources:\n{sources}\n\n"
        "Return JSON with keys: answer (markdown string with [n] citations), "
        "citation_indices (array of ints used), confidence (0-1)."
    )

    data = complete_json(user=user, system=SYSTEM, model=settings.anthropic_chat_model)
    if "answer" not in data and data.get("raw"):
        data = {
            "answer": str(data.get("raw")),
            "citation_indices": list(range(1, min(4, len(chunks) + 1))),
            "confidence": 0.5,
        }

    answer = str(data.get("answer") or "").strip()
    indices = data.get("citation_indices") or []
    used: set[int] = set()
    for idx in indices:
        if isinstance(idx, int):
            used.add(idx)
    for m in re.finditer(r"\[(\d+)\]", answer):
        used.add(int(m.group(1)))

    citations: list[Citation] = []
    for idx in sorted(used):
        if 1 <= idx <= len(chunks):
            c = chunks[idx - 1]
            bbox = c.bbox or {}
            citations.append(
                Citation(
                    chunk_id=c.id,
                    document_id=c.document_id,
                    document_name=c.document_name,
                    page=c.page_number,
                    section=c.section_number,
                    bbox=BBox(
                        x=float(bbox.get("x", 0)),
                        y=float(bbox.get("y", 0)),
                        w=float(bbox.get("w", 1)),
                        h=float(bbox.get("h", 0.05)),
                    ),
                    snippet=c.content[:280],
                    element_type=c.element_type,
                )
            )

    guard = check_faithfulness(answer, sources)
    if not guard.grounded:
        answer = refusal_message(question, guard.unsupported_claims)
        return ChatResponse(
            conversation_id=conversation_id,
            answer=answer,
            citations=citations[:3],
            confidence=min(guard.confidence, 0.35),
            grounded=False,
            query_type=routed.query_type,
            unsupported_claims=guard.unsupported_claims,
            retrieved_count=len(chunks),
        )

    conf = float(data.get("confidence") or guard.confidence or 0.7)
    conf = min(conf, guard.confidence if guard.confidence else conf)
    conflicts = find_conflicts(doc_insights or []) if routed.query_type in {"comparison", "spec_lookup"} else []

    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer,
        citations=citations,
        confidence=round(conf, 2),
        grounded=True,
        query_type=routed.query_type,
        unsupported_claims=guard.unsupported_claims,
        retrieved_count=len(chunks),
        expanded_query=routed.expanded_query or None,
        conversions=dual_conversions(answer + "\n" + sources),
        conflicts=conflicts,
        follow_up=routed.query_type == "follow_up",
    )
