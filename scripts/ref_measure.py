"""Reference measured at 30 fps (point 7). Faiz's source video: "if you only ask Claude to analyse a video it grabs a few frames;
watch every frame at 30 fps, MEASURE, never opine". Output = numbers only (small JSON), worker job:
  per second: brightness, contrast, saturation, camera shift (px/frame at 160 px long edge, phase correlation)
  overall: hard cuts, share of moving frames, dark floor (1st percentile; no pure black = premium look), p10/p90 brightness,
  camera classes (still / slow / medium / fast) using the same thresholds as the analysis (config analysis.motion_classes_flow_px).
Slow pushes are visible only through the shift numbers (their note: a tool that missed 65 % slow moves said 'camera is still')."""
import cv2
import numpy as np

from .common import limits

LONG_EDGE = 160
CUT_CORR = 0.5     # histogram correlation under this between neighbours = hard cut


def _small(fr):
    h, w = fr.shape[:2]
    k = LONG_EDGE / max(h, w)
    return cv2.resize(fr, (max(8, int(w * k)), max(8, int(h * k))), interpolation=cv2.INTER_AREA) if k < 1 else fr


def _hist(gray):
    h = cv2.calcHist([gray], [0], None, [32], [0, 256])
    return cv2.normalize(h, h).flatten()


def measure(video, fps_target=30.0, max_s=None):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or fps_target
    step = max(1, int(round(fps / fps_target)))
    prev_g, prev_h, i = None, None, 0
    sec = {}
    cuts, shifts, darks, shifts_all = [], [], [], []
    while True:
        ok, fr = cap.read()
        if not ok or (max_s and i / fps > max_s):
            break
        if i % step == 0:
            sm = _small(fr)
            g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(sm, cv2.COLOR_BGR2HSV)
            t = int(i / fps)
            row = sec.setdefault(t, {"b": [], "c": [], "s": [], "m": []})
            row["b"].append(float(g.mean()))
            row["c"].append(float(g.std()))
            row["s"].append(float(hsv[..., 1].mean()))
            darks.append(float(np.percentile(g, 1)))
            hh = _hist(g)
            if prev_g is not None:
                (dx, dy), _ = cv2.phaseCorrelate(np.float32(prev_g), np.float32(g))
                mag = float(np.hypot(dx, dy))
                row["m"].append(mag)
                shifts_all.append(mag)
                if cv2.compareHist(prev_h, hh, cv2.HISTCMP_CORREL) < CUT_CORR:
                    cuts.append(round(i / fps, 2))
            prev_g, prev_h = g, hh
        i += 1
    cap.release()
    classes = limits().get("analysis", {}).get("motion_classes_flow_px", {"static": 0.15, "slow": 0.6, "medium": 1.6})
    still, slow, med = classes["static"], classes["slow"], classes["medium"]
    per_s = [{"t": t, "brightness": round(float(np.mean(r["b"])), 1), "contrast": round(float(np.mean(r["c"])), 1),
              "saturation": round(float(np.mean(r["s"])), 1), "camera_px": round(float(np.mean(r["m"])), 3) if r["m"] else 0.0}
             for t, r in sorted(sec.items())]
    sh = np.array(shifts_all) if shifts_all else np.zeros(1)
    bright = [r["brightness"] for r in per_s] or [0]
    return {"fps_measured": fps_target, "frames": len(shifts_all) + 1, "duration_s": round(i / fps, 2), "hard_cuts": cuts,
            "cuts_per_min": round(len(cuts) / max(i / fps / 60, 1e-9), 1),
            "camera": {"still_pct": round(float((sh < still).mean() * 100), 1), "slow_pct": round(float(((sh >= still) & (sh < slow)).mean() * 100), 1),
                       "medium_pct": round(float(((sh >= slow) & (sh < med)).mean() * 100), 1), "fast_pct": round(float((sh >= med).mean() * 100), 1),
                       "moving_pct": round(float((sh >= still).mean() * 100), 1)},
            "dark_floor_p1": round(float(np.mean(darks)) if darks else 0.0, 1),
            "brightness": {"mean": round(float(np.mean(bright)), 1), "p10": round(float(np.percentile(bright, 10)), 1),
                           "p90": round(float(np.percentile(bright, 90)), 1)},
            "contrast_mean": round(float(np.mean([r["contrast"] for r in per_s] or [0])), 1),
            "saturation_mean": round(float(np.mean([r["saturation"] for r in per_s] or [0])), 1), "per_second": per_s}
