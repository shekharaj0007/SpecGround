import type { ChatResponse, CompareResult, Document, EvalRun } from "./types";

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data.detail || data.message || res.statusText;
  } catch {
    return res.statusText;
  }
}

export const api = {
  async health() {
    const res = await fetch("/api/health");
    return res.json() as Promise<{ ok: boolean; openai_configured: boolean }>;
  },

  async listDocuments() {
    const res = await fetch("/api/documents");
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<Document[]>;
  },

  async upload(file: File) {
    const body = new FormData();
    body.append("file", file);
    const res = await fetch("/api/documents", { method: "POST", body });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<Document>;
  },

  async seed() {
    const res = await fetch("/api/documents/seed", { method: "POST" });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<Document[]>;
  },

  async remove(id: string) {
    const res = await fetch(`/api/documents/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(await parseError(res));
  },

  pdfUrl(id: string) {
    return `/api/documents/${id}/file`;
  },

  async chat(question: string, documentIds: string[], conversationId?: string) {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        document_ids: documentIds,
        conversation_id: conversationId,
      }),
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<ChatResponse>;
  },

  async listEval() {
    const res = await fetch("/api/eval");
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<EvalRun[]>;
  },

  async runEval() {
    const res = await fetch("/api/eval/run", { method: "POST" });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<EvalRun>;
  },

  async compare(documentIds: string[]) {
    const res = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_ids: documentIds }),
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<CompareResult>;
  },
};
