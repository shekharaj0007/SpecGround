"""Hybrid retrieval: dense cosine + keyword overlap + clause match.

Works on SQLite (local) and Postgres. Results are fused with Reciprocal
Rank Fusion, then a cheap LLM rerank. Parent sections are injected for
small-to-big context.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Chunk, Document
from app.services.embeddings import embed_query
from app.services.expand import expand_query
from app.services.llm import complete_text
from app.services.query_router import RoutedQuery


@dataclass
class RetrievedChunk:
    id: str
    document_id: str
    document_name: str
    content: str
    page_number: int
    section_number: Optional[str]
    bbox: dict
    element_type: str
    score: float
    parent_content: Optional[str] = None


def _rrf(rank_lists: list[list[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranks in rank_lists:
        for i, cid in enumerate(ranks):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + i + 1)
    return scores


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = na = nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    denom = math.sqrt(na) * math.sqrt(nb)
    return dot / denom if denom else -1.0


def _children(db: Session, doc_ids: list[str]) -> list[Chunk]:
    q = db.query(Chunk).filter(Chunk.is_parent.is_(False))
    if doc_ids:
        q = q.filter(Chunk.document_id.in_(doc_ids))
    return q.all()


def _dense_search(db: Session, query_vec: list[float], doc_ids: list[str], limit: int) -> list[str]:
    scored: list[tuple[float, str]] = []
    for c in _children(db, doc_ids):
        vec = c.embedding
        if not vec:
            continue
        scored.append((_cosine(query_vec, vec), c.id))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [cid for _, cid in scored[:limit]]


def _keyword_search(db: Session, question: str, doc_ids: list[str], limit: int) -> list[str]:
    terms = [t for t in re.findall(r"[a-z0-9.]+", question.lower()) if len(t) > 1]
    if not terms:
        return []
    scored: list[tuple[float, str]] = []
    q_low = question.lower()
    for c in _children(db, doc_ids):
        text = (c.content or "").lower()
        score = float(sum(text.count(t) for t in terms))
        if c.section_number and c.section_number.lower() in q_low:
            score += 8
        if score:
            scored.append((score, c.id))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [cid for _, cid in scored[:limit]]


def _clause_search(db: Session, clauses: list[str], doc_ids: list[str], limit: int) -> list[str]:
    if not clauses:
        return []
    ids: list[str] = []
    for clause in clauses:
        q = db.query(Chunk.id).filter(Chunk.is_parent.is_(False))
        if doc_ids:
            q = q.filter(Chunk.document_id.in_(doc_ids))
        q = q.filter((Chunk.section_number == clause) | Chunk.content.ilike(f"%{clause}%")).limit(limit)
        ids.extend(r[0] for r in q.all())
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _load_chunks(db: Session, ids: list[str]) -> list[Chunk]:
    if not ids:
        return []
    chunks = db.query(Chunk).filter(Chunk.id.in_(ids)).all()
    by_id = {c.id: c for c in chunks}
    return [by_id[i] for i in ids if i in by_id]


def _llm_rerank(question: str, chunks: list[Chunk], top_n: int) -> list[Chunk]:
    if len(chunks) <= top_n:
        return chunks
    numbered = "\n\n".join(f"[{i}] {c.content[:800]}" for i, c in enumerate(chunks))
    prompt = (
        "You rerank engineering-document passages for a question. "
        "Return a JSON array of the most relevant passage indices, best first. "
        f"Pick at most {top_n}. No commentary.\n\n"
        f"Question: {question}\n\nPassages:\n{numbered}"
    )
    try:
        import json
        import re as _re

        raw = complete_text(user=prompt, model=settings.anthropic_guard_model)
        match = _re.search(r"\[[^\]]+\]", raw)
        if not match:
            return chunks[:top_n]
        indices = json.loads(match.group(0))
        picked: list[Chunk] = []
        for idx in indices:
            if isinstance(idx, int) and 0 <= idx < len(chunks):
                picked.append(chunks[idx])
        for c in chunks:
            if c not in picked:
                picked.append(c)
            if len(picked) >= top_n:
                break
        return picked[:top_n]
    except Exception:
        return chunks[:top_n]


def retrieve(
    db: Session,
    question: str,
    routed: RoutedQuery,
    document_ids: list[str],
) -> list[RetrievedChunk]:
    search_q = expand_query(question)
    routed.expanded_query = search_q
    query_vec = embed_query(search_q)
    doc_groups = [document_ids] if not routed.per_document or len(document_ids) <= 1 else [[d] for d in document_ids]

    fused_ids: list[str] = []
    rrf_scores: dict[str, float] = {}

    for group in doc_groups:
        dense = _dense_search(db, query_vec, group, routed.dense_k)
        keyword = _keyword_search(db, search_q, group, routed.keyword_k)
        clause = _clause_search(db, routed.clauses, group, 10)
        scores = _rrf([dense, keyword, clause] if clause else [dense, keyword])
        ranked = sorted(scores, key=scores.get, reverse=True)  # type: ignore[arg-type]
        for cid in ranked:
            rrf_scores[cid] = max(rrf_scores.get(cid, 0), scores[cid])
            if cid not in fused_ids:
                fused_ids.append(cid)

    fused_ids = sorted(set(fused_ids), key=lambda i: rrf_scores.get(i, 0), reverse=True)[:20]
    chunks = _load_chunks(db, fused_ids)
    reranked = _llm_rerank(question, chunks, routed.final_k)

    parent_ids = {c.parent_id for c in reranked if c.parent_id}
    parents = {p.id: p for p in _load_chunks(db, list(parent_ids))} if routed.expand_parent else {}

    docs = {
        d.id: d
        for d in db.query(Document).filter(Document.id.in_({c.document_id for c in reranked})).all()
    }

    results: list[RetrievedChunk] = []
    for c in reranked:
        parent = parents.get(c.parent_id) if c.parent_id else None
        doc = docs.get(c.document_id)
        results.append(
            RetrievedChunk(
                id=c.id,
                document_id=c.document_id,
                document_name=(doc.title or doc.filename) if doc else "document",
                content=c.content,
                page_number=c.page_number,
                section_number=c.section_number,
                bbox=c.bbox or {"x": 0, "y": 0, "w": 1, "h": 0.05},
                element_type=c.element_type,
                score=rrf_scores.get(c.id, 0.0),
                parent_content=parent.content if parent else None,
            )
        )
    return results
