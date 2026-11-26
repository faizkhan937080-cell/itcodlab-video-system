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


def _file_of(st, query, type_, name, tags, fallbacks=()):
    """Library first; else Openverse with 3 tries per query (their server sometimes answers 500). Never raises."""
    import time
    try:
        hit = [i for i in library.find(st, name, type_) if i.get("file")]
    except Exception:  # noqa: BLE001
        hit = []
    if hit:
        return hit[0]["file"]
    for q in (query, *fallbacks):
        for n in range(3):
            try:
                e = library.fetch_from_openverse(st, q, type_, name, tags, token=os.environ.get("OPENVERSE_TOKEN"))
                if e:
                    return e.get("file")
                break
            except Exception as ex:  # noqa: BLE001
                print(f"fetch {name} '{q}' try {n + 1}: {type(ex).__name__} {str(ex)[:80]}")
                time.sleep(4)
    return None


def run(plan_path, music_query="chiptune 8-bit loop"):
    st = Storage()
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    cues = sfx.plan_cues(plan)
    files, skipped = {}, []
    for kind in sorted({c["kind"] for c in cues}):
        f = _file_of(st, sfx.QUERIES[kind], "sfx", f"8bit-{kind}", ["8bit", kind])
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
