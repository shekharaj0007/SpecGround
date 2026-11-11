import type {
  ChatResponse,
  CitationExport,
  ClauseWatch,
  Collection,
  CompareResult,
  Document,
  EvalRun,
  SavedQuery,
} from "./types";

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
    return res.json() as Promise<{
      ok: boolean;
      openai_configured: boolean;
      anthropic_configured: boolean;
      llm: string;
      embeddings: string;
      database: string;
    }>;
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

  async chat(question: string, documentIds: string[], conversationId?: string, collectionId?: string) {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        document_ids: documentIds,
        conversation_id: conversationId,
        collection_id: collectionId,
      }),
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<ChatResponse>;
  },

  async exportCitations() {
    const res = await fetch("/api/citations/export?format=json");
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<CitationExport>;
  },

  async exportBibliography() {
    const res = await fetch("/api/citations/export?format=text");
    if (!res.ok) throw new Error(await parseError(res));
    return res.text();
  },

  async listCollections() {
    const res = await fetch("/api/collections");
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<Collection[]>;
  },

  async createCollection(name: string) {
    const res = await fetch("/api/collections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<Collection>;
  },

  async setCollectionDocs(id: string, documentIds: string[]) {
    const res = await fetch(`/api/collections/${id}/documents`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_ids: documentIds }),
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<Collection>;
  },

  async removeCollection(id: string) {
    const res = await fetch(`/api/collections/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(await parseError(res));
  },

  async listSaved() {
    const res = await fetch("/api/saved-queries");
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<SavedQuery[]>;
  },

  async saveQuery(body: { question: string; answer: string; citation_ids: string[]; collection_id?: string }) {
    const res = await fetch("/api/saved-queries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<SavedQuery>;
  },

  async removeSaved(id: string) {
    const res = await fetch(`/api/saved-queries/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(await parseError(res));
  },

  async listWatches() {
    const res = await fetch("/api/clause-watches");
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<ClauseWatch[]>;
  },

  async createWatch(clauseKey: string, heading?: string) {
    const res = await fetch("/api/clause-watches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clause_key: clauseKey, heading }),
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json() as Promise<ClauseWatch>;
  },

  async removeWatch(id: string) {
    const res = await fetch(`/api/clause-watches/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(await parseError(res));
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
