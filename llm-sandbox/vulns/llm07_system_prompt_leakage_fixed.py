"""LLM07 - FIXED: treat the system prompt as public; keep secrets and
authorization decisions outside the model.

Mitigations:
  1. No credentials, internal hostnames or business rules in the prompt.
  2. Secrets stay in the environment and are used only by application code.
  3. Authorization (discount eligibility) is computed server-side from a
     verified identity, never from prompt text or model output.
  4. A canary string in the prompt lets logging detect if the prompt is being
     echoed, without the canary itself being sensitive.
  5. Output is scanned for the canary and for secret-shaped patterns.
"""
import os
import re
import secrets

from ollama_client import chat
from vulns.common import get_logger

log = get_logger("llm07.fixed")

# Secrets live in the environment and are never placed in model context.
API_KEY = os.environ.get("ACME_API_KEY", "")

# Canary: harmless, unique per process, used only to detect prompt echoing.
CANARY = f"cn-{secrets.token_hex(4)}"

SYSTEM = (
    f"You are AcmeCorp's support bot. [{CANARY}] Answer customer questions "
    "about orders and returns. You have no access to pricing rules, internal "
    "systems, or credentials; if asked about them, say the support team will follow up."
)

SECRET_PATTERNS = [re.compile(r"sk-[A-Za-z0-9\-]{8,}"), re.compile(r"intranet\.[a-z.]+")]


def discount_for(verified_user_id: str) -> int:
    """Authorization lives here, in code, keyed on a verified identity."""
    return 100 if verified_user_id in {"admin_carol"} else 0


def scrub(reply: str) -> str:
    if CANARY in reply:
        log.warning("system prompt canary appeared in output")
        reply = reply.replace(CANARY, "")
    for pat in SECRET_PATTERNS:
        if pat.search(reply):
            log.warning("secret-shaped token in output; redacting")
            reply = pat.sub("[redacted]", reply)
    return reply


def run() -> None:
    user_id = "guest"  # would come from an authenticated session
    user_text = input("Customer message> ")
    reply = chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_text}])
    reply = scrub(reply)
    print("\nAssistant:", reply)
    print(f"(server-side discount for {user_id}: {discount_for(user_id)}%)")
