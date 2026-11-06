"""Subject tracking + auto-reframe (OpenCV). Output is plain numbers that Remotion draws:
- follow_path(video, box|'face', ...) -> [{t, x, y, w, h}]   box centre/size as fractions of the frame, t = scene-local seconds
- reframe_path(video, info, ...)      -> [{t, x}]           where the 9:16 window sits inside a wider clip (fraction of source width)
Face finding: Haar cascade if this OpenCV ships it, else the small YuNet model (downloaded once from opencv_zoo, worker only).
No face detector = the effect says so and falls back (centre crop) or asks for a box. Never guesses.
"""
from pathlib import Path

import cv2
import numpy as np

YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
LONG_EDGE = 480


def default_face_detector(cache_dir=None):
    """-> fn(frame_bgr) -> [(x, y, w, h) in pixels] or None when no detector can be built here."""
    xml = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    if xml.exists():
        casc = cv2.CascadeClassifier(str(xml))
        return lambda im: [tuple(int(v) for v in b) for b in casc.detectMultiScale(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), 1.1, 5, minSize=(30, 30))]
    try:
        d = Path(cache_dir or Path.home() / ".cache" / "itcodlab")
        d.mkdir(parents=True, exist_ok=True)
        model = d / "yunet.onnx"
        if not model.exists():
            from .netguard import safe_download
            safe_download(YUNET_URL, model, "model", only_hosts=["github.com", "githubusercontent.com"])
        det = cv2.FaceDetectorYN.create(str(model), "", (320, 320), 0.7)

        def run(im):
            h, w = im.shape[:2]
            det.setInputSize((w, h))
            _, faces = det.detect(im)
            return [] if faces is None else [tuple(int(v) for v in f[:4]) for f in faces]
        return run
    except Exception:  # noqa: BLE001
        return None


def _frames(video, start_s, end_s, step_s):
    """Yield (t_s, frame_small_bgr) every step_s seconds, sequential decode (trackers need it)."""
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_s * fps))
    i, nxt = int(start_s * fps), start_s
    try:
        while True:
            ok, fr = cap.read()
            if not ok:
                return
            t = i / fps
            i += 1
            if end_s is not None and t > end_s:
                return
            h, w = fr.shape[:2]
            k = LONG_EDGE / max(h, w)
            small = cv2.resize(fr, (max(2, int(w * k)), max(2, int(h * k))), interpolation=cv2.INTER_AREA) if k < 1 else fr
            yield t, small, t >= nxt - 1e-9
            if t >= nxt - 1e-9:
                nxt += step_s
    finally:
        cap.release()


def make_tracker():
    for name in ("TrackerCSRT_create", "TrackerKCF_create", "TrackerMIL_create"):
        f = getattr(cv2, name, None)
        if f:
            return f()
    raise RuntimeError("no OpenCV tracker available")


def _smooth(vals, a):
    out, cur = [], None
    for v in vals:
        cur = v if cur is None else a * v + (1 - a) * cur
        out.append(cur)
    return out


def track_boxes(frames, box_px, tracker_factory=None):
    """frames: iterable of (t, small_bgr, keep). box_px = (x, y, w, h) on the FIRST frame (same scale). Returns
    ([(t, cx, cy, w, h) fractions], lost_ratio)."""
    tracker_factory = tracker_factory or make_tracker
    tr, rows, lost, n, last = None, [], 0, 0, None
    for t, fr, keep in frames:
        h, w = fr.shape[:2]
        if tr is None:
            tr = tracker_factory()
            tr.init(fr, tuple(int(v) for v in box_px))
            last = tuple(float(v) for v in box_px)
        else:
            ok, b = tr.update(fr)
            n += 1
            if ok:
                last = tuple(float(v) for v in b)
            else:
                lost += 1                      # hold the last known box
        if keep:
            x, y, bw, bh = last
            rows.append((t, (x + bw / 2) / w, (y + bh / 2) / h, bw / w, bh / h))
    return rows, (lost / n if n else 0.0)


def follow_path(video, box, start_s=0.0, end_s=None, t0=0.0, step_s=1 / 15, face=None, tracker_factory=None, max_lost=0.5):
    """box = (x, y, w, h) as FRACTIONS of the frame, or 'face' (first face found in the first second). t = seconds - t0."""
    import itertools
    gen = _frames(video, start_s, end_s, step_s)
    first = next(gen, None)
    if first is None:
        raise RuntimeError("clip has no frames")
    h, w = first[1].shape[:2]
    if box == "face":
        det = face or default_face_detector()
        if det is None:
            raise RuntimeError("no face detector available here: give track_from.box = [x, y, w, h] (fractions)")
        buf = [first] + list(itertools.islice(gen, int(1 / step_s)))
        for i, (_, fr, _) in enumerate(buf):
            faces = det(fr)
            if len(faces):
                box_px = max(faces, key=lambda b: b[2] * b[3])
                gen = itertools.chain(buf[i:], gen)
                break
        else:
            raise RuntimeError("no face found in the first second: give track_from.box")
    else:
        x, y, bw, bh = (float(v) for v in box)
        box_px = (x * w, y * h, bw * w, bh * h)
        gen = itertools.chain([first], gen)
    rows, lost = track_boxes(gen, box_px, tracker_factory)
    if lost > max_lost:
        raise RuntimeError(f"tracker lost the subject in {lost:.0%} of frames: give a clearer box")
    ts = [r[0] - t0 for r in rows]
    cx, cy = _smooth([r[1] for r in rows], 0.6), _smooth([r[2] for r in rows], 0.6)
    bw, bh = _smooth([r[3] for r in rows], 0.3), _smooth([r[4] for r in rows], 0.3)
    return [{"t": round(t, 3), "x": round(a, 4), "y": round(b, 4), "w": round(c, 4), "h": round(d, 4)}
            for t, a, b, c, d in zip(ts, cx, cy, bw, bh)]


# ------------------------------------------------------------------ auto-reframe
def camera_follow(xs, dt, win, dead=0.35, max_speed=0.30):
    """Smooth 'camera operator': stay still while the subject is inside the middle `dead` share of the window, then glide
    (at most max_speed source-widths per second). xs = subject x (0..1) per step; win = visible share of source width."""
    half = win / 2.0
    cam, out = min(max(xs[0], half), 1 - half), []
    for x in xs:
        off = x - cam
        lim = dead * win / 2.0
        if abs(off) > lim:
            target = x - np.sign(off) * lim
            step = np.clip(target - cam, -max_speed * dt, max_speed * dt)
            cam = float(cam + step)
        cam = float(min(max(cam, half), 1 - half))
        out.append(cam)
    return out


def reframe_path(video, info, aspect=9 / 16, start_s=0.0, end_s=None, t0=0.0, face=None, step_s=0.5):
    """Where the crop window sits over time. No face detector / no face = centre (and the caller can see it in the numbers)."""
    win = min(1.0, aspect / (info["width"] / info["height"]))
    if win >= 0.999:
        return [{"t": 0.0, "x": 0.5}]
    det = face or default_face_detector()
    xs, ts, last = [], [], 0.5
    for t, fr, keep in _frames(video, start_s, end_s, step_s):
        if not keep:
            continue
        fs = det(fr) if det else []
        if len(fs):
            x, y, w, h = max(fs, key=lambda b: b[2] * b[3])
            last = (x + w / 2) / fr.shape[1]
        xs.append(last)
        ts.append(t - t0)
    if not xs:
        return [{"t": 0.0, "x": 0.5}]
    cam = camera_follow(xs, step_s, win)
    path = [{"t": round(t, 3), "x": round(c, 4)} for t, c in zip(ts, cam)]
    slim = [path[0]]
    for p in path[1:-1]:
        if abs(p["x"] - slim[-1]["x"]) > 0.004:
            slim.append(p)
    return slim + ([path[-1]] if len(path) > 1 else [])


def output_size(src_w, src_h, aspect=9 / 16):
    """Largest even-sized window of that aspect inside the source: a 4K 16:9 clip gives 1214x2160, the true pixels (no upscaling)."""
    h = src_h if src_w / src_h > aspect else int(src_w / aspect)
    w = int(round(h * aspect))
    return w // 2 * 2, h // 2 * 2
