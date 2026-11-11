import { useEffect, useState } from "react";
import { api } from "../api";
import type { SavedQuery } from "../types";

export function SavedPage() {
  const [rows, setRows] = useState<SavedQuery[]>([]);
  const [bibliography, setBibliography] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listSaved().then(setRows).catch((e) => setError(String(e.message || e)));
  }, []);

  async function exportLast() {
    setError(null);
    try {
      const text = await api.exportBibliography();
      setBibliography(text);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  }

  return (
    <div className="eval-page">
      <div className="panel-h" style={{ border: "1px solid var(--line)", marginBottom: 16 }}>
        <div>
          <h2>Saved queries</h2>
          <p className="doc-meta" style={{ margin: "6px 0 0" }}>
            Questions kept with the answer text and citation ids.
          </p>
        </div>
        <button className="btn" type="button" onClick={exportLast}>
          Export last bibliography
        </button>
      </div>
      {error && <div className="error-banner">{error}</div>}
      {bibliography && <pre className="pre-block">{bibliography}</pre>}
      {rows.map((row) => (
        <article className="case" key={row.id}>
          <h3>{row.question}</h3>
          <p style={{ whiteSpace: "pre-wrap", color: "var(--text)" }}>{row.answer}</p>
          <div className="cite-row">
            {row.citation_ids.map((id) => (
              <span key={id} className="cite">
                {id.slice(0, 8)}
              </span>
            ))}
            {!row.citation_ids.length && <span className="doc-meta">No citation ids</span>}
          </div>
          <button
            className="btn ghost danger"
            type="button"
            style={{ marginTop: 8 }}
            onClick={() =>
              api.removeSaved(row.id).then(() => setRows((prev) => prev.filter((item) => item.id !== row.id)))
            }
          >
            Delete
          </button>
        </article>
      ))}
      {!rows.length && <p className="doc-meta">Nothing saved yet. Ask in the workspace and use Save on an answer.</p>}
    </div>
  );
}
