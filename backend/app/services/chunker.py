"""Semantic chunking for engineering standards.

Chunks by section/clause (not token windows). Tables stay intact as one
chunk. Parent-child: small paragraph chunks for retrieval, parent section
text for context expansion (small-to-big).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from app.services.parser import ParsedDocument, ParsedElement, SECTION_RE

CLAUSE_IN_TEXT = re.compile(r"\b(\d+(?:\.\d+){1,5})\b")


@dataclass
class ChunkDraft:
    id: str
    parent_id: Optional[str]
    content: str
    element_type: str
    section_number: Optional[str]
    page_number: int
    bbox: dict
    is_parent: bool
    source_orders: list[int] = field(default_factory=list)


def _current_section(el: ParsedElement, fallback: Optional[str]) -> Optional[str]:
    if el.section_number:
        return el.section_number
    first = el.content.strip().split("\n", 1)[0]
    m = SECTION_RE.match(first.strip())
    if m:
        return m.group(1)
    return fallback


def _merge_bbox(a: dict, b: dict) -> dict:
    if not a:
        return b
    if not b:
        return a
    x0 = min(a["x"], b["x"])
    y0 = min(a["y"], b["y"])
    x1 = max(a["x"] + a["w"], b["x"] + b["w"])
    y1 = max(a["y"] + a["h"], b["y"] + b["h"])
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def chunk_document(parsed: ParsedDocument) -> list[ChunkDraft]:
    """Group layout elements into parent sections + child retrieval chunks."""
    section_groups: dict[str, list[ParsedElement]] = {}
    order_keys: list[str] = []
    current = "preamble"

    for el in parsed.elements:
        sec = _current_section(el, current) or current
        if el.element_type == "header" and el.section_number:
            sec = el.section_number
        if sec not in section_groups:
            section_groups[sec] = []
            order_keys.append(sec)
        section_groups[sec].append(el)
        current = sec

    drafts: list[ChunkDraft] = []
    for sec in order_keys:
        els = section_groups[sec]
        parent_id = str(uuid4())
        parent_text_parts: list[str] = []
        parent_bbox: dict = {}
        parent_page = els[0].page_number if els else 1

        for el in els:
            parent_text_parts.append(el.content)
            parent_bbox = _merge_bbox(parent_bbox, el.bbox)
            parent_page = min(parent_page, el.page_number)

            child_content = el.content.strip()
            if len(child_content) < 20 and el.element_type != "table":
                continue
            drafts.append(
                ChunkDraft(
                    id=str(uuid4()),
                    parent_id=parent_id,
                    content=_decorate(child_content, sec, parsed, el),
                    element_type=el.element_type,
                    section_number=sec if sec != "preamble" else None,
                    page_number=el.page_number,
                    bbox=el.bbox,
                    is_parent=False,
                    source_orders=[el.reading_order],
                )
            )

        parent_body = "\n\n".join(parent_text_parts).strip()
        if parent_body:
            drafts.append(
                ChunkDraft(
                    id=parent_id,
                    parent_id=None,
                    content=_decorate(parent_body, sec, parsed, None),
                    element_type="section",
                    section_number=sec if sec != "preamble" else None,
                    page_number=parent_page,
                    bbox=parent_bbox or {"x": 0, "y": 0, "w": 1, "h": 0.2},
                    is_parent=True,
                )
            )

    return drafts


def _decorate(content: str, section: str, parsed: ParsedDocument, el: Optional[ParsedElement]) -> str:
    header_bits = []
    if parsed.standard_code:
        header_bits.append(parsed.standard_code)
    if parsed.title:
        header_bits.append(parsed.title)
    if section and section != "preamble":
        header_bits.append(f"§{section}")
    if el and el.element_type == "table":
        header_bits.append("TABLE")
    prefix = " | ".join(header_bits)
    return f"[{prefix}]\n{content}" if prefix else content
