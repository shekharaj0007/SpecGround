from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Document, EvalRun
from app.services.generation import generate_answer
from app.services.query_router import route_query
from app.services.retrieval import retrieve

DATASET_PATH = Path(__file__).with_name("dataset.json")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _token_overlap(expected: str, answer: str) -> float:
    exp = set(re.findall(r"[a-z0-9.]+", expected.lower()))
    got = set(re.findall(r"[a-z0-9.]+", answer.lower()))
    if not exp:
        return 0.0
    return len(exp & got) / len(exp)


def run_evaluation(db: Session) -> EvalRun:
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    ready_ids = [d.id for d in db.query(Document).filter(Document.status == "ready").all()]
    results = []
    faith_scores = []
    rel_scores = []
    prec_scores = []

    for case in cases:
        question = case["question"]
        expected = case["expected"]
        must = [m.lower() for m in case.get("must_include", [])]
        routed = route_query(question, len(ready_ids))
        chunks = retrieve(db, question, routed, ready_ids) if ready_ids else []
        response = generate_answer(question, chunks, routed, conversation_id="eval")
        answer_l = _normalize(response.answer)

        if any(m == "not found" for m in must):
            must_hit = ("not found" in answer_l) or (not response.grounded) or ("800" in answer_l)
        else:
            must_hit = all(m in answer_l for m in must) if must else True

        overlap = _token_overlap(expected, response.answer)
        faithfulness = 1.0 if response.grounded else 0.35
        # Answer relevance: overlap with gold + must-include hits
        relevance = min(1.0, 0.4 * overlap + (0.6 if must_hit else 0.0) + (0.1 if response.grounded else 0.0))
        # Context precision: share of retrieved chunks whose snippet terms appear in the question or gold
        if chunks:
            hits = 0
            keys = set(re.findall(r"[a-z0-9.]+", (question + " " + expected).lower()))
            for ch in chunks:
                terms = set(re.findall(r"[a-z0-9.]+", ch.content.lower()))
                if len(keys & terms) >= 2:
                    hits += 1
            precision = hits / len(chunks)
        else:
            precision = 0.0

        passed = must_hit and (response.grounded or "not found" in must)
        results.append(
            {
                "question": question,
                "expected": expected,
                "answer": response.answer,
                "grounded": response.grounded,
                "query_type": response.query_type,
                "faithfulness": round(faithfulness, 3),
                "answer_relevance": round(relevance, 3),
                "context_precision": round(precision, 3),
                "passed": passed,
                "citations": [c.model_dump() for c in response.citations],
            }
        )
        faith_scores.append(faithfulness)
        rel_scores.append(relevance)
        prec_scores.append(precision)

    n = max(len(results), 1)
    scores = {
        "faithfulness": round(sum(faith_scores) / n, 3),
        "answer_relevance": round(sum(rel_scores) / n, 3),
        "context_precision": round(sum(prec_scores) / n, 3),
        "pass_rate": round(sum(1 for r in results if r["passed"]) / n, 3),
        "n_cases": len(results),
        "notes": (
            "Lightweight RAGAS-style metrics: faithfulness from the grounding auditor, "
            "answer relevance vs gold + must-include tokens, context precision as chunk-term overlap."
        ),
    }
    run = EvalRun(scores=scores, cases=results)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
