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


def rank(results, max_s=MAX_DURATION_S):
    """Allowed results, best first: CC0 before PDM before CC BY, then shorter."""
    good = []
    for r in results or []:
        lic = (r.get("license") or "").lower()
        dur = (r.get("duration") or 0) / 1000.0
        if lic in OK_LICENSES and r.get("url") and 0 < dur <= max_s:
            good.append((OK_LICENSES.index(lic), dur, r))
    return [r for _, _, r in sorted(good, key=lambda x: (x[0], x[1]))]


def credit_of(item):
    """CC BY needs a credit line; CC0 / PDM do not."""
    if (item.get("license") or "").lower() != "by":
        return None
    return item.get("attribution") or f'{item.get("title")} by {item.get("creator")} ({item.get("license")})'


def pick(results, max_s=MAX_DURATION_S):
    """Best allowed result -> (item, credit_or_None), or (None, None)."""
    ranked = rank(results, max_s)
    return (ranked[0], credit_of(ranked[0])) if ranked else (None, None)


def search(kind, page_size=20, token=None):
    """Openverse audio search for sound effects that allow commercial use. Needs network (worker only)."""
    return search_q(QUERIES[kind], "sound_effect", "short", page_size, token)


def search_q(query, category="sound_effect", duration="short", page_size=20, token=None):
    """Same for any text query and category (sound_effect | music)."""
    p = {"q": query, "category": category, "license_type": "commercial", "page_size": page_size}
    if duration:
        p["duration"] = duration
    q = urllib.parse.urlencode(p)
    from .netguard import config, guard
    req = urllib.request.Request(f"{OPENVERSE}?{q}", headers={"User-Agent": config()["user_agent"]})
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    def go():
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8")).get("results", [])
    return guard().call("openverse", go)


def audio_defs(cues, files, volume=SFX_VOLUME):
    """cues + {kind: 'assets/sfx/x.mp3'} -> plan.audio entries (kinds without a file are skipped, never invented)."""
    return [{"src": files[c["kind"]], "at_s": round(c["t"], 3), "volume": volume} for c in cues if c["kind"] in files]


PEAK_MAX_DB = -0.5   # louder = clipped
PEAK_MIN_DB = -35.0  # quieter = unusable


def judge(duration_s, peak_db):
    """Numbers instead of ears: returns None if the file is fine, else the reason."""
    if duration_s is None or duration_s <= 0 or duration_s > MAX_DURATION_S + 0.5:
        return f"duration {duration_s}"
    if peak_db is None:
        return "peak not measured"
    if peak_db > PEAK_MAX_DB:
        return f"clipped (peak {peak_db} dB)"
    if peak_db < PEAK_MIN_DB:
        return f"too quiet (peak {peak_db} dB)"
    return None


def measure(path):
    """(duration_s, peak_db) with ffprobe / ffmpeg volumedetect. Script-only (Claude never runs these)."""
    import re
    from .common import run_cmd
    rc, out, _ = run_cmd(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], timeout=60)
    dur = float(out.strip()) if rc == 0 and out.strip() else None
    _, _, err = run_cmd(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], timeout=120)
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", err or "")
    return dur, (float(m.group(1)) if m else None)


def download(url, dest):
    """https only, public addresses only, size cap, content must really be audio (no programs, archives or web pages)."""
    from .netguard import safe_download
    return safe_download(url, dest, "audio")


def fetch_all(plan, out_dir, rel_prefix="assets/sfx", token=None, search_fn=None, download_fn=None, measure_fn=None):
    """For every cue kind in the plan: search, take the best candidate that passes the number check, download it.
    Returns {"files": {kind: rel_path}, "credits": [...], "skipped": {kind: reason}}. A kind with no good file is skipped, never faked."""
    from pathlib import Path
    search_fn, download_fn, measure_fn = search_fn or search, download_fn or download, measure_fn or measure
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files, credits, skipped = {}, [], {}
    for kind in sorted({c["kind"] for c in plan_cues(plan)}):
        try:
            cands = rank(search_fn(kind, token=token) if token else search_fn(kind))
        except Exception as e:  # noqa: BLE001
            skipped[kind] = f"search failed: {e}"
            continue
        why = "no allowed candidate"
        for item in cands[:5]:
            ext = item.get("url", "").split("?")[0].rsplit(".", 1)[-1].lower()
            ext = ext if ext in ("mp3", "wav", "ogg", "flac", "m4a") else "mp3"
            dest = out_dir / f"{kind}.{ext}"
            try:
                download_fn(item["url"], dest)
                bad = judge(*measure_fn(dest))
            except Exception as e:  # noqa: BLE001
                bad = f"download/measure failed: {e}"
            if bad is None:
                files[kind] = f"{rel_prefix}/{dest.name}"
                c = credit_of(item)
                if c:
                    credits.append(c)
                break
            why = bad  # rejected file is simply overwritten by the next candidate; it is never referenced by the plan
        else:
            skipped[kind] = why
    return {"files": files, "credits": credits, "skipped": skipped}
