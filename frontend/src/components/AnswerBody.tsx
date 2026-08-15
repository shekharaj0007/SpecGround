import type { Citation } from "../types";

const QUERY_LABEL: Record<string, string> = {
  spec_lookup: "Spec lookup",
  comparison: "Cross-doc compare",
  explanation: "Explanation",
  unit_conversion: "Unit-aware",
  follow_up: "Follow-up",
};

function renderAnswer(
  text: string,
  citations: Citation[],
  onCite: (c: Citation) => void
) {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const m = part.match(/^\[(\d+)\]$/);
    if (m) {
      const idx = Number(m[1]) - 1;
      const cite = citations[idx] ?? citations[0];
      return (
        <button key={i} className="inline-cite" onClick={() => cite && onCite(cite)} type="button">
          {part}
        </button>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export function AnswerBody({
  text,
  citations,
  onCite,
}: {
  text: string;
  citations: Citation[];
  onCite: (c: Citation) => void;
}) {
  const blocks = text.split(/\n{2,}/);
  return (
    <div className="answer">
      {blocks.map((block, i) => {
        if (block.includes("|") && block.includes("---")) {
          const rows = block
            .split("\n")
            .filter((l) => l.trim().startsWith("|"))
            .map((l) =>
              l
                .split("|")
                .slice(1, -1)
                .map((c) => c.trim())
            );
          const body = rows.filter((_, idx) => idx !== 1);
          return (
            <table key={i}>
              <thead>
                <tr>
                  {(body[0] || []).map((h, j) => (
                    <th key={j}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.slice(1).map((row, r) => (
                  <tr key={r}>
                    {row.map((c, j) => (
                      <td key={j}>{c}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          );
        }
        return <p key={i}>{renderAnswer(block, citations, onCite)}</p>;
      })}
    </div>
  );
}

export function QueryBadge({ type }: { type?: string }) {
  if (!type) return null;
  return <span className="badge brass">{QUERY_LABEL[type] ?? type}</span>;
}
