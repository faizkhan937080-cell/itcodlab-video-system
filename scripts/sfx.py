"""SFX layer (from Faiz's reel 2026-11-06: search -> check quality -> place exactly). Pure planning + filtering; the network call is thin.
Placement is deterministic from the scene plan (cut times are known exactly), so no 'placement tool' is needed.
Only licences that allow commercial use are kept (CC0 / PDM / CC BY). CC BY needs attribution: it is returned in `credits`.
Claude never listens: quality gate = measured numbers (duration, peak) done by scripts, not by ear."""
import json
import urllib.parse
import urllib.request

LEAD_S = 0.12            # whoosh starts slightly before the visual change (sound leads the picture)
SFX_VOLUME = 0.35        # under the voice
MAX_DURATION_S = 4.0
OK_LICENSES = ("cc0", "pdm", "by")   # commercial use allowed; "by-sa", "by-nc*", "*-nd" are skipped on purpose
QUERIES = {"whoosh": "whoosh", "hit": "impact hit", "pop": "pop", "tick": "click tick"}
OPENVERSE = "https://api.openverse.org/v1/audio/"


def plan_cues(plan):
    """Scene plan -> [{t, kind, scene}] sorted by time. kind in QUERIES."""
    fps = plan.get("fps", 30)
    cues, t = [], 0.0
    for sc in plan["scenes"]:
        d = float(sc["duration_s"])
        tpl = sc["template"]
        trans = (sc.get("transition_in") or {}).get("type", "cut")
        if t > 0 and trans in ("slide", "zoom", "fade"):
            cues.append({"t": max(0.0, t - LEAD_S), "kind": "whoosh", "scene": sc["id"]})
        if tpl == "title":
            cues.append({"t": t, "kind": "hit", "scene": sc["id"]})
        elif tpl in ("counter", "bar_chart", "stroke", "paper_cutout", "quote", "split_compare", "banner", "lower_third"):
            cues.append({"t": t + 3 / fps, "kind": "pop", "scene": sc["id"]})
        elif tpl == "checklist":
            n = max(1, len((sc.get("props") or {}).get("items") or []))
            step = max(6, int(d * fps * 0.7 / n)) / fps
            for i in range(n):
                cues.append({"t": t + 6 / fps + i * step, "kind": "tick", "scene": sc["id"]})
        t += d
    return sorted(cues, key=lambda c: c["t"])


def pick(results, max_s=MAX_DURATION_S):
    """Choose the best Openverse audio result: licence allowed, short, CC0 first. Returns (item, credit_or_None) or (None, None)."""
    good = []
    for r in results or []:
        lic = (r.get("license") or "").lower()
        dur = (r.get("duration") or 0) / 1000.0
        if lic in OK_LICENSES and r.get("url") and 0 < dur <= max_s:
            good.append((OK_LICENSES.index(lic), dur, r))
    if not good:
        return None, None
    _, _, best = sorted(good, key=lambda x: (x[0], x[1]))[0]
    credit = best.get("attribution") or f'{best.get("title")} by {best.get("creator")} ({best.get("license")})' \
        if (best.get("license") or "").lower() == "by" else None
    return best, credit


def search(kind, page_size=20, token=None):
    """Openverse audio search for sound effects that allow commercial use. Needs network (worker only)."""
    q = urllib.parse.urlencode({"q": QUERIES[kind], "category": "sound_effect", "license_type": "commercial",
                                "duration": "short", "page_size": page_size})
    req = urllib.request.Request(f"{OPENVERSE}?{q}", headers={"User-Agent": "itcodlab-video-system"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
        return json.loads(r.read().decode("utf-8")).get("results", [])


def audio_defs(cues, files, volume=SFX_VOLUME):
    """cues + {kind: 'assets/sfx/x.mp3'} -> plan.audio entries (kinds without a file are skipped, never invented)."""
    return [{"src": files[c["kind"]], "at_s": round(c["t"], 3), "volume": volume} for c in cues if c["kind"] in files]
