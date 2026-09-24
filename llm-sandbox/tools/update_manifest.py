"""Regenerate scratch/docs/manifest.json (the LLM08 allowlist). Treat changes as code review."""
import hashlib, json, pathlib
d = pathlib.Path(__file__).resolve().parent.parent / "scratch" / "docs"
m = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.glob("*.md")) + sorted(d.glob("*.txt"))}
(d / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
print(f"wrote {len(m)} entries")
