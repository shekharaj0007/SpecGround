"""Query router for engineering Q&A.

Classifies: spec lookup vs comparison vs explanation vs unit conversion.
Clause numbers like 304.1.2 are extracted for keyword boosting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas import QueryType

CLAUSE_RE = re.compile(r"\b(?:§\s*)?(\d+(?:\.\d+){1,5})\b")
COMPARE_RE = re.compile(r"\b(compare|versus|vs\.?|difference|differ|across|between|both)\b", re.I)
UNIT_RE = re.compile(
    r"\b(convert|in\s+(?:psi|ksi|mpa|bar|kpa|celsius|fahrenheit|mm|inch|gpm|scfm)|"
    r"to\s+(?:si|metric|imperial)|unit)\b",
    re.I,
)
SPEC_RE = re.compile(
    r"\b(allowable|mawp|thickness|stress|pressure|temperature|nps|schedule|"
    r"clause|section|what is|minimum|maximum|required|per\s+§)\b",
    re.I,
)
FOLLOW_RE = re.compile(
    r"^(what about|and that|convert (that|it|those)|same for|how about|in si|in metric|in imperial)\b",
    re.I,
)


@dataclass
class RoutedQuery:
    query_type: QueryType
    clauses: list[str] = field(default_factory=list)
    dense_k: int = 20
    keyword_k: int = 20
    final_k: int = 6
    expand_parent: bool = True
    per_document: bool = False
    expanded_query: str = ""


def route_query(question: str, document_count: int, has_history: bool = False) -> RoutedQuery:
    clauses = CLAUSE_RE.findall(question)
    if has_history and (FOLLOW_RE.search(question.strip()) or len(question.split()) <= 4):
        return RoutedQuery(
            query_type="follow_up",
            clauses=clauses,
            dense_k=15,
            keyword_k=15,
            final_k=5,
            expand_parent=True,
        )
    if COMPARE_RE.search(question) or document_count >= 2 and "compare" in question.lower():
        return RoutedQuery(
            query_type="comparison",
            clauses=clauses,
            dense_k=12,
            keyword_k=12,
            final_k=8,
            expand_parent=True,
            per_document=True,
        )
    if UNIT_RE.search(question):
        return RoutedQuery(
            query_type="unit_conversion",
            clauses=clauses,
            dense_k=15,
            keyword_k=15,
            final_k=5,
            expand_parent=True,
        )
    if clauses or SPEC_RE.search(question):
        return RoutedQuery(
            query_type="spec_lookup",
            clauses=clauses,
            dense_k=20,
            keyword_k=25,
            final_k=5,
            expand_parent=True,
        )
    return RoutedQuery(
        query_type="explanation",
        clauses=clauses,
        dense_k=20,
        keyword_k=15,
        final_k=6,
        expand_parent=True,
    )
