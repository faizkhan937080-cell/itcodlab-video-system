"""Plan-level editing craft (rules: rulebooks/16-pro-editing.md). Pure functions on a plan copy; no files are touched.
- snap_to_beats: move cut points to the nearest beat of the music (cuts on the beat feel tight). Total length is unchanged.
- apply_jl_cuts: J-cut = the next scene's sound starts before its picture, L-cut = a scene's sound runs on over the next picture.
- detect_beats: librosa beat tracking of a music file (worker)."""
import copy

MIN_SCENE_S = 0.4
MAX_AUDIO_ENTRIES = 12      # schema limit


def detect_beats(audio_path):
    """-> (bpm, [beat times in seconds])"""
    import librosa
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
    return round(bpm, 2), [round(float(t), 3) for t in librosa.frames_to_time(frames, sr=sr)]


def snap_to_beats(plan, beats, max_shift_s=0.12, music_at_s=0.0, music_trim_s=0.0):
    """Shift each inner cut to the nearest beat within max_shift_s. Beat times are in the music file; the plan timeline is
    shifted by (music_at_s - music_trim_s). Returns (new_plan, [{boundary, from_s, to_s}])."""
    new = copy.deepcopy(plan)
    tl = sorted(b + music_at_s - music_trim_s for b in beats)
    bounds, t = [], 0.0
    for sc in new["scenes"]:
        t += sc["duration_s"]
        bounds.append(t)
    moves = []
    for i in range(len(bounds) - 1):
        near = min(tl, key=lambda b: abs(b - bounds[i]), default=None)
        if near is None or abs(near - bounds[i]) > max_shift_s or abs(near - bounds[i]) < 1e-3:
            continue
        lo = (bounds[i - 1] if i else 0.0) + MIN_SCENE_S
        hi = bounds[i + 1] - MIN_SCENE_S
        if not lo <= near <= hi:
            continue
        moves.append({"boundary": i + 1, "from_s": round(bounds[i], 3), "to_s": round(near, 3)})
        bounds[i] = near
    prev = 0.0
    for sc, b in zip(new["scenes"], bounds):
        sc["duration_s"] = round(b - prev, 4)
        prev = b
    return new, moves


def apply_jl_cuts(plan):
    """Scenes with props.audio_lead_s (J) and/or props.audio_tail_s (L): the clip's own sound moves into a separate audio entry
    so it can start earlier / end later than its picture. Needs the clip to have footage before/after the trim window
    (lead is limited to trim_start_s). Returns (new_plan, notes)."""
    new = copy.deepcopy(plan)
    notes, t = [], 0.0
    audio = new.setdefault("audio", [])
    for sc in new["scenes"]:
        p = sc.get("props") or {}
        lead, tail = float(p.get("audio_lead_s") or 0), float(p.get("audio_tail_s") or 0)
        start = t
        t += sc["duration_s"]
        if not (lead or tail) or sc.get("template") != "video" or not isinstance(p.get("src"), str):
            continue
        if p.get("speed") or p.get("speed_ramp") or p.get("muted"):
            notes.append(f"{sc['id']}: J/L cut skipped (speed change or muted clip)")
            continue
        trim = float(p.get("trim_start_s") or 0)
        lead = min(lead, trim, start)                       # cannot start before the file or before time 0
        if len(audio) >= MAX_AUDIO_ENTRIES:
            notes.append(f"{sc['id']}: J/L cut skipped (audio entry limit {MAX_AUDIO_ENTRIES})")
            continue
        entry = {"src": p["src"], "at_s": round(start - lead, 3), "trim_start_s": round(trim - lead, 3),
                 "duration_s": round(sc["duration_s"] + lead + tail, 3), "volume": p.get("volume", 1.0)}
        if lead:
            entry["fade_in_s"] = min(0.12, lead)
        if tail:
            entry["fade_out_s"] = min(0.12, tail)
        if p.get("voice"):
            entry["role"] = "voice"
            entry["clean"] = bool(p.get("clean_voice"))
        audio.append(entry)
        p["muted"] = True
        notes.append(f"{sc['id']}: J lead {lead:.2f}s, L tail {tail:.2f}s")
    return new, notes
