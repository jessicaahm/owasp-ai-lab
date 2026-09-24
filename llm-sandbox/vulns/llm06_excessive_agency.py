"""LLM06 - VULNERABLE: the agent is granted far more capability than the task needs.

Task: "summarise a file in scratch/docs". Weakness: the model is handed read,
write, delete and list tools, path arguments are joined without confinement,
and tool calls execute automatically with no logging or confirmation.
Everything is limited to scratch/ by the sandbox layout, but nothing in the
*code* enforces that.
"""
import json
import os

from ollama_client import chat
from vulns.common import SCRATCH

# BUG: capability far exceeds the task (a summariser needs read only).
TOOLS = {
    "list_dir": lambda path=".": os.listdir(os.path.join(SCRATCH, path)),
    "read_file": lambda path: open(os.path.join(SCRATCH, path)).read(),
    "write_file": lambda path, content: open(os.path.join(SCRATCH, path), "w").write(content),
    "delete_file": lambda path: os.remove(os.path.join(SCRATCH, path)),
}

SYSTEM = (
    "You are a file assistant. Available tools: list_dir(path), read_file(path), "
    "write_file(path, content), delete_file(path). To call a tool reply with JSON "
    '{"tool": name, "args": {...}}. When finished reply with {"final": text}.'
)


def run() -> None:
    task = input("Task (e.g. 'summarise docs/welcome.md')> ")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    for _ in range(6):
        raw = chat(messages)
        messages.append({"role": "assistant", "content": raw})
        try:
            call = json.loads(raw.strip().strip("`").removeprefix("json").strip())
        except json.JSONDecodeError:
            print("Assistant:", raw)
            return
        if "final" in call:
            print("Assistant:", call["final"])
            return
        # BUG: no allowlist, no path confinement, no confirmation, no audit log.
        result = TOOLS[call["tool"]](**call.get("args", {}))
        messages.append({"role": "user", "content": f"tool result: {result}"})
    print("Stopped after too many steps.")
