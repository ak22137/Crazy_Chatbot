# Excel Intelligence — Conversational Analytics Platform

Upload Excel/CSV files and query your data with natural language. SQL-powered, deterministic answers via Mistral AI.

## Architecture

```
User → Next.js Frontend → FastAPI Backend → Intent Classifier → SQL Agent → DuckDB → Response
```

- **No embeddings for analytics** — all counting, filtering, aggregation runs through SQL
- **Auto-discovery** — schema, relationships, and semantic mappings are detected automatically
- **Self-repairing SQL** — if a generated query fails, the system fixes it (up to 3 retries)
- **Streaming responses** — SSE for real-time token streaming

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Open

Go to [http://localhost:3000](http://localhost:3000)

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 15, React 19, TypeScript |
| Backend | FastAPI, Python 3.12 |
| Database | DuckDB (embedded OLAP) |
| LLM | Mistral AI (mistral-small-latest) |
| Streaming | SSE (Server-Sent Events) |

## How It Works

1. **Upload** — Drop Excel/CSV files. They're parsed, loaded into DuckDB, exported to Parquet.
2. **Auto-detect** — Schema, types, primary keys, foreign key relationships, and semantic column mappings are discovered.
3. **Ask** — Type a question. The intent classifier routes it (SQL_ANALYTICS / METADATA / GREETING).
4. **SQL Generation** — For analytics, relevant table metadata is sent to Mistral, which generates DuckDB SQL.
5. **Validation** — SQL is parsed by sqlglot to ensure safety (SELECT only, no DDL/DML).
6. **Execute** — Query runs against DuckDB. If it fails, the error is fed back to Mistral for repair.
7. **Response** — Results are formatted into natural language and streamed back.
