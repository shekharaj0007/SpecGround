import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { api } from "../api";
import type { HighlightTarget } from "../types";
import { useEffect, useState } from "react";

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export function PdfPane({
  target,
  onClose,
}: {
  target: HighlightTarget | null;
  onClose: () => void;
}) {
  const [numPages, setNumPages] = useState(1);
  const [width, setWidth] = useState(520);

  useEffect(() => {
    const onResize = () => setWidth(Math.min(560, Math.max(360, window.innerWidth * 0.38)));
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  if (!target) {
    return (
      <aside className="pdf-pane">
        <div className="panel-h">
          <h2>Source viewer</h2>
        </div>
        <div className="empty">
          <h3>Click a citation</h3>
          <p>The matching paragraph is highlighted on the page — the demo moment that makes this look production, not tutorial.</p>
        </div>
      </aside>
    );
  }

  const { bbox } = target;

  return (
    <aside className="pdf-pane">
      <div className="panel-h">
        <h2>Source viewer</h2>
        <div className="pdf-toolbar">
          <span>
            p.{target.page} / {numPages}
          </span>
          <button className="btn ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
      <div className="pdf-scroll">
        <Document
          file={api.pdfUrl(target.documentId)}
          onLoadSuccess={(info) => setNumPages(info.numPages)}
        >
          <div className="page-wrap">
            <Page pageNumber={target.page} width={width} renderTextLayer renderAnnotationLayer />
            <div
              className="hl"
              style={{
                left: `${bbox.x * 100}%`,
                top: `${bbox.y * 100}%`,
                width: `${bbox.w * 100}%`,
                height: `${bbox.h * 100}%`,
              }}
            />
          </div>
        </Document>
      </div>
      <div className="snippet">{target.snippet}</div>
    </aside>
  );
}
