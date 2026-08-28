# Architecture

This project is a **multi-source RAG agent**: retrieve evidence from local documents, structured tables, and the web, then generate an answer with citations.

Embeddings are local (`fastembed` / `BAAI/bge-small-en-v1.5`). Generation is Groq (`openai/gpt-oss-20b` for answers and SQL, `groq/compound` for web search).

## System diagram

```mermaid
flowchart TD
    user[User question] --> cli[app.py]
    cli --> agent[ResearchAgent]
    agent --> docs[search_docs]
    agent --> tables[search_tables]
    tables -->|score >= 0.5| sql[query_for_question]
    docs --> fuse[Evidence packer]
    tables --> fuse
    sql --> fuse
    agent -->|weak local match or current-events| web[groq/compound web_search]
    web --> fuse
    fuse --> llm[Groq gpt-oss-20b]
    llm --> out[Answer + citations]
```

## Ingest vs ask

Ingest is offline. Ask is online. The model never reads a whole PDF or spreadsheet at question time.

```mermaid
flowchart LR
    subgraph ingest [Ingest: python -m rag.ingest]
        data[data/ files] --> load[loaders / tables]
        load --> chunk[chunk_text]
        chunk --> embed[local embeddings]
        embed --> index[store/index.json]
        load --> db[store/data.db]
    end

    subgraph ask [Ask: app.py]
        q[Question] --> retrieve[vector search]
        index --> retrieve
        retrieve --> sql2[read-only SQL]
        db --> sql2
        retrieve --> prompt[capped evidence]
        sql2 --> prompt
        prompt --> groq[Groq]
    end
```

## Sources

| Source | Files | Retrieve | Cite |
| --- | --- | --- | --- |
| Documents | `.txt` `.md` `.pdf` | Chunk + cosine search | file / page |
| Tables | `.csv` `.xlsx` | Schema cards in the index, then SQLite `SELECT` | table name + SQL |
| SQLite | `.db` `.sqlite` | Same as tables | table name + SQL |
| Web | live | Groq Compound `web_search` when local evidence is weak or the question looks current | URL |

Unlabeled or missing sources are not treated as “false”. If docs do not answer, the agent can search the web or say unknown.

## Repository layout

```
app.py                 CLI
agent/
  llm.py               Groq client, models, citation helpers
  research.py          Orchestrator: retrieve, SQL, web, generate
rag/
  ingest.py            Build index + SQLite warehouse
  loaders.py           PDF / text loaders
  chunk.py             Paragraph packing
  embeddings.py        Local embedding model
  store.py             index.json + cosine similarity
  tables.py            CSV / Excel / SQLite import
  sql.py               Read-only SELECT generation and execution
  retrieve.py          search_docs / search_tables
tools/                 Thin wrappers over rag retrieve/SQL
data/                  User corpus (sample notes, CSV, SQLite)
store/                 Generated; gitignored
```

## Ask-time flow

1. Embed the question and retrieve top document chunks.
2. Retrieve table schema cards. If similarity is high enough, Groq writes a `SELECT`/`WITH` query (no writes, no multiple statements, row cap).
3. If the question looks time-sensitive or local scores are low, call `groq/compound` with only the question (small payload).
4. Pack evidence under a character budget and send it to `openai/gpt-oss-20b`.
5. Keep the last four short Q&A turns, not previous evidence dumps.
6. Print answer plus `[doc]`, `[table]`, `[sql]`, `[web]` sources.

## Safety

- `.env` is gitignored. Only `.env.example` is committed.
- SQL allows `SELECT` / `WITH` only.
- The SQLite warehouse is opened read-only at query time.
- Prompt size is capped to stay under Groq request limits.

## Models

| Role | Default |
| --- | --- |
| Answer | `openai/gpt-oss-20b` |
| SQL writer | `openai/gpt-oss-20b` |
| Web search | `groq/compound` |
| Embeddings | `BAAI/bge-small-en-v1.5` (local) |

Override from `.env` with `GROQ_MODEL`, `GROQ_SQL_MODEL`, or `GROQ_COMPOUND_MODEL` if those models are enabled on the Groq key.
