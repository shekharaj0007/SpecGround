import { useMemo, useRef, useState } from "react";
import { AnswerBody, QueryBadge } from "./AnswerBody";
import type { ChatMessage, Citation } from "../types";

const SUGGESTIONS = [
  "What is the allowable stress for A106 Grade B at 500 °F?",
  "Compare CP-450 casing MAWP with the Category D minimum design pressure.",
  "What is NPSHr of the CP-450 at 450 gpm?",
  "State the wall thickness formula in §4.1.1.",
  "Convert that allowable stress to MPa.",
];

export function ChatPane({
  messages,
  busy,
  error,
  onSend,
  onCite,
  selectedCount,
}: {
  messages: ChatMessage[];
  busy: boolean;
  error: string | null;
  onSend: (q: string) => void;
  onCite: (c: Citation) => void;
  selectedCount: number;
}) {
  const [text, setText] = useState("");
  const logRef = useRef<HTMLDivElement>(null);

  const canSend = text.trim().length > 0 && !busy;

  const placeholder = useMemo(
    () =>
      selectedCount
        ? `Ask across ${selectedCount} selected document${selectedCount > 1 ? "s" : ""}…`
        : "Ask a spec question — clause numbers, tables, units…",
    [selectedCount]
  );

  function submit() {
    if (!canSend) return;
    onSend(text.trim());
    setText("");
    setTimeout(() => logRef.current?.scrollTo({ top: 9e6, behavior: "smooth" }), 50);
  }

  return (
    <section className="chat-pane">
      <div className="panel-h">
        <h2>Grounded chat</h2>
        <span className="doc-meta">{selectedCount || "all"} in context</span>
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="chat-log" ref={logRef}>
        {messages.length === 0 && (
          <div className="empty">
            <h3>Ask the standards, not the model</h3>
            <p>
              Answers are retrieved with hybrid search, cited to page + bbox, then checked for
              faithfulness. If it is not in the PDF, SpecGround says so.
            </p>
            <p>
              Try: <code>{SUGGESTIONS[0]}</code>
            </p>
          </div>
        )}
        {messages.map((m) => (
          <article
            key={m.id}
            className={`msg ${m.role} ${m.role === "assistant" && m.grounded === false ? "ungrounded" : ""}`}
          >
            {m.role === "user" ? (
              <div className="bubble">{m.content}</div>
            ) : (
              <div className="bubble">
                <div className="meta-row">
                  <QueryBadge type={m.query_type} />
                  {m.grounded === false ? (
                    <span className="badge err">Not grounded</span>
                  ) : (
                    <span className="badge ok">Grounded</span>
                  )}
                  {typeof m.confidence === "number" && (
                    <span className="badge">conf {Math.round(m.confidence * 100)}%</span>
                  )}
                </div>
                <AnswerBody text={m.content} citations={m.citations ?? []} onCite={onCite} />
                {!!m.conversions?.length && (
                  <div className="conv-row">
                    {m.conversions.map((c) => (
                      <span key={c} className="badge">
                        {c}
                      </span>
                    ))}
                  </div>
                )}
                {!!m.conflicts?.length && (
                  <div className="conflict">
                    Cross-doc disagreement:{" "}
                    {m.conflicts.map((c) => c.name).join(", ")}
                  </div>
                )}
                {!!m.citations?.length && (
                  <div className="cite-row">
                    {m.citations.map((c, i) => (
                      <button key={c.chunk_id + i} className="cite" type="button" onClick={() => onCite(c)}>
                        [{i + 1}] {c.document_name.slice(0, 28)} p.{c.page}
                        {c.section ? ` §${c.section}` : ""}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </article>
        ))}
        {busy && <div className="badge">Retrieving · reranking · checking faithfulness…</div>}
      </div>
      <div className="hint">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            className="btn ghost"
            style={{ marginRight: 6, marginBottom: 6 }}
            disabled={busy}
            onClick={() => onSend(s)}
          >
            {s.length > 48 ? s.slice(0, 48) + "…" : s}
          </button>
        ))}
      </div>
      <div className="composer">
        <textarea
          value={text}
          placeholder={placeholder}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <button className="btn primary" disabled={!canSend} onClick={submit}>
          {busy ? "…" : "Ask"}
        </button>
      </div>
    </section>
  );
}
