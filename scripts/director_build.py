"""Director: approved beats + real voice timings + 3D clips -> one Remotion scene plan (no hand-typed seconds).
Look = measured reference profile (thebrainmaze): hard cuts only, slow 3D camera, cream 2-line captions at y 0.77,
voice over a low music bed. Captions use an OUTSIDE component (remocn caption-dim-progress) + Google font."""
from .anchors import words_from_transcript

CAPTION_LOOK = {"look": "ext", "component": "caption-dim-progress", "font": "Montserrat", "y": 0.77, "max_width": 0.86,
                "props": {"fontSize": 66, "fontWeight": 600, "color": "#F4EFC6", "dimOpacity": 1, "shadow": True,
                          "combineTokensWithinMilliseconds": 1400}}


def captions_from(transcript):
    """One caption per spoken sentence part. Word times come from anchors (same tokenizer), so a display word
    like "you're" or "sixty-five" that anchors splits into pieces still gets the right start/end."""
    from .anchors import norm
    words = words_from_transcript(transcript)
    caps, i = [], 0
    for seg in transcript["segments"]:
        toks = [t for t in seg["text"].split() if norm(t)]
        shown = []
        for t in toks:
            n = len(norm(t))
            ws = words[i:i + n]
            i += n
            if ws:
                shown.append({"text": t, "start_s": ws[0]["start"], "end_s": ws[-1]["end"]})
        if shown:
            caps.append({"text": seg["text"], "start_s": shown[0]["start_s"], "end_s": shown[-1]["end_s"], "words": shown})
    return caps


def build_plan(title, beats_doc, transcript, footage_rel, voice_rel, music=None, size=(1080, 1920), fps=30):
    from .beats import resolve
    vis = [b for b in resolve(beats_doc, words_from_transcript(transcript)) if str(b.get("component", "")).startswith("scene:")]
    end = float(beats_doc["duration_s"])
    scenes = []
    for k, b in enumerate(vis):
        start = 0.0 if k == 0 else b["start_s"]
        nxt = vis[k + 1]["start_s"] if k + 1 < len(vis) else end
        scenes.append({"id": b["id"], "duration_s": round(nxt - start, 3), "template": "video",
                       "props": {"src": f"{footage_rel}/{b['id']}.mp4", "muted": True, "fit": "cover"},
                       "transition_in": {"type": "cut"}})
    audio = [{"src": voice_rel, "at_s": 0, "role": "voice", "volume": 1.0}]
    if music:
        speech = [(c["start_s"], c["end_s"]) for c in captions_from(transcript)]
        audio.append({"src": music, "at_s": 0, "duration_s": end, "role": "music", "volume": 0.35, "fade_in_s": 1.0,
                      "fade_out_s": 2.0, "duck": [{"from_s": a, "to_s": b, "gain": 0.45} for a, b in speech]})
    return {"title": title, "fps": fps, "orientation": "portrait", "width": size[0], "height": size[1],
            "scenes": scenes, "captions": captions_from(transcript), "caption_style": CAPTION_LOOK,
            "audio": audio, "audio_target_lufs": -14, "vignette": 0.22, "grain": False}
