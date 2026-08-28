from agent.llm import (
    MODEL,
    MODEL_COMPOUND,
    chat,
    extract_queries,
    extract_sources,
    message_text,
)
from rag.retrieve import search_docs, search_tables
from rag.sql import query_for_question

SYSTEM_INSTRUCTION = """You are a multi-source research assistant.

You receive local document excerpts, table/SQL results, and optional web notes.

Rules:
- Prefer local documents and SQL results when they answer the question.
- Use web notes only for current or missing facts.
- Only state facts supported by the provided evidence.
- If sources disagree, say so and name them.
- If you cannot verify something, say what is unknown.
- Keep the answer concise and cite sources.
"""

MAX_EVIDENCE_CHARS = 3500
MAX_CHUNK_CHARS = 700
MAX_HISTORY_TURNS = 4
WEB_HINTS = (
    "latest",
    "today",
    "current",
    "news",
    "who is",
    "what happened",
    "this week",
    "this year",
)


def clip(text, limit):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def format_evidence(doc_hits, table_hits, sql_result, web_notes=""):
    blocks = []
    if doc_hits:
        blocks.append("Local documents:")
        for index, hit in enumerate(doc_hits, start=1):
            blocks.append(
                f"[{index}] {hit['locator']}\n{clip(hit['text'], MAX_CHUNK_CHARS)}"
            )
    else:
        blocks.append("Local documents: none retrieved.")

    if table_hits:
        blocks.append("Relevant tables:")
        for hit in table_hits[:2]:
            blocks.append(clip(hit["text"], 500))

    if sql_result:
        if sql_result.get("error"):
            blocks.append(f"SQL query failed ({sql_result['error']}).")
        else:
            blocks.append("SQL result:\n" + clip(sql_result["text"], 800))

    if web_notes:
        blocks.append("Web notes:\n" + clip(web_notes, 900))

    packed = "\n\n".join(blocks)
    return clip(packed, MAX_EVIDENCE_CHARS)


def sources_from_hits(hits, kind):
    sources = []
    seen = set()
    for hit in hits:
        key = hit["locator"]
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "title": hit["title"],
                "url": hit["locator"],
                "source": kind,
            }
        )
    return sources


def needs_web(question, doc_hits):
    lowered = question.lower()
    if any(hint in lowered for hint in WEB_HINTS):
        return True
    if not doc_hits:
        return True
    return doc_hits[0]["score"] < 0.45


class ResearchAgent:
    def __init__(self):
        self._history = []

    def _messages(self, prompt):
        messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
        for question, answer in self._history[-MAX_HISTORY_TURNS:]:
            messages.append({"role": "user", "content": question})
            messages.append({"role": "assistant", "content": clip(answer, 400)})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _web_lookup(self, question):
        response = chat(
            [{"role": "user", "content": question}],
            model=MODEL_COMPOUND,
            compound_custom={"tools": {"enabled_tools": ["web_search"]}},
        )
        return {
            "text": message_text(response),
            "sources": extract_sources(response),
            "queries": extract_queries(response),
        }

    def ask(self, question):
        doc_hits = search_docs(question, k=3, sources={"doc"})
        table_hits = [
            hit for hit in search_tables(question, k=2) if hit["score"] >= 0.5
        ]
        sql_result = None
        if table_hits:
            sql_result = query_for_question(question, table_hits)

        web = {"text": "", "sources": [], "queries": []}
        if needs_web(question, doc_hits) and not table_hits:
            web = self._web_lookup(question)

        prompt = (
            f"{format_evidence(doc_hits, table_hits, sql_result, web['text'])}\n\n"
            f"Question: {question}"
        )
        response = chat(self._messages(prompt), model=MODEL)
        text = message_text(response)
        self._history.append((question, text))

        sources = sources_from_hits(doc_hits, "doc")
        sources.extend(sources_from_hits(table_hits, "table"))
        if sql_result and not sql_result.get("error"):
            sources.append(
                {
                    "title": "SQLite query",
                    "url": sql_result.get("sql", "sql:query"),
                    "source": "sql",
                }
            )
        sources.extend(web["sources"])
        return {
            "text": text,
            "sources": sources,
            "queries": web["queries"],
        }


def research(question):
    return ResearchAgent().ask(question)
