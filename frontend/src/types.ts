export type DocType = "standard" | "datasheet" | "manual" | "material_spec" | string;

export interface Document {
  id: string;
  filename: string;
  title: string;
  doc_type: DocType;
  standard_code?: string | null;
  page_count: number;
  status: "processing" | "ready" | "error" | string;
  error?: string | null;
  insights?: DocInsights | null;
}

export interface SpecPoint {
  name: string;
  value: string;
  unit: string;
  display: string;
  document_id?: string;
  document_name?: string;
}

export interface OutlineItem {
  section: string;
  title: string;
  page: number;
  bbox: BBox;
}

export interface RiskFlag {
  name: string;
  detail: string;
  severity: string;
  document_id?: string;
  document_name?: string;
}

export interface DocInsights {
  standard_code?: string | null;
  doc_type?: string;
  title?: string;
  outline?: OutlineItem[];
  specs?: SpecPoint[];
  risks?: RiskFlag[];
  tables?: { title: string; page: number; bbox: BBox }[];
  quantities?: string[];
}

export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page: number;
  section?: string | null;
  bbox: BBox;
  snippet: string;
  element_type: string;
}

export interface ChatResponse {
  conversation_id: string;
  answer: string;
  citations: Citation[];
  confidence: number;
  grounded: boolean;
  query_type: string;
  unsupported_claims: string[];
  retrieved_count: number;
  expanded_query?: string | null;
  conversions?: string[];
  conflicts?: { name: string; values: { document_name: string; display: string }[] }[];
  follow_up?: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: number;
  grounded?: boolean;
  query_type?: string;
  conversions?: string[];
  conflicts?: { name: string; values: { document_name: string; display: string }[] }[];
  expanded_query?: string | null;
}

export interface HighlightTarget {
  documentId: string;
  page: number;
  bbox: BBox;
  snippet: string;
}

export interface CompareResult {
  specs: SpecPoint[];
  conflicts: { name: string; values: { document_name: string; display: string }[] }[];
  risks: RiskFlag[];
  documents: Document[];
}

export interface EvalCase {
  question: string;
  expected: string;
  answer: string;
  grounded: boolean;
  query_type?: string;
  faithfulness: number;
  answer_relevance: number;
  context_precision: number;
  passed: boolean;
}

export interface EvalRun {
  id: string;
  scores: {
    faithfulness: number;
    answer_relevance: number;
    context_precision: number;
    pass_rate: number;
    n_cases: number;
    notes?: string;
  };
  cases: EvalCase[];
  created_at: string;
}
