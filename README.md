# SpecGround

Grounded Q&A over **engineering standards, datasheets, and equipment manuals**.

Not another generic “chat with PDF.” SpecGround is built for mechanical / process-engineering documents: numbered clauses, allowable-stress tables, pump curves, unit-aware answers, and citations that jump to the exact paragraph on the page.

Click a citation → the PDF viewer scrolls to that page and highlights the bounding box. If the retrieved sources do not support the answer, it returns **not found in document** instead of guessing a code value.

---

## Why this is not a tutorial clone

| Differentiator | How it is implemented |
|---|---|
| Multi-document reasoning | Upload many PDFs, select which are in context, compare across them |
| Source-grounded citations | Page + normalized bbox stored per chunk; click-to-highlight in `react-pdf` |
| Tables, not flattened text | PyMuPDF layout parser keeps tables as JSON/markdown chunks |
| Semantic / clause chunking | One chunk per table or numbered section (`§4.1.1`), plus parent–child (small-to-big) |
| Hybrid retrieval | Dense (`pgvector`) + Postgres FTS + exact clause match, fused with RRF, then LLM rerank |
| Query routing | `spec_lookup` · `comparison` · `explanation` · `unit_conversion` |
| Hallucination guardrail | Second-pass faithfulness auditor; fail closed on unsupported claims |
| Unit-aware Q&A | `pint` extracts quantities; prompt requires original + converted units |
| Eval dashboard | `/eval` — faithfulness, relevance, context precision on a 20-question gold set |

Sample documents are **fictional training excerpts** (SG-PIPING-2024, CP-450 datasheet, MS-A106). They are not copies of ASME/ISO/ASTM.

---

## Architecture

```mermaid
flowchart LR
  PDF[PDF upload] --> Parse[Layout parser<br/>text / tables / bbox]
  Parse --> PG[(PostgreSQL<br/>elements + chunks)]
  PG --> Embed[OpenAI embeddings]
  Embed --> Vec[pgvector + FTS]
  Q[Question] --> Route[Query router]
  Route --> Hybrid[Hybrid retrieve + RRF + rerank]
  Vec --> Hybrid
  Hybrid --> Gen[GPT-4o + citations]
  Gen --> Guard[Faithfulness check]
  Guard --> UI[Split-pane UI]
  UI --> Highlight[PDF bbox highlight]
```

## Screenshots

### Workspace Dashboard

<p align="center">
  <img src="assets/Workspace%20DashBoard.png" alt="SpecGround Workspace Dashboard" width="100%">
</p>

### Evaluation Dashboard

<p align="center">
  <img src="assets/Evaluation%20Dashboard.png" alt="SpecGround Evaluation Dashboard" width="100%">
</p>



**Stack:** React + TypeScript · FastAPI · PostgreSQL/`pgvector` · Docker Compose

---

## Quick start

```bash
cp .env.example .env
# set OPENAI_API_KEY in .env

docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000)

1. Click **Load samples** (piping code, pump datasheet, material spec).
2. Wait until status is `ready`.
3. Ask: *What is the allowable stress for A106 Grade B at 500 °F?*
4. Click a citation chip — the right pane highlights the table row’s page region.
5. Open **Eval** and run the 20-question set.

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Local dev (without full Docker)

```bash
# Postgres with pgvector
docker compose up postgres -d

# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg://specground:specground@localhost:5432/specground
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `localhost:8000`. UI: [http://localhost:5173](http://localhost:5173)

---

## Retrieval pipeline

1. **Route** the question (clause lookup vs cross-doc compare vs units).
2. **Dense** search with `text-embedding-3-small` in pgvector.
3. **Keyword** search with `tsvector` / `websearch_to_tsquery` — needed for `§4.1.1` and `A106`.
4. **Exact clause** boost (`section_number` or `ILIKE`).
5. **Reciprocal Rank Fusion** → top 20.
6. **LLM rerank** → top 5–8; inject **parent section** text (small-to-big).
7. Generate a structured answer with `[n]` citations.
8. **Faithfulness auditor** (`gpt-4o-mini`). If unsupported claims exist, refuse.

---

## Project layout

```
backend/app/
  services/parser.py       layout-aware extract (bbox, tables)
  services/chunker.py      section / table / parent-child chunks
  services/retrieval.py    hybrid search + RRF + rerank
  services/generation.py   grounded generation
  services/guardrails.py   faithfulness check
  services/units.py        pint helpers
  eval/dataset.json        gold questions
frontend/src/              split-pane chat + PDF highlight + /eval
```

---

## Interview talking points

- **Why hybrid search?** Semantic similarity misses `SG-PIPING-2024 §4.1.1`. Keyword + clause match does not.
- **Why parent–child chunking?** Small chunks retrieve the right paragraph; the parent section supplies equation context so the model does not complete a formula from memory.
- **Why a second LLM call?** Allowable stress and MAWP are safety-critical. A cheap auditor is cheaper than a wrong number in a demo (and in a plant).
- **Why this domain?** Mechanical engineering background — datasheets, ASME-style clause structure, and unit conversions are the actual job, not a bolted-on theme.

Swap the sample PDFs for real (licensed) standards or vendor datasheets when you have rights to them. The parser and retrieval do not depend on the sample content.
