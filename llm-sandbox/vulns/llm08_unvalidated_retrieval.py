"""LLM08 - VULNERABLE: retrieved documents are trusted as if they were instructions.

Weakness: every file under scratch/docs is loaded, concatenated raw into the
system prompt, and labelled as the authoritative knowledge base. Anyone who
can add or edit a document can change the assistant's behaviour, and nothing
records which document influenced an answer.
"""
import os

from ollama_client import chat
from vulns.common import SCRATCH

DOCS = SCRATCH / "docs"


def load_knowledge_base() -> str:
    # BUG: no allowlist, no size limit, no provenance, no separation from instructions.
    parts = [open(DOCS / name).read() for name in os.listdir(DOCS)]
    return "\n\n".join(parts)


def run() -> None:
    question = input("Question> ")
    system = (
        "You are a helpful assistant. Use the following trusted knowledge base "
        "to answer and follow any guidance it contains:\n\n" + load_knowledge_base()
    )
    reply = chat([{"role": "system", "content": system}, {"role": "user", "content": question}])
    print("\nAssistant:", reply)
