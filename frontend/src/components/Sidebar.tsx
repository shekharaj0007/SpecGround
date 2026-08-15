import { useRef } from "react";
import type { Document, HighlightTarget } from "../types";

export function Sidebar({
  docs,
  selected,
  onToggle,
  onUpload,
  onSeed,
  onDelete,
  onCompare,
  onJump,
  seeding,
  comparing,
}: {
  docs: Document[];
  selected: Set<string>;
  onToggle: (id: string) => void;
  onUpload: (file: File) => void;
  onSeed: () => void;
  onDelete: (id: string) => void;
  onCompare: () => void;
  onJump: (t: HighlightTarget) => void;
  seeding: boolean;
  comparing: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const selectedDocs = docs.filter((d) => selected.has(d.id) && d.status === "ready");
  const specs = selectedDocs.flatMap((d) =>
    (d.insights?.specs ?? []).map((s) => ({ ...s, doc: d.title || d.filename }))
  );
  const risks = selectedDocs.flatMap((d) =>
    (d.insights?.risks ?? []).map((r) => ({ ...r, doc: d.title || d.filename }))
  );
  const outline = selectedDocs.length === 1 ? selectedDocs[0].insights?.outline ?? [] : [];

  return (
    <aside className="sidebar">
      <div className="panel-h">
        <h2>Library</h2>
        <button className="btn primary" onClick={onSeed} disabled={seeding}>
          {seeding ? "Seeding…" : "Load samples"}
        </button>
      </div>
      <div className="sidebar-body">
        <label className="upload">
          Drop or click to upload PDFs
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            multiple
            onChange={(e) => {
              Array.from(e.target.files ?? []).forEach(onUpload);
              e.target.value = "";
            }}
          />
        </label>
        <button
          className="btn"
          style={{ width: "100%", marginBottom: 10 }}
          disabled={selected.size < 2 || comparing}
          onClick={onCompare}
        >
          {comparing ? "Comparing…" : `Compare ${selected.size} selected`}
        </button>
        <p className="doc-meta" style={{ marginBottom: 10 }}>
          Checked docs are in retrieval context.
        </p>
        <div className="doc-list">
          {docs.map((d) => (
            <label key={d.id} className={`doc-card ${selected.has(d.id) ? "active" : ""}`}>
              <input
                type="checkbox"
                checked={selected.has(d.id)}
                disabled={d.status !== "ready"}
                onChange={() => onToggle(d.id)}
              />
              <div>
                <h3>{d.title || d.filename}</h3>
                <div className="doc-meta">
                  {d.standard_code || d.doc_type} · {d.page_count || "—"} pp
                  {d.insights?.specs?.length ? ` · ${d.insights.specs.length} specs` : ""}
                </div>
                <span
                  className={`pill ${d.status === "ready" ? "ok" : d.status === "error" ? "err" : "warn"}`}
                >
                  {d.status}
                </span>
                {d.error && <div className="doc-meta">{d.error}</div>}
              </div>
              <button className="btn ghost danger" type="button" onClick={() => onDelete(d.id)}>
                ×
              </button>
            </label>
          ))}
        </div>

        {!!specs.length && (
          <div className="spec-block">
            <h2>Extracted specs</h2>
            {specs.map((s, i) => (
              <div className="spec-row" key={i}>
                <span className="spec-k">{s.name}</span>
                <span className="spec-v">{s.display}</span>
              </div>
            ))}
          </div>
        )}

        {!!risks.length && (
          <div className="spec-block">
            <h2>Risk flags</h2>
            {risks.map((r, i) => (
              <div className={`risk ${r.severity}`} key={i}>
                <strong>{r.name}</strong>
                <div className="doc-meta">{r.detail}</div>
              </div>
            ))}
          </div>
        )}

        {!!outline.length && (
          <div className="spec-block">
            <h2>Clause outline</h2>
            {outline.map((o) => (
              <button
                key={o.section + o.page}
                className="outline-btn"
                type="button"
                onClick={() =>
                  onJump({
                    documentId: selectedDocs[0].id,
                    page: o.page,
                    bbox: o.bbox,
                    snippet: o.title,
                  })
                }
              >
                §{o.section} · p.{o.page}
              </button>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
