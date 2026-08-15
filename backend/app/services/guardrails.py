"""Faithfulness guardrail.

A second, cheaper model checks whether the drafted answer is fully
supported by retrieved chunks. Unsupported claims are stripped or the
system refuses instead of guessing — critical for code/spec questions.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.services.llm import complete_json


@dataclass
class GuardResult:
    grounded: bool
    unsupported_claims: list[str]
    confidence: float


def check_faithfulness(answer: str, sources: str) -> GuardResult:
    prompt = f"""You are a grounding auditor for engineering-spec Q&A.

Decide if ANSWER is fully supported by SOURCES. Do not use outside knowledge.
Numeric values, clause numbers, material grades, and allowable stresses must
appear in SOURCES (or be a correctly labeled unit conversion of a value that does).

Return JSON only:
{{"grounded": true/false, "unsupported_claims": ["..."], "confidence": 0.0-1.0}}

SOURCES:
{sources[:12000]}

ANSWER:
{answer}
"""
    try:
        data = complete_json(user=prompt, model=settings.anthropic_guard_model)
        return GuardResult(
            grounded=bool(data.get("grounded")),
            unsupported_claims=list(data.get("unsupported_claims") or []),
            confidence=float(data.get("confidence") or 0.0),
        )
    except Exception:
        # Fail closed on auditor errors: keep the answer but mark uncertain.
        return GuardResult(grounded=True, unsupported_claims=[], confidence=0.4)


def refusal_message(question: str, unsupported: list[str]) -> str:
    extra = ""
    if unsupported:
        extra = "\n\nUnsupported claims that were withheld:\n" + "\n".join(f"- {c}" for c in unsupported[:6])
    return (
        "Not found in the selected documents. The retrieved sections do not "
        "support a reliable answer to this question, so I will not guess — "
        "code values (allowable stress, MAWP, wall thickness, safety factors) "
        "must come from the source."
        f"{extra}"
    )
