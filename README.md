# LLM Security Training Sandbox

A deliberately vulnerable Python agent for developers learning to build safe LLM
applications, in the spirit of OWASP WebGoat and Juice Shop. Each lesson under
`vulns/` is a pair of modules: `llmNN_<name>.py` (vulnerable) and
`llmNN_<name>_fixed.py` (secure). **The diff between the two files is the lesson.**

> This code is intentionally insecure. Run it only on a local machine against a
> local Ollama model. Never point it at real data, real credentials, or a remote
> model endpoint. The client refuses non-localhost Ollama URLs on purpose.

## Setup

```bash
# 1. Install Ollama (https://ollama.com) and pull a model
ollama pull llama3

# 2. Run a lesson (Python 3.9+, standard library only)
python main.py --list
python main.py llm01            # vulnerable version
python main.py llm01 --fixed    # secure version
```

Environment variables: `OLLAMA_MODEL` (default `llama3`), `OLLAMA_URL`
(default `http://127.0.0.1:11434`, localhost only).

## Layout

```
main.py                      runner + sandbox banner
ollama_client.py             minimal /api/chat client, localhost-only
vulns/common.py              shared helpers used by the fixed versions
vulns/llm01_*                LLM01 Prompt Injection
vulns/llm02_*                LLM02 Insecure Output Handling
vulns/llm06_*                LLM06 Excessive Agency
vulns/llm07_*                LLM07 System Prompt Leakage
vulns/llm08_*                LLM08 Vector & Embedding Weaknesses (unvalidated retrieval)
scratch/                     the only directory lessons read or write
scratch/docs/                retrieval corpus + manifest.json allowlist
tools/update_manifest.py     regenerate the allowlist after editing docs
```

## How to use the lessons

For each category: read the vulnerable module, predict what could go wrong,
run it with ordinary inputs, then diff it against the fixed module
(`diff vulns/llm01_prompt_injection.py vulns/llm01_prompt_injection_fixed.py`)
and map each change to a mitigation in this README. Local models vary in how
reliably they follow instructions, so treat the model's behaviour as
illustrative; the code patterns are the point.

---

## LLM01 — Prompt Injection (untrusted input reaching the prompt)

**What the weakness is.** The model receives one stream of text and cannot
cryptographically tell instructions from data. When untrusted input (user
messages, form fields, uploaded content) is placed where the model expects
instructions, that input can steer the model away from its intended task.

**Why this code is unsafe.** `build_prompt` concatenates the system
instructions and the customer message into a single string sent in a single
`user` message. There is no role separation, no delimiter, no length limit,
no cleaning, and no logging. The application has given the model no structural
hint about which part is trusted.

**How to detect it.**
- *Code review:* look for `+`, f-strings, or `.format()` that mix an
  instruction template with request data; look for a single message where a
  `system` / `user` split was possible; look for inputs with no maximum size.
- *Logging:* log input length and a short preview for every call. Spikes in
  input length, inputs containing role-like tokens ("system:", "assistant:")
  or phrases that address the model rather than the business task, and
  outputs that drift off-topic are the signals to alert on.

**How the fixed version addresses it.** Instructions go in the `system` role
and untrusted text in the `user` role, wrapped in `<customer_message>` tags
with the closing tag escaped. Input is cleaned and capped (`clean_text`).
The system prompt states that the wrapped content is data. Inputs and outputs
are logged, and a cheap output policy check (`within_policy`) suppresses
replies that show the model has left its task. Prompt injection is not fully
solvable at the prompt layer; the goal is to shrink the blast radius, which is
why LLM02 and LLM06 matter as much as this lesson.

---

## LLM02 — Insecure Output Handling (model output passed unsafely downstream)

**What the weakness is.** Treating model output as trusted code or markup.
The model is an untrusted component: anything that influences its input
(users, documents, tool results) indirectly controls its output, so passing
that output to an interpreter, a shell, a database, or a browser reintroduces
every classic injection class.

**Why this code is unsafe.** The model is asked to write raw SQL, and the
string is executed as-is with `conn.execute(sql)`; there is no schema, no
allowlist, and no parameters. The same string, plus the query results, is
then written into HTML without escaping.

**How to detect it.**
- *Code review:* trace every variable that holds model output to its sinks.
  Red flags: `eval`, `exec`, `subprocess`, `os.system`, `cursor.execute(text)`,
  template rendering with autoescape off, `innerHTML`, file paths or URLs built
  from the response. Ask "what schema constrains this value before it is used?"
  If the answer is "none", it is a finding.
- *Logging:* log the raw model output alongside the action taken. Alert on
  outputs that contain statement separators, markup, or multiple statements
  when one was expected, and on parse/validation failures.

**How the fixed version addresses it.** The model returns a small JSON intent
(`column`, `value`). `parse_intent` fails closed: exact key set, column from an
allowlist, bounded string value. The application builds the query itself with
a bound parameter, so the model never authors executable text. Everything
rendered into HTML passes through `html.escape`. Rejected outputs are logged
so a pattern of malformed output is visible during review.

---

## LLM06 — Excessive Agency (tools granted more permission than the task needs)

**What the weakness is.** Giving an agent broader capabilities, permissions,
or autonomy than its task requires. When a model is confused, mistaken, or
manipulated, the damage it can do equals the power it was handed.

**Why this code is unsafe.** The task is "summarise a document", yet the
agent is given `list_dir`, `read_file`, `write_file` and `delete_file`. Paths
are joined with `os.path.join` and never confined, so the sandbox boundary is
a directory-layout convention rather than something the code enforces. Tool
calls execute automatically with no argument validation, no confirmation and
no audit log.

**How to detect it.**
- *Code review:* compare the tool list to the user story. Any tool that
  mutates state for a read-only task is a finding. Check that path, ID and URL
  arguments are validated and confined; check for a step budget; check whether
  destructive actions require confirmation; check that the tool registry is an
  explicit allowlist rather than "whatever the model names".
- *Logging:* every tool invocation should be logged with tool name, arguments,
  caller context and outcome. Review for tools called that the task did not
  need, for denied calls (a sign of confusion or manipulation), and for
  loops that hit the step budget.

**How the fixed version addresses it.** Only `read_file` is exposed, limited
to `.md`/`.txt` under `scratch/docs`, with the path resolved and checked by
`confine_to_scratch` so `..` and symlinks cannot escape. `dispatch` validates
the tool name and exact argument set before running anything. Reads are
size-capped, the loop has a hard step budget, and every call and denial is
logged. A `require_confirmation` gate is in place for any future state-changing
tool, so mutation always goes through a human.

---

## LLM07 — System Prompt Leakage

**What the weakness is.** Assuming the system prompt is confidential and
storing secrets, internal details, or authorization rules inside it. Prompts
are frequently disclosed through ordinary conversation, and a "do not reveal
this" instruction is advice to the model, not an access control.

**Why this code is unsafe.** The prompt embeds an API key, an internal
hostname and a business rule ("names starting with `admin_` get 100% off").
Disclosure leaks credentials and topology; worse, the discount rule is enforced
by the model, so it can be argued with.

**How to detect it.**
- *Code review:* grep prompt files and string constants for key-shaped tokens,
  hostnames, connection strings, and words like "never reveal", "secret",
  "internal", "confidential". Any `if user is X then allow Y` logic expressed
  in prose is authorization in the wrong layer.
- *Logging:* scan outputs for a canary token placed in the prompt and for
  secret-shaped patterns. Scan secret-management logs for keys that only exist
  in prompt text (they should exist nowhere the model can see).

**How the fixed version addresses it.** The prompt contains nothing sensitive
and can be published without harm. The API key lives in the environment and is
used only by application code. `discount_for` computes eligibility server-side
from a verified identity. A per-process canary in the prompt lets `scrub`
detect echoing and log it; secret-shaped patterns are redacted from output as
defence in depth. The design principle: treat the system prompt as public.

---

## LLM08 — Vector & Embedding Weaknesses (unvalidated retrieval data)

**What the weakness is.** Retrieval-augmented generation pulls documents into
the model's context. If those documents are not validated, provenance is not
tracked, and content is framed as authoritative, then whoever can write to the
corpus can influence the assistant — a form of indirect prompt injection with
a supply-chain shape.

**Why this code is unsafe.** `load_knowledge_base` reads every file in
`scratch/docs`, concatenates them raw into the system prompt, and labels the
result "trusted knowledge base ... follow any guidance it contains". There is
no allowlist, no integrity check, no size limit, no separation from
instructions, and no record of which document shaped an answer.

**How to detect it.**
- *Code review:* find where retrieved text enters the prompt. Red flags:
  loading a whole directory or index without an allowlist; inserting documents
  into the `system` role; wording that tells the model to obey document
  content; no per-document size cap; no citation of sources in output; corpus
  writes that do not go through review.
- *Logging:* log the identifiers and hashes of every document retrieved per
  request. Alert on hash mismatches, on documents outside the manifest, and on
  answers whose cited sources do not match what was retrieved. Track corpus
  changes like code changes.

**How the fixed version addresses it.** Documents are loaded only if they
appear in `manifest.json` with a matching SHA-256, so adding a document is a
reviewable change (`tools/update_manifest.py`). Each document is size-capped
and stripped of markup and control characters. Documents are placed in the
`user` turn inside `<document source=...>` tags, and the system prompt states
that they are untrusted reference data. The model is asked to cite sources,
and the retrieval set is logged, giving auditors a trail from answer to
document.

---

## Cross-cutting principles

1. **Roles are signals, not walls.** Separating system/user/data helps the
   model but does not stop injection. Pair it with output validation and
   least-privilege tools.
2. **Model output is untrusted input** to everything downstream. Constrain it
   with schemas, allowlists and parameters; escape it before rendering.
3. **Capability equals blast radius.** Expose the minimum tool surface,
   confine every path, budget every loop, and gate mutations behind a human.
4. **Prompts are public.** Secrets and authorization belong in code and
   configuration the model never sees.
5. **Corpus changes are code changes.** Allowlist, hash, cap, frame as data,
   cite, and log.
6. **Log at the boundaries** — input, model output, tool call, retrieval set —
   so that when something goes wrong you can see where.

## Extending the sandbox

Add a new lesson by creating `vulns/llmNN_<name>.py` and the matching
`_fixed.py`, registering it in `main.py`'s `LESSONS`, and writing a README
section using the same four headings. Keep every lesson confined to
`scratch/` and localhost.
# owasp-ai-lab
