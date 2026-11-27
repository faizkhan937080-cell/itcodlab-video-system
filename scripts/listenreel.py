"""Listen to one reference reel again (CLAP sound events + music name) and put listen.json on branch `review`.
Run on the worker: ./run listen-reel <handle>/<code>   (e.g. 8bit_sciences/DgJre5hyNYW)."""
import json
import tempfile
from pathlib import Path

from .common import limits, log

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm")


def run(handle_code, storage=None):
    from . import audio, layout, listen, review
    from .storage import Storage
    st = storage or Storage()
    handle, code = handle_code.split("/", 1)
    base = layout.reel_rel(handle, code)
    names = [n for n in st.list_dir(base) if n.lower().endswith(VIDEO_EXT)]
    if not names:
        raise SystemExit(f"no source video in {base}")
    src = sorted(names, key=lambda n: (not n.startswith("source"), n))[0]
    work = Path(tempfile.mkdtemp(prefix="listen_"))
    st.fetch(f"{base}/{src}", work / src)
    wav = audio.extract_wav(work / src, work / "a.wav")
    meta = {}
    if st.exists(f"{base}/source.info.json"):
        meta = st.read_json(f"{base}/source.info.json")
    from .pack import _listen
    res = _listen(work / src, wav, limits())
    pack = work / "pack"
    pack.mkdir()
    (pack / "listen.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    st.put_json(f"{base}/listen.json", res)
    log(f"listen: {len(res.get('sound_events', []))} sound events, error={res.get('sound_events_error')}")
    print(json.dumps(res, ensure_ascii=False)[:3000])
    print(review.publish(pack, f"listen-{code}"))
    return res
