import { useEffect, useState } from "react";
import { api } from "../api";
import type { Note } from "../types";

function stamp(iso: string) {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleString();
}

export function NotesPanel({
  documentId,
  savedQueryId,
  label = "Notes",
}: {
  documentId?: string;
  savedQueryId?: string;
  label?: string;
}) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [author, setAuthor] = useState("local");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId && !savedQueryId) return;
    api
      .listNotes({ documentId, savedQueryId })
      .then(setNotes)
      .catch((e) => setError(String(e.message || e)));
  }, [documentId, savedQueryId]);

  async function add() {
    const text = body.trim();
    if (!text) return;
    setError(null);
    const created = await api.createNote({
      body: text,
      author: author.trim() || "local",
      document_id: documentId,
      saved_query_id: savedQueryId,
    });
    setNotes((prev) => [created, ...prev.filter((note) => note.id !== created.id)]);
    setBody("");
  }

  return (
    <div className="notes">
      <h2 className="section-label">{label}</h2>
      {error && <div className="error-banner">{error}</div>}
      <div className="stack">
        <input className="field" value={author} placeholder="Author" onChange={(e) => setAuthor(e.target.value)} />
        <textarea
          className="note-box"
          value={body}
          placeholder="Short note"
          onChange={(e) => setBody(e.target.value)}
        />
        <button className="btn" type="button" onClick={() => add().catch((e) => setError(String(e.message || e)))}>
          Add note
        </button>
      </div>
      <div style={{ marginTop: 10 }}>
        {notes.map((note) => (
          <article className="case" key={note.id}>
            <div className="doc-meta">
              {note.author} · {stamp(note.created_at)}
            </div>
            <p style={{ color: "var(--text)", whiteSpace: "pre-wrap" }}>{note.body}</p>
            <button
              className="btn ghost danger"
              type="button"
              onClick={() =>
                api.removeNote(note.id).then(() => setNotes((prev) => prev.filter((item) => item.id !== note.id)))
              }
            >
              Remove
            </button>
          </article>
        ))}
        {!notes.length && <p className="doc-meta">No notes yet.</p>}
      </div>
    </div>
  );
}
