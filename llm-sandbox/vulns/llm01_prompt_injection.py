"""LLM01 - VULNERABLE: untrusted input is spliced directly into the instruction text.

Weakness: the system instructions and the user's text are concatenated into a
single string and sent as one message. The model has no signal that the second
half is data rather than instructions, and nothing limits or logs the input.
"""
from ollama_client import chat

SYSTEM = (
    "You are AcmeCorp's order-status assistant. Only answer questions about "
    "order status. Politely decline anything else."
)


def build_prompt(user_text: str) -> str:
    # BUG: instructions and untrusted data share one string and one role.
    return SYSTEM + "\n\nCustomer message: " + user_text


def run() -> None:
    user_text = input("Customer message> ")
    prompt = build_prompt(user_text)
    reply = chat([{"role": "user", "content": prompt}])
    print("\nAssistant:", reply)
