"""Engineering synonym expansion — critical for standards Q&A.

'MAWP' must also match 'maximum allowable working pressure'.
"""

from __future__ import annotations

import re

SYNONYMS: dict[str, list[str]] = {
    "mawp": ["maximum allowable working pressure", "casing mawp", "allowable working pressure"],
    "npshr": ["net positive suction head required", "npshe required"],
    "npsha": ["net positive suction head available"],
    "nps": ["nominal pipe size", "nominal diameter"],
    "od": ["outside diameter", "outer diameter"],
    "id": ["inside diameter", "inner diameter"],
    "tdh": ["total dynamic head", "total head"],
    "bep": ["best efficiency point"],
    "smys": ["specified minimum yield strength", "yield strength"],
    "pwht": ["postweld heat treatment", "post-weld heat treatment"],
    "allowable stress": ["basic allowable stress", "design stress", "s value"],
    "design pressure": ["p design", "minimum design pressure"],
    "wall thickness": ["required thickness", "minimum wall", "t min"],
    "schedule": ["pipe schedule", "sch"],
    "category d": ["category d fluid service"],
    "seamless": ["smls"],
    "gpm": ["gallons per minute", "m3/h", "m³/h"],
    "ksi": ["kips per square inch", "1000 psi"],
}

_WORD = re.compile(r"[a-z0-9.]+", re.I)


def expand_query(question: str) -> str:
    q = question.strip()
    low = q.lower()
    extras: list[str] = []
    for key, alts in SYNONYMS.items():
        if key in low or any(a in low for a in alts):
            extras.extend([key, *alts])
    # unique, keep short
    seen = set()
    add: list[str] = []
    for term in extras:
        t = term.lower()
        if t not in seen and t not in low:
            seen.add(t)
            add.append(term)
    if not add:
        return q
    return q + " " + " ".join(add[:12])
