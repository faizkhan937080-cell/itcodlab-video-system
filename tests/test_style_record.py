"""Style record must separate events even when something on the page always moves (like the heysansser reel)."""
import cv2
import numpy as np

from scripts import style_record

CARD_TIMES = [2.0, 6.0, 10.0, 14.0, 18.0, 22.0]


def _reel(path, seconds=26, fps=24):
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (270, 480))
    for i in range(seconds * fps):
        t = i / fps
        fr = np.full((480, 270), 246, np.uint8)
        fr = cv2.cvtColor(fr, cv2.COLOR_GRAY2BGR)
        x = int(20 + (t * 14) % 230)                      # a timeline dot that never stops
        cv2.circle(fr, (x, 440), 6, (60, 60, 60), -1)
        cv2.line(fr, (20, 440), (250, 440), (200, 200, 200), 2)
        bx = int((t * 30) % 200)                           # a ticker bar sweeping all the time: the page is never quiet
        cv2.rectangle(fr, (bx, 20), (bx + 30, 70), (150, 150, 150), -1)
        for k, t0 in enumerate(CARD_TIMES):
            if t >= t0:
                p = min(1.0, (t - t0) / 0.5)             # card slides up in 0.5 s, then stays
                y = int(380 - 120 * (1 - (1 - p) ** 2)) - 60 * (k % 3)
                cv2.rectangle(fr, (30, y), (240, y + 40), (255, 255, 255), -1)
                cv2.rectangle(fr, (30, y), (240, y + 40), (120, 120, 120), 2)
        w.write(fr)
    w.release()


def test_events_found_despite_constant_drift(tmp_path):
    v = tmp_path / "reel.mp4"
    _reel(v)
    rec = style_record.build(v, tmp_path / "out", with_ocr=False)
    assert rec["event_count"] >= 5, rec["events"]
    starts = [e["t_in"] for e in rec["events"]]
    for t0 in CARD_TIMES:
        assert any(abs(s - t0) < 1.0 for s in starts), (t0, starts)
    assert (tmp_path / "out" / "activity.json").exists()
