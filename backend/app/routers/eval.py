from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.eval import run_evaluation
from app.models import EvalRun
from app.schemas import EvalRunOut

router = APIRouter(prefix="/api/eval", tags=["eval"])


def _to_out(run: EvalRun) -> EvalRunOut:
    return EvalRunOut(
        id=run.id,
        scores=run.scores,
        cases=run.cases,
        created_at=run.created_at.isoformat() if run.created_at else "",
    )


@router.get("", response_model=list[EvalRunOut])
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(EvalRun).order_by(EvalRun.created_at.desc()).limit(20).all()
    return [_to_out(r) for r in runs]


@router.get("/{run_id}", response_model=EvalRunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(EvalRun, run_id)
    if not run:
        raise HTTPException(404, "Eval run not found")
    return _to_out(run)


@router.post("/run", response_model=EvalRunOut)
def start_run(db: Session = Depends(get_db)):
    run = run_evaluation(db)
    return _to_out(run)
