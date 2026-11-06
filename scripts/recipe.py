"""Recipe card per reference reel: ONE file that links the reel to its DNA and to the named elements it uses
(fonts, music, SFX, motion, textures, tools). Used when Faiz says "make it like THIS reel" (no whole-creator learning).
Built from reel.json + dna paths + `<analysis>/elements.json` (judged by Claude from the collages and transcript)."""
ELEMENT_KEYS = ("fonts", "music", "sfx", "motion", "textures", "tools_named", "layout", "captions", "assets_needed")


def _with_confidence(items):
    """Every named element says how sure it is: seen (on screen) / heard / judged (looks like) / not-analysed. Default judged."""
    if isinstance(items, list):
        return [({"confidence": "judged", **x} if isinstance(x, dict) else x) for x in items]
    if isinstance(items, dict):
        return {"confidence": "judged", **items}
    return items


def build(reel, elements):
    el = {k: _with_confidence(elements[k]) for k in ELEMENT_KEYS if elements and k in elements}
    return {"schema_version": 1, "creator": reel.get("creator", ""), "reel": reel.get("job", ""), "link": reel.get("link", ""),
            "folder": reel.get("analysis", ""), "mode": reel.get("mode", ""), "saved": reel.get("saved", ""),
            "dna": {p.rsplit("__", 2)[-2] if p.count("__") >= 2 else p: p for p in reel.get("dna", [])},
            "files": {"transcript": f"{reel.get('analysis', '')}/transcript.txt", "pack": f"{reel.get('analysis', '')}/pack"},
            "elements": el,
            "how_to_reuse": "Use ONLY this reel's DNA files + elements. For music/SFX/fonts take new licensed items from "
                            "assets/library (never the demucs stem of this reel)."}


def _line(x):
    if isinstance(x, dict):
        return "; ".join(f"{k}: {v}" for k, v in x.items() if v not in (None, "", []))
    return str(x)


def render(card):
    out = [f"# Recipe: {card['reel']} ({card['creator']})", "", f"Reel: {card['link']}", f"Folder: {card['folder']}", ""]
    out.append("## DNA (is reel se bana)")
    out += [f"- {t}: {p}" for t, p in card["dna"].items()] or ["- (none yet)"]
    for k, items in card["elements"].items():
        out += ["", f"## {k}"]
        if isinstance(items, list):
            out += [f"- {_line(i)}" for i in items]
        else:
            out.append(f"- {_line(items)}")
    out += ["", card["how_to_reuse"]]
    return "\n".join(out) + "\n"


def write(storage, reel):
    base = reel["analysis"]
    try:
        elements = storage.read_json(f"{base}/elements.json")
    except Exception:  # noqa: BLE001  (no elements judged yet: card still links reel -> DNA)
        elements = {}
    card = build(reel, elements)
    storage.put_json(f"{base}/recipe.json", card, versioned=False)
    storage.put_text(f"{base}/RECIPE.md", render(card), versioned=False)
    return card
