"""Style record of a reference (rulebooks/23 rule 2). Cut-based analysis sees a cut-less animation reel as ONE picture,
so this one watches CHANGE: every burst of movement on the page becomes an event with
  when it starts (t_in), when it settles (t_settled), how it eases, where it sits, how big, and the text on it.
Also the static parts (brand, footer, handles) and keyframes of the events for a collage.
`complete` stays False (with `problems`) if the record is too thin to rebuild the reel from."""
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .analyze import ocr_text

SAMPLE_FPS = 6.0
PIXEL_DELTA = 14          # grey-level change that counts as "moved"
ACTIVE_FRAC = 0.0015      # share of the page that must change
GAP_SAMPLES = 3           # silence shorter than this joins two movements


def _small(frame, long_edge=360):
    h, w = frame.shape[:2]
    k = long_edge / max(h, w)
    return cv2.resize(frame, (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_AREA)


def _read_at(cap, t):
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000)
    ok, fr = cap.read()
    return fr if ok else None


def _activity(video):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, int(round(fps / SAMPLE_FPS)))
    prev, rows, i = None, [], 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % step == 0:
            g = cv2.cvtColor(_small(fr), cv2.COLOR_BGR2GRAY)
            if prev is not None:
                m = np.abs(g.astype(int) - prev.astype(int)) > PIXEL_DELTA
                frac = float(m.mean())
                bb = None
                if m.any():
                    ys, xs = np.where(m)
                    h, w = g.shape
                    bb = [float(np.percentile(xs, 1)) / w, float(np.percentile(ys, 1)) / h, float(np.percentile(xs, 99)) / w, float(np.percentile(ys, 99)) / h]
                rows.append({"t": round(i / fps, 3), "frac": frac, "bbox": bb})
            prev = g
        i += 1
    cap.release()
    return fps, (n / fps if n else i / fps), rows


def _thresholds(rows):
    """Per-sample threshold. A reel with something always drifting (timeline, background) never goes quiet, so a fixed
    level merges everything into one event. The level follows the local baseline (rolling median ~3 s) and the loud end."""
    f = np.array([r["frac"] for r in rows]) if rows else np.zeros(0)
    if len(f) == 0:
        return f
    half = int(SAMPLE_FPS * 1.5)
    base = np.array([np.median(f[max(0, i - half): i + half + 1]) for i in range(len(f))])
    p95 = float(np.percentile(f, 95))
    return np.maximum(ACTIVE_FRAC, np.maximum(base * 2.5, 0.2 * p95))


def _bursts(rows):
    thr = _thresholds(rows)
    out, cur, gap = [], None, 0
    for r, th in zip(rows, thr):
        if r["frac"] > th and r["bbox"]:
            if cur is None:
                cur = {"t_in": max(0.0, r["t"] - 1 / SAMPLE_FPS), "rows": []}
            cur["rows"].append(r)
            gap = 0
        elif cur is not None:
            gap += 1
            if gap > GAP_SAMPLES:
                out.append(cur)
                cur, gap = None, 0
    if cur is not None:
        out.append(cur)
    return out


def _profile(rows):
    f = np.array([r["frac"] for r in rows])
    if len(f) < 2 or f.sum() == 0:
        return "pop"
    c = float((np.arange(len(f)) * f).sum() / f.sum()) / max(1, len(f) - 1)   # 0 = all change at the start
    return "ease_out" if c < 0.38 else "ease_in_out" if c < 0.62 else "ease_in"


def _union(rows):
    bbs = [r["bbox"] for r in rows if r["bbox"]]
    return [round(min(b[0] for b in bbs), 3), round(min(b[1] for b in bbs), 3), round(max(b[2] for b in bbs), 3), round(max(b[3] for b in bbs), 3)]


def _region(bb):
    cy = (bb[1] + bb[3]) / 2
    area = (bb[2] - bb[0]) * (bb[3] - bb[1])
    where = "header" if cy < 0.2 else "footer" if cy > 0.85 else "lower" if cy > 0.6 else "body"
    return where, ("full" if area > 0.45 else "element")


def _text_in(frame, bb):
    """Words of the full frame whose centre lies in the event box (full-frame OCR reads small text far better than crops)."""
    words = ocr_text(frame)
    if words is None:
        return None
    pad = 0.02
    hit = [w for w in words if bb[0] - pad <= w["x"] + w["w"] / 2 <= bb[2] + pad and bb[1] - pad <= w["y"] + w["h"] / 2 <= bb[3] + pad]
    hit.sort(key=lambda a: (round(a["y"] * 30), a["x"]))
    return " ".join(w["text"] for w in hit)[:160]


def _static_text(cap, dur, n=6):
    seen = {}
    for k in range(n):
        fr = _read_at(cap, dur * (k + 0.5) / n)
        if fr is None:
            continue
        words = ocr_text(fr)
        if not words:
            continue
        lines = {}
        for w in words:
            lines.setdefault(round(w["y"] * 40), []).append(w)
        for ws in lines.values():
            ws.sort(key=lambda a: a["x"])
            txt = " ".join(a["text"] for a in ws)
            y = round(float(np.mean([a["y"] for a in ws])), 2)
            seen.setdefault(txt, {"y": y, "n": 0})["n"] += 1
    return [{"text": t, "y": v["y"]} for t, v in seen.items() if v["n"] >= max(3, n // 2)]


def _collage(cap, events, path, max_tiles=10):
    if not events:
        return None
    pick = events if len(events) <= max_tiles else [events[int(i * (len(events) - 1) / (max_tiles - 1))] for i in range(max_tiles)]
    tiles = []
    for ev in pick:
        fr = _read_at(cap, ev["t_settled"] + 0.1)
        if fr is None:
            continue
        h, w = fr.shape[:2]
        tw = 300 if h >= w else 480
        im = Image.fromarray(cv2.cvtColor(cv2.resize(fr, (tw, int(h * tw / w))), cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(im)
        lab = f"e{ev['id']} {ev['t_in']:.1f}->{ev['t_settled']:.1f}s"
        d.rectangle([0, 0, 8 + 7 * len(lab), 16], fill=(0, 0, 0))
        d.text((3, 2), lab, fill=(255, 255, 255))
        tiles.append(im)
    if not tiles:
        return None
    cols = min(5, len(tiles))
    rows = int(math.ceil(len(tiles) / cols))
    tw_, th_ = tiles[0].size
    sheet = Image.new("RGB", (cols * tw_, rows * th_), (255, 0, 255))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * tw_, (i // cols) * th_))
    sheet.save(path, quality=88)
    return path


def _sheets(cap, dur, out_dir, max_sheets=9, per_sheet=12, cols=4, tile_w=240):
    """Dense look at the WHOLE reference (not only movement events): a frame about every second, labelled with its
    time, on at most `max_sheets` sheets (collage cap 10 incl. the event collage). These sheets are what a clone is
    built and checked against."""
    n = max_sheets * per_sheet
    step = max(dur / n, 0.25)
    times = [round(min(dur - 0.05, (i + 0.5) * step), 2) for i in range(int(dur / step))][:n]
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1080
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1920
    tile_h = int(tile_w * h / w)
    names = []
    for k in range(0, len(times), per_sheet):
        chunk = times[k:k + per_sheet]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (0, 0, 0))
        d = ImageDraw.Draw(sheet)
        for j, t in enumerate(chunk):
            fr = _read_at(cap, t)
            if fr is None:
                continue
            im = Image.fromarray(cv2.cvtColor(cv2.resize(fr, (tile_w, tile_h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB))
            x, y = (j % cols) * tile_w, (j // cols) * tile_h
            sheet.paste(im, (x, y))
            d.rectangle([x, y, x + 52, y + 16], fill=(0, 0, 0))
            d.text((x + 3, y + 2), f"{t:.1f}s", fill=(255, 255, 0))
        name = f"collage_ref_{len(names) + 1:02d}.jpg"
        sheet.save(Path(out_dir) / name, quality=88)
        names.append({"file": name, "times": chunk})
    return names


def build(video, out_dir, lim=None, with_ocr=True):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fps, dur, rows = _activity(video)
    cap = cv2.VideoCapture(str(video))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    events = []
    for k, b in enumerate(_bursts(rows), 1):
        rs = b["rows"]
        bb = _union(rs)
        where, size = _region(bb)
        ev = {"id": k, "t_in": round(b["t_in"], 2), "t_settled": round(rs[-1]["t"], 2),
              "entrance_s": round(rs[-1]["t"] - b["t_in"], 2), "ease": _profile(rs),
              "bbox": bb, "where": where, "size": size, "peak_change": round(max(r["frac"] for r in rs), 4)}
        events.append(ev)
    if with_ocr:
        for ev in events:
            fr = _read_at(cap, ev["t_settled"] + 0.1)
            ev["text"] = _text_in(fr, ev["bbox"]) if fr is not None else None
    static = _static_text(cap, dur) if with_ocr else []
    coll = _collage(cap, events, out_dir / "collage_events.jpg")
    sheets = _sheets(cap, dur, out_dir)
    cap.release()
    problems = []
    need = 1 if dur < 8 else max(2, int(dur / 15))
    if len(events) < need and dur >= 8:
        problems.append(f"only {len(events)} movement event(s) found in {dur:.0f}s (need >= {need}); this is a plain talking video, not an animation reel, or the sampling missed it")
    if with_ocr and events and all(not e.get("text") for e in events):
        problems.append("no text could be read on any event (OCR missing or text too small)")
    rec = {"video": {"width": w, "height": h, "fps": round(fps, 2), "duration_s": round(dur, 2)},
           "static_text": static, "events": events, "event_collage": coll.name if coll else None,
           "event_count": len(events), "frame_sheets": sheets, "complete": not problems, "problems": problems}
    # raw activity curve: lets the detector be tuned on the real reel without rendering anything again
    (out_dir / "activity.json").write_text(json.dumps([[r["t"], round(r["frac"], 5)] + ([round(x, 3) for x in r["bbox"]] if r["bbox"] else []) for r in rows]), encoding="utf-8")
    (out_dir / "style_record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec
