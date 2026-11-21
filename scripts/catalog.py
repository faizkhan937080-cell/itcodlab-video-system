"""Director's menu of motion-graphic / asset sources (config/motion-catalog.json). `./run catalog [word]`."""
import json

from .common import CONFIG


def show(word=""):
    d = json.loads((CONFIG / "motion-catalog.json").read_text(encoding="utf-8"))
    w, out = word.lower(), []
    for grp, items in d.items():
        if grp.startswith("_"):
            continue
        rows = [i for i in items if not w or w in json.dumps(i).lower() or w in grp]
        if rows:
            out.append(f"[{grp}]")
            for i in rows:
                out.append(f"- {i['use']}: {i['from']}" + (f" | guide {i['guide']}" if i.get("guide") else "") + (f" | {i['note']}" if i.get("note") else ""))
    return "\n".join(out) or f"nothing for '{word}'"
