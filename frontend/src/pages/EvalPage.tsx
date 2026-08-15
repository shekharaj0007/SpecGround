import { useEffect, useState } from "react";
import { api } from "../api";
import type { EvalRun } from "../types";

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

export function EvalPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [current, setCurrent] = useState<EvalRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const list = await api.listEval();
    setRuns(list);
    if (list[0]) setCurrent(list[0]);
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e.message || e)));
  }, []);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.runEval();
      setCurrent(result);
      await refresh();
      setCurrent(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Eval failed");
    } finally {
      setBusy(false);
    }
  }

  const s = current?.scores;

  return (
    <div className="eval-page">
      <div className="panel-h" style={{ border: "1px solid var(--line)", marginBottom: 16 }}>
        <div>
          <h2>Evaluation dashboard</h2>
          <p className="doc-meta" style={{ margin: "6px 0 0" }}>
            RAGAS-style faithfulness, answer relevance, and context precision on a 20-question gold set
            built from the sample piping code, pump datasheet, and material spec.
          </p>
        </div>
        <button className="btn primary" onClick={run} disabled={busy}>
          {busy ? "Running 20 cases…" : "Run evaluation"}
        </button>
      </div>
      {error && <div className="error-banner">{error}</div>}
      {s && (
        <div className="eval-grid">
          <div className="metric">
            <div className="n">{pct(s.faithfulness)}</div>
            <div className="l">Faithfulness</div>
          </div>
          <div className="metric">
            <div className="n">{pct(s.answer_relevance)}</div>
            <div className="l">Answer relevance</div>
          </div>
          <div className="metric">
            <div className="n">{pct(s.context_precision)}</div>
            <div className="l">Context precision</div>
          </div>
          <div className="metric">
            <div className="n">{pct(s.pass_rate)}</div>
            <div className="l">Pass rate · {s.n_cases} cases</div>
          </div>
        </div>
      )}
      {current?.cases.map((c, i) => (
        <article className="case" key={i}>
          <h3>
            {c.passed ? "PASS" : "FAIL"} · {c.question}
          </h3>
          <p className="gold">Gold: {c.expected}</p>
          <p>Answer: {c.answer.slice(0, 420)}{c.answer.length > 420 ? "…" : ""}</p>
          <div className="row-scores">
            <span>faith {c.faithfulness.toFixed(2)}</span>
            <span>rel {c.answer_relevance.toFixed(2)}</span>
            <span>prec {c.context_precision.toFixed(2)}</span>
            <span>{c.grounded ? "grounded" : "ungrounded"}</span>
          </div>
        </article>
      ))}
      {!current && !busy && (
        <p className="doc-meta">Load sample documents first, then run evaluation.</p>
      )}
    </div>
  );
}
