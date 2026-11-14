"""Mistake-to-rule loop (point 6). Faiz's reference: 152 review notes, many the same problem in another scene; fixing the video
fixes one scene, fixing the RULE fixes every later video. Notes are saved per job; `digest` groups notes that say the same thing;
a group seen twice or more is promoted to a lesson + a rule line (./run learn path, tripwire registry)."""
import json
import re
from pathlib import Path

from .common import ROOT, now_iso

FILE = ROOT / "memory" / "review-notes.jsonl"
STOP = {"the", "and", "this", "that", "with", "from", "have", "your", "into", "ho", "hai", "ka", "ki", "ke", "me", "mein", "se", "ye", "wo",
        "nahi", "kar", "karo", "bhi", "pe", "par", "ek", "scene", "video", "should", "need", "make", "more", "very"}
SIM = 0.4


def _keys(text):
    return {w[:5] for w in re.findall(r"\w{3,}", (text or "").lower()) if w not in STOP}  # 5-letter stem: covers = covering


def add(job, text, t=None, path=FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"job": job, "t": t, "text": text.strip(), "at": now_iso()}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def load(path=FILE):
    try:
        return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    except OSError:
        return []


def digest(rows=None, min_repeat=2, path=FILE):
    """-> groups [{key, count, jobs, examples}] of notes about the same problem, biggest first."""
    rows = rows if rows is not None else load(path)
    groups = []
    for r in rows:
        k = _keys(r["text"])
        if not k:
            continue
        for g in groups:
            if len(k & g["k"]) / max(1, len(k | g["k"])) >= SIM:
                g["rows"].append(r)
                g["k"] |= k
                break
        else:
            groups.append({"k": set(k), "rows": [r]})
    out = [{"key": " ".join(sorted(g["k"]))[:60], "count": len(g["rows"]), "jobs": sorted({x["job"] for x in g["rows"]}),
            "examples": [x["text"][:90] for x in g["rows"][:2]]} for g in groups if len(g["rows"]) >= min_repeat]
    return sorted(out, key=lambda g: -g["count"])


def lesson_line(group):
    ex = group["examples"][0]
    return (f"M: review note repeated {group['count']}x across {len(group['jobs'])} job(s): {ex} | "
            f"C: rule missing for this look/timing problem | R: never ship it again; check it before the preview")
