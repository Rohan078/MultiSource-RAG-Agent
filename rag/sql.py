import re

from agent.llm import MODEL_SQL, ask
from rag.tables import connect_db

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|attach|detach|pragma|replace|create|"
    r"vacuum|grant|revoke|truncate)\b",
    re.IGNORECASE,
)
ROW_LIMIT = 10

SQL_SYSTEM = """You write SQLite queries.
Return only SQL. No markdown, no explanation.
Use SELECT or WITH only. Always include LIMIT 10 or less.
Only use the tables and columns listed by the user.
"""


def query_for_question(question, table_cards):
    if not table_cards:
        return None
    schema = "\n\n".join(card["text"] for card in table_cards)
    raw = ask(
        f"Schema:\n{schema}\n\nQuestion:\n{question}",
        system_instruction=SQL_SYSTEM,
        model=MODEL_SQL,
    )
    sql = _clean_sql(raw)
    if not sql:
        return None
    rows, error = run_sql(sql)
    if error:
        return {"sql": sql, "error": error, "rows": [], "locator": "sql:query"}
    return {
        "sql": sql,
        "error": None,
        "rows": rows,
        "locator": "sql:query",
        "title": "SQLite query",
        "source": "sql",
        "text": _format_rows(sql, rows),
    }


def run_sql(sql):
    cleaned = _clean_sql(sql)
    error = _validate_sql(cleaned)
    if error:
        return [], error
    conn = connect_db(readonly=True)
    try:
        cursor = conn.execute(cleaned)
        fetched = cursor.fetchmany(ROW_LIMIT)
        rows = [dict(row) for row in fetched]
        return rows, None
    except Exception as exc:
        return [], str(exc)
    finally:
        conn.close()


def _clean_sql(text):
    sql = (text or "").strip()
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)
    sql = sql.strip().rstrip(";")
    return sql


def _validate_sql(sql):
    if not sql:
        return "empty SQL"
    if ";" in sql:
        return "multiple statements are not allowed"
    if not re.match(r"^\s*(with|select)\b", sql, re.IGNORECASE):
        return "only SELECT/WITH queries are allowed"
    if FORBIDDEN.search(sql):
        return "write/DDL keywords are not allowed"
    return None


def _format_rows(sql, rows):
    if not rows:
        return f"SQL:\n{sql}\n\n(no rows)"
    header = ", ".join(rows[0].keys())
    lines = [f"SQL:\n{sql}", f"Columns: {header}", "Rows:"]
    for row in rows[:10]:
        lines.append(", ".join(f"{key}={value}" for key, value in row.items()))
    if len(rows) > 10:
        lines.append(f"... {len(rows)} rows total")
    return "\n".join(lines)
