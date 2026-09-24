"""LLM Security Training Sandbox runner.

Usage:
    python main.py <lesson> [--fixed]
    python main.py --list

Each lesson has a deliberately vulnerable module and a *_fixed module.
Run both with the same input and compare behaviour and code.
"""
import argparse
import importlib
import sys

from ollama_client import DEFAULT_MODEL, OLLAMA_URL

LESSONS = {
    "llm01": ("vulns.llm01_prompt_injection", "LLM01 Prompt Injection"),
    "llm02": ("vulns.llm02_insecure_output", "LLM02 Insecure Output Handling"),
    "llm06": ("vulns.llm06_excessive_agency", "LLM06 Excessive Agency"),
    "llm07": ("vulns.llm07_system_prompt_leakage", "LLM07 System Prompt Leakage"),
    "llm08": ("vulns.llm08_unvalidated_retrieval", "LLM08 Vector/Embedding Weaknesses"),
}

BANNER = r"""
==============================================================
  LLM SECURITY TRAINING SANDBOX  --  DELIBERATELY VULNERABLE
  For local learning only. Do not deploy. Do not point at
  real data, real credentials, or a remote model endpoint.
  Model: {model}   Endpoint: {url}
==============================================================
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lesson", nargs="?", choices=LESSONS.keys())
    parser.add_argument("--fixed", action="store_true", help="run the secure implementation")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    print(BANNER.format(model=DEFAULT_MODEL, url=OLLAMA_URL))
    if args.list or not args.lesson:
        for key, (_, title) in LESSONS.items():
            print(f"  {key:6s} {title}")
        return 0

    module_name, title = LESSONS[args.lesson]
    if args.fixed:
        module_name += "_fixed"
    print(f"[{title}] running {'FIXED' if args.fixed else 'VULNERABLE'} version: {module_name}\n")
    module = importlib.import_module(module_name)
    module.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
