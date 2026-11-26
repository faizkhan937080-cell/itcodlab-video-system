"""Add music + beat-matched sfx to an eightbit plan on the worker: fetch free (CC0/PDM/BY) files by name into the library, then write plan.audio.
Run: python -m scripts.sunsound <plan.json> [music query]. Never fakes a sound: a kind with no usable file is skipped and reported."""
import json
import os
import sys
from pathlib import Path

from . import library, sfx
from .storage import Storage

MUSIC_NAME = "8bit-sunburn-loop"
SFX_VOLUME = 0.5
MUSIC_VOLUME = 0.18


def _file_of(st, query, type_, name, tags, fallbacks=(), tries=3):
    """Library first; else Openverse with 3 tries per query (their server sometimes answers 500). Never raises."""
    import time
    try:
        hit = [i for i in library.find(st, name, type_) if i.get("file")]
    except Exception:  # noqa: BLE001
        hit = []
    if hit:
        return hit[0]["file"]
    for q in (query, *fallbacks):
        for n in range(tries):
            try:
                e = library.fetch_from_openverse(st, q, type_, name, tags, token=os.environ.get("OPENVERSE_TOKEN"))
                if e:
                    return e.get("file")
                break
            except Exception as ex:  # noqa: BLE001
                print(f"fetch {name} '{q}' try {n + 1}: {type(ex).__name__} {str(ex)[:80]}")
                time.sleep(4)
    return None


def _synth_local(kind):
    """Own 8-bit sound written straight into remotion/public (no Drive round trip: Drive uploads made the old step time out)."""
    from . import sfx_synth
    from .common import ROOT
    if kind not in sfx_synth.RECIPES:
        return None
    rel = f"assets/library/sfx/8bit-{kind}-own.wav"
    dest = ROOT / "remotion" / "public" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        sfx_synth.make(kind, dest)
        return rel
    except Exception as ex:  # noqa: BLE001
        print(f"synth {kind} failed: {type(ex).__name__} {str(ex)[:80]}")
        return None


def _synth_file(st, kind):
    """Backup when the internet source fails: own 8-bit sound (scripts/sfx_synth.py), added to the library by name."""
    import tempfile
    from . import sfx_synth
    if kind not in sfx_synth.RECIPES:
        return None
    rel = f"assets/library/sfx/8bit-{kind}-own.wav"
    try:
        if not st.exists(rel):
            with tempfile.TemporaryDirectory() as td:
                st.put_file(sfx_synth.make(kind, Path(td) / f"8bit-{kind}-own.wav"), rel)
        return rel
    except Exception as ex:  # noqa: BLE001
        print(f"synth {kind} failed: {type(ex).__name__} {str(ex)[:80]}")
        return None


def run(plan_path, music_query="chiptune 8-bit loop"):
    st = Storage()
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    cues = sfx.plan_cues(plan)
    files, skipped = {}, []
    for kind in sorted({c["kind"] for c in cues}):
        f = (_file_of(st, sfx.QUERIES[kind], "sfx", f"8bit-{kind}", ["8bit", kind], tries=1) if os.environ.get("SUN_INTERNET_SFX") else None) or _synth_local(kind)
        if f:
            files[kind] = f
        else:
            skipped.append(kind)
    audio = [a for a in plan.get("audio", []) if a.get("role") not in ("sfx", "music")]
    total = sum(float(s["duration_s"]) for s in plan["scenes"])
    music = _file_of(st, music_query, "music", MUSIC_NAME, ["chiptune", "8bit", "loop"], ("8-bit game music", "chiptune", "retro game loop"))
    if music:
        audio.append({"src": music, "at_s": 0, "role": "music", "volume": MUSIC_VOLUME, "duration_s": round(total, 3)})
    audio += [dict(a, role="sfx") for a in sfx.audio_defs(cues, files, SFX_VOLUME)]
    plan["audio"] = audio
    Path(plan_path).write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"cues": len(cues), "sfx_files": files, "skipped_kinds": skipped, "music": music, "audio_items": len(audio)}, indent=1))


if __name__ == "__main__":
    run(sys.argv[1], *(sys.argv[2:3]))
