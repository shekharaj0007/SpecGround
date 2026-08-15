"""Extract spec cards, clause outline, and risk flags from a parsed PDF."""

from __future__ import annotations

import re
from typing import Any

from app.services.parser import ParsedDocument, ParsedElement
from app.services.units import QTY_RE, try_convert

SPEC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("MAWP", re.compile(r"MAWP[^\n]{0,90}?(\d+(?:\.\d+)?)\s*(psig|psi|MPa|kPa)", re.I)),
    ("Design pressure (Category D min)", re.compile(r"Category D[^\n]{0,80}?(\d+(?:\.\d+)?)\s*(psi|MPa)", re.I)),
    ("Rated flow", re.compile(r"Rated[^\n]{0,40}?(\d+(?:\.\d+)?)\s*(gpm|m³/h|m3/h)", re.I)),
    ("Rated TDH", re.compile(r"(\d+(?:\.\d+)?)\s*(ft|m)\s+total dynamic head", re.I)),
    ("NPSHr (rated)", re.compile(r"NPSHr[^\n]{0,40}?(\d+(?:\.\d+)?)\s*(ft|m)", re.I)),
    ("Tensile strength min", re.compile(r"Tensile strength[^\n]{0,40}?(\d+(?:\.\d+)?)\s*(ksi|MPa)", re.I)),
    ("Yield strength min", re.compile(r"Yield strength[^\n]{0,40}?(\d+(?:\.\d+)?)\s*(ksi|MPa)", re.I)),
    ("Corrosion allowance", re.compile(r"corrosion allowance[^\n]{0,40}?(\d+(?:\.\d+)?)\s*(in|mm)", re.I)),
    ("Max fluid temperature", re.compile(r"Maximum[^\n]{0,40}temperature[^\n]{0,20}?(\d+(?:\.\d+)?)\s*(°F|°C|F)", re.I)),
    ("Carbon max (Grade B)", re.compile(r"Carbon \(C\)[^\n|]*?([0-9.]+)", re.I)),
]

RISK_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "Threaded joints restricted",
        re.compile(r"threaded joints are not permitted above (\d+(?:\.\d+)?)\s*(psi|MPa)", re.I),
        "high",
    ),
    (
        "Temperature ceiling",
        re.compile(r"not permitted above (\d+(?:\.\d+)?)\s*°?F", re.I),
        "high",
    ),
    (
        "CE / weld without PWHT",
        re.compile(r"CE shall not exceed ([0-9.]+)", re.I),
        "medium",
    ),
    (
        "Independent valve support",
        re.compile(r"Valves heavier than (\d+)\s*lb", re.I),
        "low",
    ),
]


def _si_pair(value: str, unit: str) -> list[str]:
    try:
        v = float(value)
    except ValueError:
        return [f"{value} {unit}"]
    pairs = {
        "psi": "MPa",
        "psig": "MPa",
        "ksi": "MPa",
        "MPa": "psi",
        "ft": "m",
        "m": "ft",
        "gpm": None,
        "in": "mm",
        "mm": "in",
        "°F": "°C",
        "F": "°C",
        "°C": "°F",
    }
    target = pairs.get(unit)
    out = [f"{value} {unit}"]
    if target:
        conv = try_convert(v, unit if unit != "F" else "degF", target if target != "°C" else "degC")
        if conv:
            out.append(conv.split(" = ", 1)[-1])
    return out


def build_insights(parsed: ParsedDocument) -> dict[str, Any]:
    blob = "\n".join(el.content for el in parsed.elements)
    outline: list[dict[str, Any]] = []
    seen_sec: set[str] = set()
    for el in parsed.elements:
        if el.section_number and el.section_number not in seen_sec:
            seen_sec.add(el.section_number)
            first = el.content.strip().split("\n", 1)[0][:90]
            outline.append(
                {
                    "section": el.section_number,
                    "title": first,
                    "page": el.page_number,
                    "bbox": el.bbox,
                }
            )

    specs: list[dict[str, Any]] = []
    for name, pat in SPEC_PATTERNS:
        m = pat.search(blob)
        if not m:
            continue
        val, unit = m.group(1), (m.group(2) if m.lastindex and m.lastindex >= 2 else "")
        specs.append({"name": name, "value": val, "unit": unit, "display": " ".join(_si_pair(val, unit))})

    risks: list[dict[str, str]] = []
    for name, pat, severity in RISK_PATTERNS:
        m = pat.search(blob)
        if m:
            risks.append({"name": name, "detail": m.group(0)[:180], "severity": severity})

    tables = []
    for el in parsed.elements:
        if el.element_type == "table":
            header = el.content.split("\n", 1)[0][:80]
            tables.append({"title": header, "page": el.page_number, "bbox": el.bbox})

    quantities = []
    for m in QTY_RE.finditer(blob):
        quantities.append(f"{m.group(1)} {m.group(2)}")
    # unique preserve order
    seen_q: set[str] = set()
    uniq_q = []
    for q in quantities:
        if q not in seen_q:
            seen_q.add(q)
            uniq_q.append(q)

    return {
        "standard_code": parsed.standard_code,
        "doc_type": parsed.doc_type,
        "title": parsed.title,
        "outline": outline[:40],
        "specs": specs,
        "risks": risks,
        "tables": tables[:12],
        "quantities": uniq_q[:30],
    }


def ensure_insights(db, doc) -> dict:
    if doc.insights:
        return doc.insights
    elements = [
        ParsedElement(
            element_type=el.element_type,  # type: ignore[arg-type]
            content=el.content or "",
            page_number=el.page_number,
            bbox=el.bbox or {},
            table_json=el.table_json,
            section_number=el.section_number,
            reading_order=el.reading_order,
        )
        for el in (doc.elements or [])
    ]
    parsed = ParsedDocument(
        title=doc.title or doc.filename,
        page_count=doc.page_count or 0,
        elements=elements,
        standard_code=doc.standard_code,
        doc_type=doc.doc_type or "standard",
    )
    doc.insights = build_insights(parsed)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc.insights or {}
