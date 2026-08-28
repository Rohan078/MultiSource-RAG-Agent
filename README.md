# Multi-source RAG agent

CLI research agent that answers from local files (PDF, text, markdown), CSV/Excel/SQLite tables, and the web. Generation uses Groq; embeddings run locally.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md).

## Setup

```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

Put a Groq key in `.env`:

```
GROQ_API_KEY=gsk_your_key
```

## Run

```powershell
# index files in data/
.\venv\Scripts\python.exe -m rag.ingest

# chat
.\venv\Scripts\python.exe app.py
```

Drop `.pdf`, `.txt`, `.md`, `.csv`, `.xlsx`, or `.db` files into `data/`, then ingest again.
