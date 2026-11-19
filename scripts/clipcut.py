"""Clip-and-text reels (Faiz 2026-11-19): real clips from interviews/films/YouTube + matching text + date/topic card.
Phase 1 `subs`: per YouTube link read title + timed subtitle lines (no video downloaded) -> branch `review` manifest.json,
so Claude can pick the exact lines/times. Phase 2 `cut` (see clipcut_build.py): download only those seconds, compose."""
import json
import os
import tempfile
from pathlib import Path

from .common import log, run_cmd, tail
from .yt_learn import vid_id, vtt_to_lines


def subs(spec, out_dir):
    from .netguard import config as net_config, guard, host_key
    cfg = net_config()
    g = guard()
    res = []
    for url in spec["urls"]:
        vid = vid_id(url)
        if not vid:
            res.append({"url": url, "error": "not a YouTube link"})
            continue
        clean = f"https://www.youtube.com/watch?v={vid}"
        key = host_key(clean, cfg)
        with tempfile.TemporaryDirectory(prefix="itcod-cc-") as wd:
            wd = Path(wd)
            g.before(key)
            cmd = ["yt-dlp", "--no-playlist", *cfg["yt_dlp_polite"], "--skip-download", "--write-info-json", "--write-subs",
                   "--write-auto-subs", "--sub-langs", "hi,en,en-orig,hi-orig,en.*", "--sub-format", "vtt", "-o", str(wd / f"{vid}.%(ext)s"), clean]
            ck = os.environ.get("ITCOD_COOKIES")
            if ck and Path(ck).exists():
                cmd[1:1] = ["--cookies", ck]
            rc, o, e = run_cmd(cmd, timeout=600)
            if rc != 0:
                g.after(key, None, e or o)
                res.append({"id": vid, "error": tail(e or o)})
                continue
            info = json.loads((wd / f"{vid}.info.json").read_text(encoding="utf-8"))
            files = sorted(wd.glob(f"{vid}*.vtt"))
            lines = []
            lang = None
            if files:
                f = files[0]
                lang = f.name.split(".")[-2]
                lines = [[round(t, 1), s] for t, s in vtt_to_lines(f.read_text(encoding="utf-8", errors="ignore"))]
            res.append({"id": vid, "title": info.get("title"), "channel": info.get("channel"), "duration_s": info.get("duration"),
                        "views": info.get("view_count"), "sub_lang": lang, "lines": lines})
            log(f"clipcut subs {vid}: {info.get('title')!r} {len(lines)} lines ({lang})")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps({"name": spec["name"], "videos": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    return res
