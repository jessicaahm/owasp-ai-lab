"""LLM02 - FIXED: model output is a constrained intent, never executable code.

Mitigations:
  1. The model returns structured JSON describing *what* to query, not SQL.
  2. The JSON is validated against a strict schema and an allowlist of columns.
  3. The real query is built by the application with parameters.
  4. Anything rendered into HTML is escaped.
  5. Malformed or out-of-policy model output is rejected and logged.
"""
import html
import json
import sqlite3

from ollama_client import chat
from vulns.common import SCRATCH, get_logger

log = get_logger("llm02.fixed")

ALLOWED_COLUMNS = {"id", "customer", "status"}

SYSTEM = (
    "Convert the customer's question about orders into JSON with exactly two "
    'keys: "column" (one of id, customer, status) and "value" (a string). '
    "Output only the JSON object, nothing else."
)


def setup_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        "CREATE TABLE orders(id INTEGER, customer TEXT, status TEXT);"
        "INSERT INTO orders VALUES (1,'ana','shipped'),(2,'ben','pending'),(3,'cy','delivered');"
    )
    return conn


def parse_intent(raw: str) -> dict:
    """Strict parsing: fail closed on anything unexpected."""
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    intent = json.loads(raw)
    if set(intent) != {"column", "value"}:
        raise ValueError("unexpected keys")
    if intent["column"] not in ALLOWED_COLUMNS:
        raise ValueError("column not allowed")
    if not isinstance(intent["value"], str) or len(intent["value"]) > 100:
        raise ValueError("bad value")
    return intent


def run() -> None:
    conn = setup_db()
    question = input("Question about orders> ")
    raw = chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}])
    log.info("model raw output=%r", raw[:200])
    try:
        intent = parse_intent(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        log.warning("rejected model output: %s", exc)
        print("Sorry, I couldn't understand that question.")
        return

    # Column comes from the allowlist; value is a bound parameter.
    sql = f"SELECT id, customer, status FROM orders WHERE {intent['column']} = ?"
    rows = conn.execute(sql, (intent["value"],)).fetchall()

    page = "<h1>Results</h1><p>Filter: " + html.escape(json.dumps(intent)) + "</p><ul>"
    page += "".join(f"<li>{html.escape(str(r))}</li>" for r in rows) + "</ul>"
    out = SCRATCH / "llm02_report_fixed.html"
    out.write_text(page)
    print(f"Rows: {rows}\nWrote {out}")
