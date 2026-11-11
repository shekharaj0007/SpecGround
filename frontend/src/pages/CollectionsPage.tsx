import { useEffect, useState } from "react";
import { api } from "../api";
import type { ChatResponse, ClauseWatch, Collection, Document } from "../types";

export function CollectionsPage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [watches, setWatches] = useState<ClauseWatch[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [name, setName] = useState("");
  const [question, setQuestion] = useState("What is the allowable stress for A106 Grade B at 500 °F?");
  const [clauseKey, setClauseKey] = useState("4.1.1");
  const [heading, setHeading] = useState("Internal Pressure");
  const [answer, setAnswer] = useState<ChatResponse | null>(null);
  const [bibliography, setBibliography] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const selected = collections.find((c) => c.id === selectedId) ?? null;

  async function refresh() {
    const [docList, cols, watchList] = await Promise.all([
      api.listDocuments(),
      api.listCollections(),
      api.listWatches(),
    ]);
    setDocs(docList);
    setCollections(cols);
    setWatches(watchList);
    setSelectedId((prev) => prev ?? cols[0]?.id);
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e.message || e)));
  }, []);

  async function createCollection() {
    const trimmed = name.trim();
    if (!trimmed) return;
    setError(null);
    const created = await api.createCollection(trimmed);
    setName("");
    setCollections((prev) => [created, ...prev]);
    setSelectedId(created.id);
  }

  async function toggleDoc(docId: string) {
    if (!selected) return;
    const has = selected.document_ids.includes(docId);
    const documentIds = has
      ? selected.document_ids.filter((id) => id !== docId)
      : [...selected.document_ids, docId];
    const updated = await api.setCollectionDocs(selected.id, documentIds);
    setCollections((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
  }

  async function ask() {
    if (!selected || !question.trim()) return;
    setBusy(true);
    setError(null);
    setNote(null);
    setBibliography("");
    try {
      const res = await api.chat(question.trim(), [], undefined, selected.id);
      setAnswer(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Question failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveAnswer() {
    if (!answer || !selected) return;
    await api.saveQuery({
      question: question.trim(),
      answer: answer.answer,
      citation_ids: answer.citations.map((c) => c.chunk_id),
      collection_id: selected.id,
    });
    setNote("Saved this question and its citation ids.");
  }

  async function exportLast() {
    setError(null);
    try {
      const exported = await api.exportCitations();
      setBibliography(exported.bibliography);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  }

  async function addWatch() {
    if (!clauseKey.trim()) return;
    setError(null);
    const created = await api.createWatch(clauseKey.trim(), heading.trim() || undefined);
    setWatches((prev) => [created, ...prev.filter((w) => w.id !== created.id)]);
    setNote(created.changed ? `§${created.clause_key} already differs across uploads.` : `Watching ${created.clause_key}.`);
  }

  return (
    <div className="eval-page">
      <div className="panel-h" style={{ border: "1px solid var(--line)", marginBottom: 16 }}>
        <div>
          <h2>Collections</h2>
          <p className="doc-meta" style={{ margin: "6px 0 0" }}>
            Group documents and ask only inside that set. Sample standards are fictional.
          </p>
        </div>
      </div>
      {error && <div className="error-banner">{error}</div>}
      {note && <div className="notice-banner">{note}</div>}
      <div className="library-grid">
        <div>
          <div className="stack">
            <input
              className="field"
              value={name}
              placeholder="Collection name"
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") createCollection().catch((err) => setError(String(err.message || err)));
              }}
            />
            <button className="btn primary" type="button" onClick={() => createCollection().catch((e) => setError(String(e.message || e)))}>
              New collection
            </button>
          </div>
          <div className="doc-list" style={{ marginTop: 12 }}>
            {collections.map((c) => (
              <div
                key={c.id}
                className={`doc-card ${c.id === selectedId ? "active" : ""}`}
                style={{ textAlign: "left", color: "inherit", width: "100%", cursor: "pointer" }}
                onClick={() => {
                  setSelectedId(c.id);
                  setAnswer(null);
                }}
              >
                <div />
                <div>
                  <h3>{c.name}</h3>
                  <div className="doc-meta">{c.document_ids.length} documents</div>
                </div>
                <button
                  className="btn ghost danger"
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    api.removeCollection(c.id).then(() => {
                      setCollections((prev) => prev.filter((item) => item.id !== c.id));
                      if (selectedId === c.id) setSelectedId(undefined);
                    });
                  }}
                >
                  ×
                </button>
              </div>
            ))}
            {!collections.length && <p className="doc-meta">No collections yet.</p>}
          </div>
        </div>
        <div>
          {!selected && <p className="doc-meta">Create a collection, then check the documents that belong in it.</p>}
          {selected && (
            <>
              <h2 className="section-label">{selected.name}</h2>
              <div className="doc-list">
                {docs.map((d) => (
                  <label key={d.id} className={`doc-card ${selected.document_ids.includes(d.id) ? "active" : ""}`}>
                    <input
                      type="checkbox"
                      checked={selected.document_ids.includes(d.id)}
                      onChange={() => toggleDoc(d.id).catch((e) => setError(String(e.message || e)))}
                    />
                    <div>
                      <h3>{d.title || d.filename}</h3>
                      <div className="doc-meta">
                        {d.status}
                        {d.standard_code ? ` · ${d.standard_code}` : ""}
                      </div>
                    </div>
                    <span />
                  </label>
                ))}
                {!docs.length && <p className="doc-meta">Load samples from Workspace first.</p>}
              </div>
              <div className="composer" style={{ paddingLeft: 0, paddingRight: 0 }}>
                <textarea value={question} onChange={(e) => setQuestion(e.target.value)} />
                <button className="btn primary" type="button" disabled={busy || !selected.document_ids.length} onClick={ask}>
                  {busy ? "…" : "Ask"}
                </button>
              </div>
              {answer && (
                <article className="case">
                  <div className="meta-row">
                    <span className={`badge ${answer.grounded ? "ok" : "err"}`}>
                      {answer.grounded ? "Grounded" : "Not grounded"}
                    </span>
                    <span className="badge">{answer.query_type}</span>
                  </div>
                  <p style={{ whiteSpace: "pre-wrap" }}>{answer.answer}</p>
                  <div className="cite-row">
                    {answer.citations.map((c, i) => (
                      <span key={c.chunk_id + i} className="cite">
                        [{i + 1}] {c.document_name} p.{c.page}
                        {c.section ? ` §${c.section}` : ""}
                      </span>
                    ))}
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                    <button className="btn" type="button" onClick={() => saveAnswer().catch((e) => setError(String(e.message || e)))}>
                      Save query
                    </button>
                    <button className="btn" type="button" onClick={exportLast}>
                      Export citations
                    </button>
                  </div>
                </article>
              )}
              {bibliography && <pre className="pre-block">{bibliography}</pre>}
            </>
          )}
        </div>
      </div>

      <div className="panel-h" style={{ border: "1px solid var(--line)", margin: "22px 0 12px" }}>
        <div>
          <h2>Clause watch</h2>
          <p className="doc-meta" style={{ margin: "6px 0 0" }}>
            Store a clause number or heading. A newer upload with the same clause and different text is marked changed.
          </p>
        </div>
      </div>
      <div className="stack" style={{ maxWidth: 520 }}>
        <input className="field" value={clauseKey} placeholder="Clause id, e.g. 4.1.1" onChange={(e) => setClauseKey(e.target.value)} />
        <input className="field" value={heading} placeholder="Heading (optional)" onChange={(e) => setHeading(e.target.value)} />
        <button className="btn primary" type="button" onClick={() => addWatch().catch((e) => setError(String(e.message || e)))}>
          Watch clause
        </button>
      </div>
      <div style={{ marginTop: 12 }}>
        {watches.map((w) => (
          <article className="case" key={w.id}>
            <h3>
              {w.clause_key}
              {w.heading ? ` · ${w.heading}` : ""}
            </h3>
            <span className={`pill ${w.changed ? "err" : "ok"}`}>{w.status}</span>
            {w.baseline_text && <p>{w.baseline_text.slice(0, 280)}</p>}
            {w.changed && w.latest_text && (
              <p className="gold">Newer text: {w.latest_text.slice(0, 280)}</p>
            )}
            <button className="btn ghost danger" type="button" onClick={() => api.removeWatch(w.id).then(() => setWatches((prev) => prev.filter((item) => item.id !== w.id)))}>
              Remove
            </button>
          </article>
        ))}
        {!watches.length && <p className="doc-meta">No clauses on watch.</p>}
      </div>
    </div>
  );
}
