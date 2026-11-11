import { useEffect, useState } from "react";
import { api } from "../api";
import { NotesPanel } from "../components/NotesPanel";
import type { ClauseCompare, Document } from "../types";

export function ComparePage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");
  const [result, setResult] = useState<ClauseCompare | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listDocuments()
      .then((list) => {
        setDocs(list);
        const ready = list.filter((doc) => doc.status === "ready");
        setLeftId((prev) => prev || ready[0]?.id || list[0]?.id || "");
        setRightId((prev) => prev || ready[1]?.id || list[1]?.id || "");
      })
      .catch((e) => setError(String(e.message || e)));
  }, []);

  async function run() {
    if (!leftId || !rightId || leftId === rightId) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.compareClauses(leftId, rightId));
    } catch (e: unknown) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Compare failed");
    } finally {
      setBusy(false);
    }
  }

  const leftTitle = docs.find((doc) => doc.id === leftId)?.title || result?.left_title || "Left";
  const rightTitle = docs.find((doc) => doc.id === rightId)?.title || result?.right_title || "Right";

  return (
    <div className="eval-page">
      <div className="panel-h" style={{ border: "1px solid var(--line)", marginBottom: 16 }}>
        <div>
          <h2>Document compare</h2>
          <p className="doc-meta" style={{ margin: "6px 0 0" }}>
            Shared clause numbers whose text differs, and clauses that exist on only one side. Sample documents are
            fictional.
          </p>
        </div>
        <button className="btn primary" type="button" disabled={busy || !leftId || !rightId || leftId === rightId} onClick={run}>
          {busy ? "Comparing…" : "Compare clauses"}
        </button>
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="compare-picks">
        <label className="stack">
          <span className="section-label">Left</span>
          <select className="field" value={leftId} onChange={(e) => setLeftId(e.target.value)}>
            <option value="">Choose a document</option>
            {docs.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.title || doc.filename}
              </option>
            ))}
          </select>
        </label>
        <label className="stack">
          <span className="section-label">Right</span>
          <select className="field" value={rightId} onChange={(e) => setRightId(e.target.value)}>
            <option value="">Choose a document</option>
            {docs.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.title || doc.filename}
              </option>
            ))}
          </select>
        </label>
      </div>
      {!docs.length && <p className="doc-meta">Load samples from Workspace, then pick two documents.</p>}

      {result && (
        <>
          <div className="eval-grid">
            <div className="metric">
              <div className="n">{result.changed.length}</div>
              <div className="l">Changed</div>
            </div>
            <div className="metric">
              <div className="n">{result.only_left.length}</div>
              <div className="l">Only left</div>
            </div>
            <div className="metric">
              <div className="n">{result.only_right.length}</div>
              <div className="l">Only right</div>
            </div>
            <div className="metric">
              <div className="n">{result.changed.length + result.only_left.length + result.only_right.length}</div>
              <div className="l">Differences</div>
            </div>
          </div>

          <h2 className="section-label">Changed clauses</h2>
          {result.changed.map((clause) => (
            <article className="case" key={clause.clause_number}>
              <h3>§{clause.clause_number}</h3>
              <span className="pill warn">changed</span>
              <div className="compare-grid">
                <div>
                  <div className="doc-meta">
                    {result.left_title}
                    {clause.left_page ? ` · p.${clause.left_page}` : ""}
                  </div>
                  <p style={{ color: "var(--text)", whiteSpace: "pre-wrap" }}>{clause.left_text || "—"}</p>
                </div>
                <div>
                  <div className="doc-meta">
                    {result.right_title}
                    {clause.right_page ? ` · p.${clause.right_page}` : ""}
                  </div>
                  <p className="gold" style={{ whiteSpace: "pre-wrap" }}>{clause.right_text || "—"}</p>
                </div>
              </div>
            </article>
          ))}
          {!result.changed.length && <p className="doc-meta">No shared clause number has different text.</p>}

          <h2 className="section-label" style={{ marginTop: 18 }}>
            Only in {result.left_title}
          </h2>
          {result.only_left.map((clause) => (
            <article className="case" key={`L-${clause.clause_number}`}>
              <h3>§{clause.clause_number}</h3>
              <span className="pill">only left</span>
              <p style={{ color: "var(--text)", whiteSpace: "pre-wrap" }}>{clause.text}</p>
            </article>
          ))}
          {!result.only_left.length && <p className="doc-meta">Every numbered clause on the left also exists on the right.</p>}

          <h2 className="section-label" style={{ marginTop: 18 }}>
            Only in {result.right_title}
          </h2>
          {result.only_right.map((clause) => (
            <article className="case" key={`R-${clause.clause_number}`}>
              <h3>§{clause.clause_number}</h3>
              <span className="pill">only right</span>
              <p style={{ color: "var(--text)", whiteSpace: "pre-wrap" }}>{clause.text}</p>
            </article>
          ))}
          {!result.only_right.length && <p className="doc-meta">Every numbered clause on the right also exists on the left.</p>}
        </>
      )}

      {(leftId || rightId) && (
        <div className="compare-grid" style={{ marginTop: 22 }}>
          {leftId && <NotesPanel documentId={leftId} label={`Notes · ${leftTitle}`} />}
          {rightId && rightId !== leftId && <NotesPanel documentId={rightId} label={`Notes · ${rightTitle}`} />}
        </div>
      )}
    </div>
  );
}
