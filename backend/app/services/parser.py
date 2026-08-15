"""Layout-aware PDF parser.

Extracts text blocks, tables, and bounding boxes with page numbers.
PyMuPDF is the default (self-hosted, no extra system deps). Tables are
kept as structured JSON rather than flattened strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

import fitz

ElementType = Literal["header", "text", "table", "figure"]

SECTION_RE = re.compile(
    r"^(?:§\s*|Section\s+|Clause\s+|Article\s+)?"
    r"(\d+(?:\.\d+){0,6})"
    r"(?:\s+[—–-]\s*|\s+)([A-Z][^\n]{2,90})$"
)


@dataclass
class ParsedElement:
    element_type: ElementType
    content: str
    page_number: int
    bbox: dict[str, float]
    table_json: Optional[dict[str, Any]] = None
    section_number: Optional[str] = None
    reading_order: int = 0


@dataclass
class ParsedDocument:
    title: str
    page_count: int
    page_sizes: list[dict[str, float]] = field(default_factory=list)
    elements: list[ParsedElement] = field(default_factory=list)
    standard_code: Optional[str] = None
    doc_type: str = "standard"


def _norm_bbox(bbox: tuple[float, float, float, float], width: float, height: float) -> dict[str, float]:
    x0, y0, x1, y1 = bbox
    w = max(width, 1.0)
    h = max(height, 1.0)
    return {
        "x": max(0.0, x0 / w),
        "y": max(0.0, y0 / h),
        "w": max(0.0, (x1 - x0) / w),
        "h": max(0.0, (y1 - y0) / h),
    }


def _table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    cleaned = [[(c or "").strip() for c in row] for row in rows]
    width = max(len(r) for r in cleaned)
    for row in cleaned:
        while len(row) < width:
            row.append("")
    header = cleaned[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in cleaned[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _guess_section(text: str) -> Optional[str]:
    first = text.strip().split("\n", 1)[0].strip()
    m = SECTION_RE.match(first)
    if m:
        return m.group(1)
    return None


def _detect_standard_code(text: str) -> Optional[str]:
    patterns = [
        r"\b(ASME\s+[A-Z]?\d+(?:\.\d+)?(?:\s*[A-Z]\d+\.\d+)?)",
        r"\b(ISO\s+\d+(?:-\d+)?)",
        r"\b(ASTM\s+[A-Z]\d+)",
        r"\b(SG-[A-Z0-9-]+)",
        r"\b(MS-[A-Z0-9-]+)",
        r"\b(CP-\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, text[:2000], re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).upper()
    return None


def _overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float], iou_thresh: float = 0.4) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return False
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max((ax1 - ax0) * (ay1 - ay0), 1.0)
    return (inter / area_a) > iou_thresh


def parse_pdf(path: str | Path) -> ParsedDocument:
    doc = fitz.open(path)
    elements: list[ParsedElement] = []
    page_sizes: list[dict[str, float]] = []
    order = 0
    first_text_parts: list[str] = []

    for page_index, page in enumerate(doc, start=1):
        width, height = page.rect.width, page.rect.height
        page_sizes.append({"width": width, "height": height, "page": page_index})
        table_rects: list[tuple[float, float, float, float]] = []

        try:
            finder = page.find_tables()
            tables = finder.tables if finder else []
        except Exception:
            tables = []

        for table in tables:
            rows = table.extract() or []
            md = _table_to_markdown(rows)
            if not md.strip():
                continue
            bbox = tuple(table.bbox)
            table_rects.append(bbox)
            header_guess = rows[0][0] if rows and rows[0] else "Table"
            content = f"Table: {header_guess}\n{md}"
            elements.append(
                ParsedElement(
                    element_type="table",
                    content=content,
                    page_number=page_index,
                    bbox=_norm_bbox(bbox, width, height),
                    table_json={"rows": rows},
                    section_number=_guess_section(content),
                    reading_order=order,
                )
            )
            order += 1

        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            btype = block.get("type", 0)
            bbox = tuple(block.get("bbox", (0, 0, 0, 0)))
            if any(_overlaps(bbox, tr) for tr in table_rects):
                continue

            if btype == 1:
                elements.append(
                    ParsedElement(
                        element_type="figure",
                        content=f"[Figure on page {page_index}]",
                        page_number=page_index,
                        bbox=_norm_bbox(bbox, width, height),
                        reading_order=order,
                    )
                )
                order += 1
                continue

            lines: list[str] = []
            max_size = 0.0
            for line in block.get("lines", []):
                span_text = "".join(span.get("text", "") for span in line.get("spans", []))
                if span_text.strip():
                    lines.append(span_text)
                for span in line.get("spans", []):
                    max_size = max(max_size, float(span.get("size", 0)))
            text = "\n".join(lines).strip()
            if not text:
                continue
            if page_index <= 2:
                first_text_parts.append(text)

            is_header = bool(SECTION_RE.match(text.split("\n", 1)[0].strip())) or max_size >= 13
            elements.append(
                ParsedElement(
                    element_type="header" if is_header else "text",
                    content=text,
                    page_number=page_index,
                    bbox=_norm_bbox(bbox, width, height),
                    section_number=_guess_section(text),
                    reading_order=order,
                )
            )
            order += 1

    preview = "\n".join(first_text_parts)
    title = Path(path).stem
    for line in preview.splitlines():
        cleaned = line.strip()
        if len(cleaned) > 8:
            title = cleaned[:180]
            break

    doc.close()
    return ParsedDocument(
        title=title,
        page_count=len(page_sizes),
        page_sizes=page_sizes,
        elements=elements,
        standard_code=_detect_standard_code(preview),
        doc_type=_guess_doc_type(preview, title),
    )


def _guess_doc_type(text: str, title: str) -> str:
    blob = f"{title}\n{text[:1500]}".lower()
    if "datasheet" in blob or "performance curve" in blob:
        return "datasheet"
    if "manual" in blob or "maintenance" in blob:
        return "manual"
    if "material" in blob and "composition" in blob:
        return "material_spec"
    return "standard"
