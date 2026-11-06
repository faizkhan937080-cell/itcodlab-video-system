"""The 'ears': names what is heard in a reel so nobody has to tell the system the music or sound-effect names.
 1. music_from_meta   - track/artist that Instagram itself reports (yt-dlp source.info.json)
 2. fingerprint_lookup - chromaprint (fpcalc) + AcoustID lookup, needs env ACOUSTID_KEY (free), else skipped
 3. sound_events       - zero-shot audio labels (CLAP) on short windows -> time + name (whoosh, pop, click ...)
 4. resolve_names      - label/name -> library items by tags/names; missing ones are listed for download
Heavy parts (models, network) are injected so the logic is testable; every step degrades to 'not found', never to a guess."""
import json
import subprocess
import urllib.parse
import urllib.request

LABELS = ["whoosh", "swoosh", "pop", "click", "tick", "camera shutter", "paper rustle", "page flip", "typing", "impact hit",
          "riser", "bass drop", "ding notification", "glitch", "stamp", "scribble pen drawing", "cash register", "applause"]
MIN_SCORE = 0.35
WINDOW_S, HOP_S = 1.0, 0.5


def music_from_meta(meta):
    """Instagram sometimes reports the audio: track, artist(s), album. Returns {} when it does not."""
    out = {}
    track = (meta.get("track") or "").strip()
    artists = meta.get("artists") or ([meta["artist"]] if meta.get("artist") else [])
    if track and track.lower() not in ("original audio", "original sound"):
        out = {"title": track, "artists": [a for a in artists if a], "album": meta.get("album"), "source": "instagram-metadata",
               "confidence": "reported"}
    elif track:
        out = {"title": track, "artists": [], "source": "instagram-metadata", "confidence": "original-audio (no named track)"}
    return out


def fingerprint_lookup(wav, key, run=subprocess.run, get=None):
    """fpcalc -> AcoustID. Returns best {title, artists, score, mbid} or {}. No key / no fpcalc / no match -> {} (never guessed)."""
    if not key:
        return {}
    try:
        r = run(["fpcalc", "-json", str(wav)], capture_output=True, text=True, timeout=120)
        fp = json.loads(r.stdout)
        q = urllib.parse.urlencode({"client": key, "meta": "recordings", "duration": int(fp["duration"]), "fingerprint": fp["fingerprint"]})
        raw = get(q) if get else urllib.request.urlopen(f"https://api.acoustid.org/v2/lookup?{q}", timeout=30).read().decode()  # noqa: S310
        for res in sorted(json.loads(raw).get("results", []), key=lambda x: -x.get("score", 0)):
            for rec in res.get("recordings", []):
                if rec.get("title"):
                    return {"title": rec["title"], "artists": [a["name"] for a in rec.get("artists", [])],
                            "score": round(res.get("score", 0), 3), "mbid": rec.get("id"), "source": "acoustid",
                            "confidence": "fingerprint-match"}
    except Exception:  # noqa: BLE001
        return {}
    return {}


def sound_events(wav, score_fn, labels=LABELS, min_score=MIN_SCORE):
    """score_fn(window_samples, sr, labels) -> {label: 0..1}. Windows with a clear label become events;
    neighbours with the same label are merged. Returns [{label, t, end, score}]."""
    import librosa
    y, sr = librosa.load(str(wav), sr=16000, mono=True)
    win, hop = int(WINDOW_S * sr), int(HOP_S * sr)
    events = []
    for i in range(0, max(1, len(y) - win + 1), hop):
        sc = score_fn(y[i:i + win], sr, labels)
        lab, v = max(sc.items(), key=lambda kv: kv[1])
        if v >= min_score:
            t = round(i / sr, 2)
            if events and events[-1]["label"] == lab and t - events[-1]["end"] <= HOP_S + 1e-6:
                events[-1]["end"] = round(t + WINDOW_S, 2)
                events[-1]["score"] = max(events[-1]["score"], round(v, 3))
            else:
                events.append({"label": lab, "t": t, "end": round(t + WINDOW_S, 2), "score": round(v, 3)})
    return events


def clap_scorer():
    """Real model (worker only, ~600 MB download): laion CLAP zero-shot. Imported lazily; raises if unavailable."""
    import torch
    from transformers import ClapModel, ClapProcessor
    model = ClapModel.from_pretrained("laion/clap-htsat-unfused").eval()
    proc = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")

    def score(samples, sr, labels):
        inp = proc(text=[f"the sound of {x}" for x in labels], audios=[samples], sampling_rate=sr, return_tensors="pt", padding=True)
        with torch.no_grad():
            probs = model(**inp).logits_per_audio.softmax(dim=-1)[0].tolist()
        return dict(zip(labels, probs))
    return score


def resolve_names(items, wanted):
    """wanted: [{'name': 'whoosh', 'kind': 'sfx'}...]. Returns (found {name: item_id}, missing [name]).
    Library match by exact name, alias, id or tag. Missing ones go to the downloader, never get invented."""
    found, missing = {}, []
    for w in wanted:
        n = w["name"].lower()
        hit = next((i for i in items if (not w.get("kind") or i["type"] == w["kind"]) and
                    (n == i["name"].lower() or n in [a.lower() for a in i.get("aliases", [])] or n == i["id"] or n in i.get("tags", []))), None)
        if hit:
            found[w["name"]] = hit["id"]
        else:
            missing.append(w["name"])
    return found, missing


def listen(wav, meta, acoustid_key=None, score_fn=None):
    """Everything the ears can say about one reel; each part says how sure it is or that it found nothing."""
    music = music_from_meta(meta or {}) or fingerprint_lookup(wav, acoustid_key)
    out = {"music": music or {"title": None, "note": "not identified (no named track, no fingerprint match)"}}
    if score_fn:
        try:
            out["sound_events"] = sound_events(wav, score_fn)
        except Exception as e:  # noqa: BLE001
            out["sound_events"] = []
            out["sound_events_error"] = f"{type(e).__name__}"
    else:
        out["sound_events"] = []
        out["sound_events_note"] = "model not run"
    return out
