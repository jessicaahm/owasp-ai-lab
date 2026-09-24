"""LLM02 - VULNERABLE: model output is executed and rendered without validation.

Weakness: the model is asked to write SQL and HTML, and both are used verbatim.
The model's output is treated as trusted code, so anything that influences the
model (user text, retrieved docs) can influence what gets executed or rendered.
"""
import sqlite3

from ollama_client import chat
from vulns.common import SCRATCH

SYSTEM = (
    "You translate customer questions into a single SQLite query against the "
    "table orders(id INTEGER, customer TEXT, status TEXT). Reply with SQL only."
)


def setup_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        "CREATE TABLE orders(id INTEGER, customer TEXT, status TEXT);"
        "INSERT INTO orders VALUES (1,'ana','shipped'),(2,'ben','pending'),(3,'cy','delivered');"
    )
    return conn


def run() -> None:
    conn = setup_db()
    question = input("Question about orders> ")
    sql = chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}])
    print("\nModel produced SQL:\n", sql)

    # BUG 1: whatever the model emitted is executed as-is. No schema, no
    # allowlist, no parameters; the model decides what runs against the DB.
    rows = conn.execute(sql).fetchall()

    # BUG 2: model/user-derived text written into HTML without escaping.
    html = "<h1>Results</h1><p>Query: " + sql + "</p><ul>"
    html += "".join(f"<li>{r}</li>" for r in rows) + "</ul>"
    out = SCRATCH / "llm02_report.html"
    out.write_text(html)
    print(f"Rows: {rows}\nWrote {out}")
