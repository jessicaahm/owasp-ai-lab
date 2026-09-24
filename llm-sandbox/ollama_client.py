"""Minimal Ollama chat client. Localhost only by design (training sandbox)."""
import json
import os
import urllib.parse
import urllib.request

DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _assert_local(url: str) -> None:
    host = urllib.parse.urlparse(url).hostname
    if host not in _LOCAL_HOSTS:
        raise RuntimeError(f"Refusing non-local Ollama URL: {url} (sandbox is localhost-only)")


def chat(messages, model: str = DEFAULT_MODEL, temperature: float = 0.0) -> str:
    """Send a chat request to Ollama and return the assistant text."""
    _assert_local(OLLAMA_URL)
    body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["message"]["content"]
