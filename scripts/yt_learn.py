"""Learning material from YouTube videos Faiz gives (not creator references, nothing goes into creators/ or DNA).
Per video: title, channel, date, length, full description (all links), chapters and the spoken words
(the video's own subtitles; if it has none, the audio is turned into text with faster-whisper).
Output: Drive research/youtube-learning/<id>.json + <id>.txt (plain transcript with [mm:ss] marks).
Polite network: yt-dlp with the same gaps/cooldown as every download (netguard)."""
import json
import os
import re
import tempfile
from pathlib import Path

from .common import log, now_iso, run_cmd, stage, tail

ID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})")


def vid_id(url):
    m = ID_RE.search(url)
    return m.group(1) if m else None


def _ts(sec):
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60:02d}:{sec % 60:02d}"


def vtt_to_lines(text):
    """YouTube auto-subtitles repeat each line 2-3 times while it scrolls: keep each new line once, with its time."""
    out, seen, cur = [], set(), 0.0
    for block in text.split("\n\n"):
        lines = [ln for ln in block.strip().splitlines() if ln.strip()]
        if not lines:
            continue
        for i, ln in enumerate(lines):
            m = re.match(r"(\d+):(\d+):(\d+)\.(\d+)\s+-->", ln) or re.match(r"(\d+):(\d+)\.(\d+)\s+-->", ln)
            if m:
                g = [int(x) for x in m.groups()]
                cur = g[0] * 3600 + g[1] * 60 + g[2] if len(g) == 4 else g[0] * 60 + g[1]
                for t in lines[i + 1:]:
                    t = re.sub(r"<[^>]+>", "", t).strip()
                    if t and t not in seen:
                        seen.add(t)
                        out.append((cur, t))
                break
    return out


def _join(lines, every_s=30):
    """[mm:ss] mark about every 30 s, words in between joined into running text."""
    paras, last, buf = [], -every_s, []
    for t, s in lines:
        if t - last >= every_s and buf:
            paras.append(buf)
            buf = []
        if not buf:
            buf = [f"[{_ts(t)}]"]
            last = t
        buf.append(s)
    if buf:
        paras.append(buf)
    return "\n".join(" ".join(p) for p in paras)


def _whisper(audio):
    from faster_whisper import WhisperModel
    model = WhisperModel(os.environ.get("ITCOD_LEARN_WHISPER", "small"), device="cpu", compute_type="int8")
    segs, info = model.transcribe(str(audio), vad_filter=True)
    return [(s.start, s.text.strip()) for s in segs], info.language


def one(url, storage, wd):
    from .netguard import config as net_config, guard, host_key
    vid = vid_id(url)
    if not vid:
        raise ValueError(f"not a YouTube link: {url}")
    cfg = net_config()
    key = host_key(url, cfg)
    g = guard()
    clean = f"https://www.youtube.com/watch?v={vid}"
    base = ["yt-dlp", "--no-playlist", *cfg["yt_dlp_polite"]]
    cookies = os.environ.get("ITCOD_COOKIES")
    if cookies and Path(cookies).exists():
        base += ["--cookies", cookies]
    g.before(key)
    rc, out, err = run_cmd(base + ["--skip-download", "--write-info-json", "--write-subs", "--write-auto-subs",
                                   "--sub-langs", "en,en-orig,en-US,hi,en.*", "--sub-format", "vtt",
                                   "-o", str(wd / f"{vid}.%(ext)s"), clean], timeout=900)
    if rc != 0:
        g.after(key, None, err or out)
        raise RuntimeError("yt-dlp failed:\n" + tail(err or out))
    info = json.loads((wd / f"{vid}.info.json").read_text(encoding="utf-8"))
    subs = sorted(wd.glob(f"{vid}*.vtt"), key=lambda p: (".en-orig." not in p.name, ".en." not in p.name, p.name))
    source, lang = "none", None
    lines = []
    if subs:
        lines = vtt_to_lines(subs[0].read_text(encoding="utf-8", errors="ignore"))
        source, lang = f"subtitles:{subs[0].name.split('.')[-2]}", subs[0].name.split(".")[-2]
    if not lines:                                 # no subtitles: listen to the audio
        g.before(key)
        rc, out, err = run_cmd(base + ["-f", "ba/b", "-x", "--audio-format", "m4a", "-o", str(wd / f"{vid}.audio.%(ext)s"), clean],
                               timeout=1800)
        if rc != 0:
            g.after(key, None, err or out)
            raise RuntimeError("yt-dlp audio failed:\n" + tail(err or out))
        audio = next(iter(sorted(wd.glob(f"{vid}.audio.*"))))
        with stage("learn_whisper"):
            lines, lang = _whisper(audio)
        source = "whisper"
    rec = {
        "id": vid, "url": clean, "fetched": now_iso(), "title": info.get("title"), "channel": info.get("channel") or info.get("uploader"),
        "upload_date": info.get("upload_date"), "duration_s": info.get("duration"), "views": info.get("view_count"),
        "description": info.get("description"), "chapters": info.get("chapters") or [], "tags": info.get("tags") or [],
        "transcript_source": source, "language": lang, "words": sum(len(s.split()) for _t, s in lines),
        "lines": [[round(t, 1), s] for t, s in lines],
    }
    txt = (f"# {rec['title']}\n# {rec['channel']} | {rec['upload_date']} | {_ts(rec['duration_s'] or 0)} | {clean}\n\n"
           f"## Description\n{rec['description']}\n\n## Chapters\n"
           + "\n".join(f"{_ts(c.get('start_time', 0))} {c.get('title')}" for c in rec["chapters"])
           + f"\n\n## Transcript ({source})\n{_join(lines)}\n")
    storage.put_json(f"research/youtube-learning/{vid}.json", rec)
    (wd / f"{vid}.txt").write_text(txt, encoding="utf-8")
    storage.put_file(wd / f"{vid}.txt", f"research/youtube-learning/{vid}.txt")
    log(f"learn {vid}: {rec['title']!r} {rec['words']} words from {source}")
    return {"id": vid, "title": rec["title"], "words": rec["words"], "source": source}


GEM_TRANSCRIPT = (
    "Write the COMPLETE transcript of everything spoken in this video, word for word, in the language spoken "
    "(keep Hindi/English as spoken, Latin letters for Hindi). Put a [mm:ss] time mark at the start of every new "
    "paragraph, about every 20-40 seconds. Do not summarise, do not skip any part, do not add comments.")
GEM_SCREEN = (
    "This is a tutorial video. Walk through it in time order and write down, as plain text with [mm:ss] marks, "
    "EVERYTHING shown on screen that a person would need to repeat the work: every app, website, tool, library, "
    "GitHub repo, file and folder name, setting, button, command typed, code or config visible, prompt text typed "
    "into an AI (copy it exactly when readable), templates, skills, before/after results, and the order of the steps. "
    "Then a section 'TOOLS AND LINKS' listing every tool/product/repo named or shown, with what it is used for. "
    "Facts only.")


def gemini_watch(url, prompt, low_res=True):
    """Google's own Gemini API reads a public YouTube link itself (official feature; our machine never contacts
    YouTube). Used when YouTube blocks the worker."""
    from .describe import _post, get_key
    import time
    import urllib.error
    key = get_key()
    if not key:
        raise RuntimeError("no GEMINI_API_KEY")
    body = {"contents": [{"parts": [{"file_data": {"file_uri": url}}, {"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 65536,
                                 **({"mediaResolution": "MEDIA_RESOLUTION_LOW"} if low_res else {})}}
    last = ""
    for model in ("gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-pro"):
        for attempt in range(3):
            try:
                with stage("learn_gemini"):
                    res = _post(model, key, body, timeout=900)
                try:
                    from . import costs
                    um = res.get("usageMetadata", {})
                    costs.add("gemini", calls=1, in_tok=um.get("promptTokenCount", 0),
                              out_tok=um.get("candidatesTokenCount", 0) + um.get("thoughtsTokenCount", 0), model=model)
                except Exception:  # noqa: BLE001
                    pass
                parts = res["candidates"][0]["content"].get("parts", [])
                return model, "".join(p.get("text", "") for p in parts)
            except urllib.error.HTTPError as e:
                last = f"{model} HTTP {e.code}: {e.read().decode(errors='ignore')[:300]}"
                if e.code == 429:
                    time.sleep(60 * (attempt + 1))
                elif e.code in (400, 403, 404):
                    break
            except Exception as e:  # noqa: BLE001
                last = f"{model} {type(e).__name__}: {str(e)[:200]}"
                time.sleep(10)
    raise RuntimeError(last)


def one_gemini(url, storage, wd):
    vid = vid_id(url)
    clean = f"https://www.youtube.com/watch?v={vid}"
    m1, spoken = gemini_watch(clean, GEM_TRANSCRIPT)
    m2, screen = gemini_watch(clean, GEM_SCREEN)
    rec = {"id": vid, "url": clean, "fetched": now_iso(), "transcript_source": f"gemini:{m1}", "screen_source": f"gemini:{m2}",
           "transcript": spoken, "screen": screen, "words": len(spoken.split())}
    storage.put_json(f"research/youtube-learning/{vid}.json", rec)
    txt = f"# {clean}\n\n## Transcript (Gemini {m1})\n{spoken}\n\n## On screen (Gemini {m2})\n{screen}\n"
    (wd / f"{vid}.txt").write_text(txt, encoding="utf-8")
    storage.put_file(wd / f"{vid}.txt", f"research/youtube-learning/{vid}.txt")
    log(f"learn {vid}: {rec['words']} words via Gemini")
    return {"id": vid, "words": rec["words"], "source": rec["transcript_source"]}


def run(urls, storage, via=None):
    done = []
    with tempfile.TemporaryDirectory(prefix="itcod-learn-") as wd:
        for u in urls:
            try:
                if via == "gemini":
                    done.append(one_gemini(u, storage, Path(wd)))
                    continue
                try:
                    done.append(one(u, storage, Path(wd)))
                except Exception as e:  # noqa: BLE001
                    if "Sign in" in str(e) or "cooldown" in str(e) or "said stop" in str(e):
                        log(f"youtube blocked this machine; reading {u} through Gemini instead")
                        done.append(one_gemini(u, storage, Path(wd)))
                    else:
                        raise
            except Exception as e:  # noqa: BLE001
                log(f"learn failed for {u}: {str(e)[:300]}")
                done.append({"url": u, "error": str(e)[:300]})
    storage.put_json(f"research/youtube-learning/_batch_{now_iso().replace(':', '').replace('-', '')}.json", {"items": done})
    print(json.dumps(done, indent=1))
    return done
