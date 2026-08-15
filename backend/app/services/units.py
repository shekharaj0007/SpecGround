"""Unit-aware helpers for engineering Q&A (pint)."""

from __future__ import annotations

import re

from pint import UnitRegistry

ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)
for _def in ("ksi = 1000 * psi", "psig = psi", "psia = psi"):
    try:
        ureg.define(_def)
    except Exception:
        pass

QTY_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*(ksi|psi|psig|psia|MPa|kPa|bar|°F|°C|F|C|mm|in|inch|inches|gpm|scfm)",
    re.I,
)


def extract_quantities(text: str) -> list[str]:
    found = []
    for m in QTY_RE.finditer(text):
        found.append(f"{m.group(1)} {m.group(2)}")
    return found


def try_convert(value: float, unit: str, target: str) -> str | None:
    try:
        q = ureg.Quantity(value, unit)
        out = q.to(target)
        return f"{value} {unit} = {out.magnitude:.4g} {target}"
    except Exception:
        return None


PAIRS = {
    "psi": "MPa",
    "psig": "MPa",
    "psia": "MPa",
    "ksi": "MPa",
    "MPa": "psi",
    "kPa": "psi",
    "bar": "psi",
    "ft": "m",
    "m": "ft",
    "in": "mm",
    "inch": "mm",
    "inches": "mm",
    "mm": "in",
    "°F": "degC",
    "F": "degC",
    "°C": "degF",
    "C": "degF",
}


def dual_conversions(text: str, limit: int = 8) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in QTY_RE.finditer(text):
        raw_u = m.group(2)
        target = PAIRS.get(raw_u) or PAIRS.get(raw_u.lower())
        if not target:
            continue
        src = "degF" if raw_u in {"°F", "F"} else "degC" if raw_u in {"°C", "C"} else raw_u
        conv = try_convert(float(m.group(1)), src, target)
        if conv and conv not in seen:
            seen.add(conv)
            out.append(conv)
        if len(out) >= limit:
            break
    return out


def unit_context_note(question: str, chunks_text: str) -> str:
    qtys = extract_quantities(chunks_text)
    if not qtys:
        return ""
    lines = ["Quantities observed in sources (preserve these units in the answer):"]
    for q in qtys[:20]:
        lines.append(f"- {q}")
    q_lower = question.lower()
    if "si" in q_lower or "metric" in q_lower or "mpa" in q_lower:
        lines.append("User asked for SI/metric; convert and show both original and converted values.")
    if "imperial" in q_lower or "psi" in q_lower or "ksi" in q_lower:
        lines.append("User asked for imperial; convert and show both original and converted values.")
    return "\n".join(lines)
