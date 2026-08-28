import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from groq import Groq

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH, override=True)
_file_env = dotenv_values(ENV_PATH)

MODEL = _file_env.get("GROQ_MODEL") or "openai/gpt-oss-20b"
MODEL_SQL = _file_env.get("GROQ_SQL_MODEL") or "openai/gpt-oss-20b"
MODEL_COMPOUND = _file_env.get("GROQ_COMPOUND_MODEL") or "groq/compound"

_client = None
_client_key = None


def _api_key():
    load_dotenv(ENV_PATH, override=True)
    key = (os.getenv("GROQ_API_KEY") or "").strip().strip('"').strip("'")
    return "".join(ch for ch in key if ch.isprintable())


def get_client():
    global _client, _client_key
    key = _api_key()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to .env from https://console.groq.com/keys"
        )
    if _client is None or _client_key != key:
        _client = Groq(api_key=key)
        _client_key = key
    return _client


def require_api_key():
    if not _api_key():
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to .env from https://console.groq.com/keys"
        )


def chat(messages, model=None, **kwargs):
    require_api_key()
    return get_client().chat.completions.create(
        model=model or MODEL,
        messages=messages,
        **kwargs,
    )


def ask(prompt, system_instruction=None, model=None):
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    response = chat(messages, model=model)
    return response.choices[0].message.content or ""


def message_text(response):
    return response.choices[0].message.content or ""


def extract_sources(response):
    sources = []
    seen = set()
    message = response.choices[0].message
    tools = getattr(message, "executed_tools", None) or []
    for tool in tools:
        for title, url in _tool_links(tool):
            if not url or url in seen:
                continue
            seen.add(url)
            sources.append({"title": title or url, "url": url, "source": "web"})
    return sources


def extract_queries(response):
    queries = []
    message = response.choices[0].message
    tools = getattr(message, "executed_tools", None) or []
    for tool in tools:
        arguments = getattr(tool, "arguments", None)
        if isinstance(arguments, dict):
            query = arguments.get("query")
            if query:
                queries.append(query)
                continue
        if isinstance(arguments, str) and "query" in arguments:
            try:
                import json

                parsed = json.loads(arguments)
                query = parsed.get("query")
                if query:
                    queries.append(query)
            except json.JSONDecodeError:
                continue
    return queries


def _tool_links(tool):
    links = []
    search_results = getattr(tool, "search_results", None)
    results = []
    if isinstance(search_results, dict):
        results = search_results.get("results") or []
    elif search_results is not None:
        results = getattr(search_results, "results", None) or []
    for item in results:
        if isinstance(item, dict):
            title = item.get("title") or item.get("url")
            url = item.get("url")
        else:
            title = getattr(item, "title", None) or getattr(item, "url", None)
            url = getattr(item, "url", None)
        if url:
            links.append((title, url))
    return links
