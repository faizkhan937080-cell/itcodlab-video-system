"""Clone by NAME: every named element of one reel's recipe is looked up in the library first; what is missing is
fetched from a licensed free source (Openverse sfx/music) and added to the library by its name. Anything that cannot be had
legally (a commercial song, a paid font) is listed as `needs_human_or_licence`, never faked."""
from . import library
from .listen import resolve_names

HOW = {"sfx": "openverse sound_effect (cc0/pdm/by)", "music": "openverse music (cc0/pdm/by) - or licensed track by name",
       "font": "Google Fonts via @remotion/google-fonts (ofl) - no download", "texture": "ambientcg / polyhaven (cc0)",
       "brush": "p5.brush (mit)", "motion": "build as Remotion template (our code)"}


def wanted_from_recipe(card):
    el = card.get("elements", {})
    w = []
    m = el.get("music") or {}
    if m.get("title"):
        w.append({"name": m["title"], "kind": "music"})
    for e in el.get("sfx") or []:
        n = e.get("name") or e.get("label") or e.get("type")
        if n and n != "not analysed":
            w.append({"name": n, "kind": "sfx"})
    for f in el.get("fonts") or []:
        if f.get("name"):
            w.append({"name": f["name"], "kind": "font"})
    for t in el.get("textures") or []:
        if t.get("name"):
            w.append({"name": t["name"], "kind": "texture"})
    return w


def resolve(storage, card):
    wanted = wanted_from_recipe(card)
    items = library.load(storage)
    found, missing = resolve_names(items, wanted)
    kinds = {w["name"]: w["kind"] for w in wanted}
    todo = [{"name": n, "kind": kinds[n], "how": HOW.get(kinds[n], "search")} for n in missing]
    return {"reel": card.get("reel"), "found": found, "missing": todo,
            "needs_human_or_licence": [t for t in todo if t["kind"] in ("music", "font") and "title" not in t]}
