"""Cross-document conflict detection for the same named spec."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def find_conflicts(docs_insights: list[tuple[str, str, dict]]) -> list[dict[str, Any]]:
    """docs_insights: (document_id, document_name, insights)."""
    by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    for doc_id, name, insights in docs_insights:
        for spec in insights.get("specs") or []:
            key = str(spec.get("name") or "").strip()
            if not key:
                continue
            by_name[key].append(
                {
                    "document_id": doc_id,
                    "document_name": name,
                    "value": str(spec.get("value") or ""),
                    "unit": str(spec.get("unit") or ""),
                    "display": str(spec.get("display") or ""),
                }
            )
    conflicts = []
    for key, rows in by_name.items():
        sigs = {(r["value"], r["unit"].lower()) for r in rows}
        if len(sigs) > 1 and len({r["document_id"] for r in rows}) > 1:
            conflicts.append({"name": key, "values": rows})
    return conflicts
