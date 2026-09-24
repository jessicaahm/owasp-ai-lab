"""LLM06 - FIXED: least privilege, confined paths, audited tool calls.

Mitigations:
  1. Only the tool the task needs (read_file) is exposed, and it is read-only.
  2. Paths are resolved and confined to scratch/docs; escapes raise.
  3. Tool names and arguments are validated against a schema before dispatch.
  4. Every tool invocation is logged with its arguments and outcome.
  5. A hard step budget and a maximum read size bound the agent's behaviour.
  6. Anything mutating (if ever added) must go through `require_confirmation`.
"""
import json

from ollama_client import chat
from vulns.common import confine_to_scratch, get_logger

log = get_logger("llm06.fixed")

DOCS_ROOT = confine_to_scratch("docs")
MAX_READ_BYTES = 20_000
MAX_STEPS = 4


def read_file(path: str) -> str:
    target = confine_to_scratch(path)
    if DOCS_ROOT not in target.parents:
        raise PermissionError("only files under scratch/docs may be read")
    if target.suffix not in {".md", ".txt"}:
        raise PermissionError("only .md/.txt files may be read")
    return target.read_text()[:MAX_READ_BYTES]


TOOLS = {"read_file": (read_file, {"path"})}


def require_confirmation(action: str) -> bool:
    """Human-in-the-loop gate for any state-changing action (none exist yet)."""
    return input(f"Allow '{action}'? [y/N] ").strip().lower() == "y"


SYSTEM = (
    "You are a read-only document summariser. The only tool is read_file(path) "
    "for files under docs/. To call it reply with JSON "
    '{"tool": "read_file", "args": {"path": "docs/<name>"}}. When finished reply '
    'with {"final": text}. You cannot write, delete or list files.'
)


def dispatch(call: dict) -> str:
    name = call.get("tool")
    if name not in TOOLS:
        raise PermissionError(f"tool not permitted: {name!r}")
    fn, allowed_args = TOOLS[name]
    args = call.get("args", {})
    if set(args) != allowed_args:
        raise ValueError(f"bad arguments for {name}: {sorted(args)}")
    log.info("tool call %s(%s)", name, args)
    return fn(**args)


def run() -> None:
    task = input("Task (e.g. 'summarise docs/welcome.md')> ")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    for step in range(MAX_STEPS):
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
        try:
            result = dispatch(call)
        except (PermissionError, ValueError, FileNotFoundError) as exc:
            log.warning("tool call denied at step %d: %s", step, exc)
            result = f"error: {exc}"
        messages.append({"role": "user", "content": f"tool result: {result}"})
    log.warning("step budget exhausted")
    print("Stopped: step budget exhausted.")
