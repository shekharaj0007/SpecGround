import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { ChatPane } from "./components/ChatPane";
import { PdfPane } from "./components/PdfPane";
import { Sidebar } from "./components/Sidebar";
import { CollectionsPage } from "./pages/CollectionsPage";
import { ComparePage } from "./pages/ComparePage";
import { EvalPage } from "./pages/EvalPage";
import { SavedPage } from "./pages/SavedPage";
import type { ChatMessage, Citation, Document, HighlightTarget } from "./types";

function Workspace() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [target, setTarget] = useState<HighlightTarget | null>(null);
  const [comparing, setComparing] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [bibliography, setBibliography] = useState("");

  async function refreshDocs() {
    const list = await api.listDocuments();
    setDocs(list);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.size === 0) {
        for (const d of list) if (d.status === "ready") next.add(d.id);
      }
      return next;
    });
  }

  useEffect(() => {
    refreshDocs().catch((e) => setError(String(e.message || e)));
  }, []);

  useEffect(() => {
    const pending = docs.some((d) => d.status === "processing");
    if (!pending) return;
    const t = setInterval(() => refreshDocs().catch(() => undefined), 2000);
    return () => clearInterval(t);
  }, [docs]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function onUpload(file: File) {
    setError(null);
    await api.upload(file);
    await refreshDocs();
  }

  async function onSeed() {
    setSeeding(true);
    setError(null);
    try {
      await api.seed();
      await refreshDocs();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Seed failed");
    } finally {
      setSeeding(false);
    }
  }

  async function onDelete(id: string) {
    await api.remove(id);
    setSelected((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
    if (target?.documentId === id) setTarget(null);
    await refreshDocs();
  }

  function onCite(c: Citation) {
    setTarget({
      documentId: c.document_id,
      page: c.page,
      bbox: c.bbox,
      snippet: c.snippet,
    });
  }

  async function onSend(question: string) {
    setBusy(true);
    setError(null);
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
    setMessages((m) => [...m, userMsg]);
    try {
      const ids = [...selected];
      const res = await api.chat(question, ids, conversationId);
      setConversationId(res.conversation_id);
      const assistant: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.answer,
        citations: res.citations,
        confidence: res.confidence,
        grounded: res.grounded,
        query_type: res.query_type,
        conversions: res.conversions,
        conflicts: res.conflicts,
        expanded_query: res.expanded_query,
      };
      setMessages((m) => [...m, assistant]);
      if (res.citations[0]) onCite(res.citations[0]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setBusy(false);
    }
  }

  async function onWatch(section: string, heading: string) {
    setError(null);
    try {
      const watch = await api.createWatch(section, heading);
      setNote(
        watch.changed
          ? `§${section} differs from an earlier upload. See Collections.`
          : `Watching §${section}. A newer upload with different text is marked on Collections.`
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not watch clause");
    }
  }

  async function onSave(message: ChatMessage, question: string) {
    setError(null);
    try {
      await api.saveQuery({
        question,
        answer: message.content,
        citation_ids: (message.citations ?? []).map((c) => c.chunk_id),
      });
      setSavedIds((prev) => new Set(prev).add(message.id));
      setNote("Saved query.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  async function onExport() {
    setError(null);
    try {
      const exported = await api.exportCitations();
      setBibliography(exported.bibliography);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  }

  async function onCompare() {
    setComparing(true);
    setError(null);
    try {
      const res = await api.compare([...selected]);
      const lines = [
        "### Cross-document spec matrix",
        "",
        ...res.specs.map((s) => `- **${s.name}** (${s.document_name}): ${s.display}`),
        "",
        res.conflicts.length
          ? "### Conflicts\n" +
            res.conflicts
              .map((c) => `- ${c.name}: ${c.values.map((v) => `${v.document_name} = ${v.display}`).join(" vs ")}`)
              .join("\n")
          : "No numeric conflicts on shared spec names.",
        "",
        res.risks.length
          ? "### Risk flags\n" + res.risks.map((r) => `- **${r.name}** (${r.document_name}): ${r.detail}`).join("\n")
          : "",
      ];
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: lines.join("\n"),
          grounded: true,
          query_type: "comparison",
          conflicts: res.conflicts,
          confidence: 1,
        },
      ]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Compare failed");
    } finally {
      setComparing(false);
    }
  }

  return (
    <div className={`workspace ${target ? "pdf-open" : ""}`}>
      <Sidebar
        docs={docs}
        selected={selected}
        onToggle={toggle}
        onUpload={onUpload}
        onSeed={onSeed}
        onDelete={onDelete}
        onCompare={onCompare}
        onJump={setTarget}
        onWatch={onWatch}
        seeding={seeding}
        comparing={comparing}
        note={note}
      />
      <ChatPane
        messages={messages}
        busy={busy}
        error={error}
        onSend={onSend}
        onCite={onCite}
        onSave={onSave}
        onExport={onExport}
        savedIds={savedIds}
        bibliography={bibliography}
        selectedCount={selected.size}
      />
      <PdfPane target={target} onClose={() => setTarget(null)} />
    </div>
  );
}

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="mark">§</div>
          <h1>SpecGround</h1>
          <span>Grounded Q&A for standards & datasheets</span>
        </div>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Workspace
          </NavLink>
          <NavLink to="/compare" className={({ isActive }) => (isActive ? "active" : "")}>
            Compare
          </NavLink>
          <NavLink to="/collections" className={({ isActive }) => (isActive ? "active" : "")}>
            Collections
          </NavLink>
          <NavLink to="/saved" className={({ isActive }) => (isActive ? "active" : "")}>
            Saved
          </NavLink>
          <NavLink to="/eval" className={({ isActive }) => (isActive ? "active" : "")}>
            Eval
          </NavLink>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Workspace />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/collections" element={<CollectionsPage />} />
        <Route path="/saved" element={<SavedPage />} />
        <Route path="/eval" element={<EvalPage />} />
      </Routes>
    </div>
  );
}
