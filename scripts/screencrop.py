"""Screen-in-scene references: find the playing video inside a phone-filmed monitor / player box and
flatten ONLY that region (rulebooks/23: analyse the final video, never the room). Free: opencv + ffmpeg."""
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

MIN_AREA = 0.08
MAX_AREA = 0.96
MARGIN = 0.15          # best must beat the 2nd by this much to be picked without Claude
MIN_SCORE = 0.45


def _order(p):
    p = np.array(p, dtype=np.float32).reshape(4, 2)
    s, d = p.sum(1), np.diff(p, axis=1).ravel()
    return np.array([p[s.argmin()], p[d.argmin()], p[s.argmax()], p[d.argmax()]], dtype=np.float32)  # TL TR BR BL


def _area(q):
    return abs(cv2.contourArea(np.array(q, dtype=np.float32)))


def _sample(video, n, width=480):
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w0, h0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    idx = np.linspace(0, max(total - 2, 0), n).astype(int) if total > 1 else [0]
    out = []
    for i in idx:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, f = cap.read()
        if ok:
            out.append(f)
    cap.release()
    if not out:
        raise RuntimeError("no frames could be read")
    sc = width / out[0].shape[1]
    return [cv2.resize(f, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) for f in out], sc, (w0, h0)


def _quads_from_mask(mask, shape):
    H, W = shape[:2]
    res = []
    cs, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for c in cs:
        if cv2.contourArea(c) < MIN_AREA * W * H:
            continue
        hull = cv2.convexHull(c)
        ap = cv2.approxPolyDP(hull, 0.03 * cv2.arcLength(hull, True), True)
        q = ap.reshape(-1, 2) if len(ap) == 4 and _area(ap.reshape(-1, 2)) >= 0.92 * cv2.contourArea(hull) else cv2.boxPoints(cv2.minAreaRect(hull))
        q = _order(q)
        if MIN_AREA * W * H <= _area(q) <= MAX_AREA * W * H:
            res.append(q)
    return res


def _edge_quads(f):
    g = cv2.GaussianBlur(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    out = []
    for lo, hi in ((40, 120), (20, 60)):
        e = cv2.dilate(cv2.Canny(g, lo, hi), np.ones((3, 3), np.uint8))
        cs, _ = cv2.findContours(e, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in cs:                                   # closed outline of a screen edge -> 4 corners
            if cv2.contourArea(c) < MIN_AREA * g.size:
                continue
            ap = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
            if len(ap) == 4 and cv2.isContourConvex(ap):
                q = _order(ap.reshape(-1, 2))
                if MIN_AREA * g.size <= _area(q) <= MAX_AREA * g.size:
                    out.append(q)
    return out


def _motion_map(frames):
    g = np.stack([cv2.GaussianBlur(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (0, 0), 6).astype(np.float32) for f in frames])
    return g.std(0)   # heavy blur: phone shake moves edges by pixels, the playing video changes whole areas


def _motion_quads(std):
    m = (std > 0.2 * np.percentile(std, 99)).astype(np.uint8) * 255
    k = np.ones((15, 15), np.uint8)
    m = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_CLOSE, k), cv2.MORPH_OPEN, k)
    return _quads_from_mask(m, std.shape)


def _contrast(std, q):
    m = np.zeros(std.shape, np.uint8)
    cv2.fillPoly(m, [q.astype(np.int32)], 1)
    ins, out = std[m > 0].mean(), (std[m == 0].mean() if (m == 0).any() else 0)
    return float(ins / (ins + out + 1e-6))


def detect(video, out_dir=None, n_frames=12):
    """-> list of {id, quad (source px), score, area} best first; writes screen_candidates.jpg/json if out_dir."""
    frames, sc, (w0, h0) = _sample(video, n_frames)
    std = _motion_map(frames)
    found = [(q, "edge") for f in frames for q in _edge_quads(f)]
    motion = _motion_quads(std)
    diag = float(np.hypot(*frames[0].shape[:2]))
    clusters = []
    for q, src in found:
        for c in clusters:
            if np.linalg.norm(c["q"] - q, axis=1).mean() < 0.06 * diag:
                c["m"].append(q)
                c["n"] += 1
                c["q"] = np.mean(c["m"], axis=0)
                break
        else:
            clusters.append({"q": q, "m": [q], "n": 1})
    cands = []
    total = len(frames)
    # a moving blob that sits inside an edge-found screen is only part of that screen: it boosts it, not a rival
    contained = [[any(cv2.pointPolygonTest(c["q"].astype(np.float32), (float(x), float(y)), True) > -0.03 * diag for x, y in m)
                  for c in clusters] for m in motion]
    for c, ci in zip(clusters, range(len(clusters))):
        c["boost"] = any(row[ci] for row in contained)
    clusters += [{"q": m, "n": 3, "boost": False} for m, row in zip(motion, contained) if not any(row)]
    for c in clusters:
        q = c["q"]
        score = 0.45 * min(1.0, c["n"] / total) + 0.45 * _contrast(std, q) + (0.1 if c["boost"] else 0)
        cands.append({"quad": (q / sc).round(1).tolist(), "score": round(score, 3),
                      "area": round(_area(q) / (frames[0].shape[0] * frames[0].shape[1]), 3)})
    cands.sort(key=lambda d: -d["score"])
    cands = cands[:4]
    for i, d in enumerate(cands, 1):
        d["id"] = i
    if out_dir:
        _write_candidates(frames, sc, cands, Path(out_dir))
    return cands


def _write_candidates(frames, sc, cands, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    pick = [frames[int(i)] for i in np.linspace(0, len(frames) - 1, 6)]
    cols = [(0, 255, 0), (0, 200, 255), (255, 120, 0), (255, 0, 255)]
    tiles = []
    for f in pick:
        t = f.copy()
        for d in cands:
            q = (np.array(d["quad"]) * sc).astype(np.int32)
            col = cols[(d["id"] - 1) % 4]
            cv2.polylines(t, [q], True, col, 3)
            cv2.putText(t, str(d["id"]), tuple(int(v) for v in q[0] + 8), cv2.FONT_HERSHEY_SIMPLEX, 1.2, col, 3)
        tiles.append(cv2.resize(t, (400, int(400 * t.shape[0] / t.shape[1]))))
    h = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 0, cv2.BORDER_CONSTANT) for t in tiles]
    grid = np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:])])
    q = 85
    while True:
        ok, buf = cv2.imencode(".jpg", grid, [cv2.IMWRITE_JPEG_QUALITY, q])
        if len(buf) <= 1_500_000 or q <= 30:
            break
        q -= 15
    (out_dir / "screen_candidates.jpg").write_bytes(buf.tobytes())
    (out_dir / "screen_candidates.json").write_text(json.dumps({"candidates": cands}, indent=1), encoding="utf-8")


def pick_confident(cands):
    """Best candidate only when clearly best, else None."""
    if not cands or cands[0]["score"] < MIN_SCORE:
        return None
    if len(cands) > 1 and cands[0]["score"] - cands[1]["score"] < MARGIN:
        return None
    return cands[0]


def default_size(quad):
    q = np.array(quad, dtype=np.float32)
    w = (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2
    h = (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2
    return max(2, int(w) // 2 * 2), max(2, int(h) // 2 * 2)


def _tracked_quads(video, quad, n_total):
    """Per-frame quad via ORB homography against frame 0 (features outside the quad only). Returns list of
    (quad or None) per frame, first frame included."""
    cap = cv2.VideoCapture(str(video))
    orb = cv2.ORB_create(1500)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    q0 = np.array(quad, dtype=np.float32)
    ok, f0 = cap.read()
    g0 = cv2.cvtColor(f0, cv2.COLOR_BGR2GRAY)
    m = np.full(g0.shape, 255, np.uint8)
    cv2.fillPoly(m, [q0.astype(np.int32)], 0)
    m = cv2.erode(m, np.ones((15, 15), np.uint8))
    k0, d0 = orb.detectAndCompute(g0, m)
    diag = float(np.hypot(*g0.shape))
    res = [q0]
    while True:
        ok, f = cap.read()
        if not ok:
            break
        q = None
        try:
            k1, d1 = orb.detectAndCompute(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), None)
            if d0 is not None and d1 is not None and len(k0) >= 12:
                mt = sorted(bf.match(d0, d1), key=lambda x: x.distance)[:400]
                if len(mt) >= 12:
                    a = np.float32([k0[x.queryIdx].pt for x in mt]).reshape(-1, 1, 2)
                    b = np.float32([k1[x.trainIdx].pt for x in mt]).reshape(-1, 1, 2)
                    G, inl = cv2.findHomography(a, b, cv2.RANSAC, 3.0)
                    if G is not None and inl.sum() >= 12 and inl.mean() >= 0.3:
                        cand = cv2.perspectiveTransform(q0.reshape(-1, 1, 2), G).reshape(4, 2)
                        if np.linalg.norm(cand - q0, axis=1).max() < 0.25 * diag and cv2.isContourConvex(cand.astype(np.float32)):
                            q = cand
        except cv2.error:
            q = None
        res.append(q)
    cap.release()
    return res


def _smooth(qs, q0, win=5):
    filled = [q if q is not None else np.array(q0, dtype=np.float32) for q in qs]
    arr = np.stack(filled)
    out = np.empty_like(arr)
    h = win // 2
    for i in range(len(arr)):
        out[i] = arr[max(0, i - h):i + h + 1].mean(0)
    return out


def _encode_cmd(video, out_path, w, h, fps, audio_codec):
    return ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", f"{fps}",
            "-i", "-", "-i", str(video), "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "libx264", "-crf", "18",
            "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", audio_codec, "-shortest", "-movflags", "+faststart", str(out_path)]


def extract(video, quad, out_w=None, out_h=None, out_path="screen_content.mp4"):
    """Flat video of only the quad; audio kept. Resumable: an existing out_path + report is reused."""
    out_path = Path(out_path)
    rep_path = out_path.parent / "screen_crop.json"
    if out_path.exists() and out_path.stat().st_size > 0 and rep_path.exists():
        return json.loads(rep_path.read_text(encoding="utf-8"))
    quad = _order(quad)
    dw, dh = default_size(quad)
    w, h = int(out_w or dw) // 2 * 2, int(out_h or dh) // 2 * 2
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    tq = _tracked_quads(video, quad, n)
    sm = _smooth(tq, quad)
    dst = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    tmp = out_path.with_suffix(".part.mp4")
    for codec in ("copy", "aac"):
        cap = cv2.VideoCapture(str(video))
        p = subprocess.Popen(_encode_cmd(video, tmp, w, h, fps, codec), stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        i = 0
        try:
            while True:
                ok, f = cap.read()
                if not ok:
                    break
                M = cv2.getPerspectiveTransform(sm[min(i, len(sm) - 1)].astype(np.float32), dst)
                p.stdin.write(cv2.warpPerspective(f, M, (w, h), flags=cv2.INTER_CUBIC).tobytes())
                i += 1
            p.stdin.close()
        except BrokenPipeError:
            pass
        cap.release()
        err = p.stderr.read().decode(errors="replace")[-300:]
        if p.wait() == 0:
            break
        if codec == "aac":
            raise RuntimeError(f"ffmpeg failed: {err}")
    tmp.replace(out_path)
    ok_n = sum(1 for q in tq[1:] if q is not None)
    rep = {"quad": quad.round(1).tolist(), "tracked_fraction": round(ok_n / max(1, len(tq) - 1), 3),
           "out_w": w, "out_h": h, "frames": i, "fps": fps, "audio": "original", "file": out_path.name}
    rep_path.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def prepare(video, work_dir, crop=None):
    """Job entry. Returns (path_to_analyse, capture_dict, warning|None). Never raises: falls back to full frame."""
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    try:
        cand_file = work / "screen_candidates.json"
        if cand_file.exists():
            cands = json.loads(cand_file.read_text(encoding="utf-8"))["candidates"]
        else:
            cands = detect(video, work)
        if crop and crop.get("quad"):
            quad, w, h, how = crop["quad"], crop.get("out_w"), crop.get("out_h"), "given"
        else:
            c = pick_confident(cands)
            if c is None:
                return str(video), {"type": "screen_in_scene", "analysed": "full_frame", "quad": None}, "content_crop_needs_claude"
            quad, w, h, how = c["quad"], None, None, "auto"
        rep = extract(video, quad, w, h, work / "screen_content.mp4")
        return (str(work / "screen_content.mp4"),
                {"type": "screen_in_scene", "analysed": "inner_content", "quad": rep["quad"], "choice": how,
                 "tracked_fraction": rep["tracked_fraction"], "out": [rep["out_w"], rep["out_h"]]}, None)
    except Exception as e:  # noqa: BLE001
        return str(video), {"type": "screen_in_scene", "analysed": "full_frame", "quad": None}, f"content_crop_failed: {type(e).__name__}: {str(e)[:120]}"
