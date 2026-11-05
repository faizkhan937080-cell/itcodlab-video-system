"""Project memory helper. Long-form, sharded, cheap to read. Never summarises, never deletes.

  ./run mem brief            state + index (what a new session reads first, ~1 KB)
  ./run mem find <words..>   grep memory/ and lessons/, only matching lines
  ./run mem add <shard> <text..> [--keys "k1 k2"]   append one dated line (rolls to <shard>-2 at 58 lines)
  ./run mem index            rebuild memory/index.md from the shards
Every file stays under 60 lines (repo rule). Secrets are refused.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

from .common import ROOT

MEM = ROOT / "memory"
MAX_LINES = 58
SECRET = re.compile(r"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9]{20,}"
                    r"|AKIA[0-9A-Z]{12,}|-----BEGIN|\b(?:\d[ -]?){13,16}\b")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")


def check_secret(text):
    if SECRET.search(text):
        raise ValueError("refused: text looks like a secret (token, key or card number)")


def _lines(p):
    return len(p.read_text(encoding="utf-8").splitlines()) if p.exists() else 0


def _target(shard, mem):
    shard = shard.strip("/").removesuffix(".md")
    base = Path(mem) / f"{shard}.md"
    p, n = base, 1
    while _lines(p) >= MAX_LINES:
        n += 1
        p = base.with_name(f"{base.stem}-{n}.md")
    return p


def add(shard, text, keys="", mem=None):
    check_secret(text)
    p = _target(shard, mem or MEM)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(f"# {p.stem}\nkeys: {keys or p.stem.replace('-', ' ')}\n", encoding="utf-8")
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"- {_now()} {text.strip()}\n")
    return p


def find(words, limit=15, roots=None):
    roots = roots or [MEM, ROOT / "lessons"]
    terms = [w.lower() for w in words]
    hits = []
    for r in roots:
        for p in sorted(Path(r).rglob("*.md")):
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                low = line.lower()
                if all(t in low for t in terms):
                    try:
                        name = p.relative_to(ROOT)
                    except ValueError:
                        name = p
                    hits.append(f"{name}:{i}: {line[:220]}")
    return hits[:limit]


def build_index(mem=None):
    mem = Path(mem or MEM)
    groups = {}
    for p in sorted(mem.rglob("*.md")):
        if p.name == "index.md" or p.name == "state.md":
            continue
        rel = p.relative_to(mem)
        base = re.sub(r"-\d+$", "", str(rel.with_suffix("")))
        keys = ""
        head = p.read_text(encoding="utf-8").splitlines()[:3]
        for h in head:
            if h.startswith("keys:"):
                keys = h[5:].strip()
        g = groups.setdefault(base, {"n": 0, "lines": 0, "keys": keys})
        g["n"] += 1
        g["lines"] += _lines(p)
    out = ["# memory index (auto-built by ./run mem index)",
           "Read memory/state.md first. Then open only the shard you need, or `./run mem find <word>`.",
           "format: path | files | lines | keys"]
    for base, g in groups.items():
        out.append(f"{base}.md | {g['n']} | {g['lines']} | {g['keys'][:90]}")
    out = out[:MAX_LINES]
    (mem / "index.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    return out


def brief():
    parts = []
    for name in ("state.md", "index.md"):
        p = MEM / name
        if p.exists():
            parts.append(p.read_text(encoding="utf-8").rstrip())
    return "\n\n".join(parts)
