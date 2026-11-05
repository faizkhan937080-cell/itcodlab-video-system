"""Creator-level DNA from MANY videos (e.g. 50): what is the creator's signature, what is only situational.

Input: v2 DNA dicts of ONE type for ONE creator (one per analysed video).
Output (schema dna-corpus): per-field statistics, `signature` (stable across videos = clone these) and
`situational` (varies = depends on the topic; do not copy blindly), plus `targets` = the value to aim for per
signature field (median for numbers, mode for words, items most videos share for lists).
Fewer than MIN_STABLE videos -> provisional: usable, but say so. Nothing is averaged blindly: a field is a
signature only when most videos agree (low spread / high agreement).
"""
import statistics as st
from collections import Counter

MIN_STABLE = 10
SKIP = {"type", "schema_version", "source", "evidence", "confidence", "corpus", "notes"}
NAME_KEYS = ("beat", "type", "hex", "part")
CV_MAX, MODE_MIN, ITEM_MIN, COVER_MIN = 0.25, 0.6, 0.5, 0.6


def flatten(node, path="", out=None):
    out = {} if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            if not path and k in SKIP:
                continue
            flatten(v, f"{path}.{k}" if path else k, out)
    elif isinstance(node, bool):
        out[path] = node
    elif isinstance(node, (int, float)):
        out[path] = float(node)
    elif isinstance(node, str):
        if len(node) <= 60:
            out[path] = node
    elif isinstance(node, list):
        if all(isinstance(x, str) for x in node) and node:
            out[path] = sorted({x.strip().lower() for x in node if x.strip()})
        elif all(isinstance(x, dict) for x in node):
            for i, x in enumerate(node):
                key = next((x[nk] for nk in NAME_KEYS if isinstance(x.get(nk), str)), None)
                flatten(x, f"{path}[{key if key is not None else i}]", out)
    return out


def _pct(vals, q):
    s = sorted(vals)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def aggregate(dna_type, creator, dnas, job_ids=None):
    flats = [flatten(d) for d in dnas]
    n = len(dnas)
    paths = sorted({p for f in flats for p in f})
    fields, signature, situational, targets = {}, [], [], {}
    for p in paths:
        vals = [f[p] for f in flats if p in f]
        cover = len(vals) / n
        kind = vals[0]
        if all(isinstance(v, bool) for v in vals):
            c = Counter(vals)
            mode, cnt = c.most_common(1)[0]
            fields[p] = {"kind": "bool", "n": len(vals), "mode": mode, "agreement": round(cnt / len(vals), 3)}
            ok, tgt = cnt / len(vals) >= MODE_MIN, mode
        elif all(isinstance(v, float) for v in vals):
            med = st.median(vals)
            q1, q3 = _pct(vals, 0.25), _pct(vals, 0.75)
            sd = st.pstdev(vals) if len(vals) > 1 else 0.0
            cv = (sd / abs(st.mean(vals))) if st.mean(vals) else 0.0
            fields[p] = {"kind": "number", "n": len(vals), "median": round(med, 3), "mean": round(st.mean(vals), 3),
                         "p25": round(q1, 3), "p75": round(q3, 3), "min": round(min(vals), 3),
                         "max": round(max(vals), 3), "cv": round(cv, 3)}
            ok, tgt = cv <= CV_MAX, round(med, 3)
        elif all(isinstance(v, str) for v in vals):
            c = Counter(v.lower() for v in vals)
            mode, cnt = c.most_common(1)[0]
            fields[p] = {"kind": "word", "n": len(vals), "mode": mode, "agreement": round(cnt / len(vals), 3),
                         "top": c.most_common(5)}
            ok, tgt = cnt / len(vals) >= MODE_MIN, mode
        elif all(isinstance(v, list) for v in vals):
            c = Counter(i for v in vals for i in v)
            top = [(i, round(k / len(vals), 3)) for i, k in c.most_common(10)]
            fields[p] = {"kind": "items", "n": len(vals), "top": top}
            common = [i for i, sh in top if sh >= ITEM_MIN]
            ok, tgt = bool(common), common
        else:
            continue
        ok = ok and cover >= COVER_MIN
        fields[p]["coverage"] = round(cover, 3)
        (signature if ok else situational).append(p)
        if ok:
            targets[p] = tgt
    return {"type": "corpus", "schema_version": 2, "dna_type": dna_type, "creator": creator, "n_videos": n,
            "job_ids": job_ids or [d.get("source", {}).get("job_id", f"v{i}") for i, d in enumerate(dnas)],
            "fields": fields, "signature": signature, "situational": situational, "targets": targets,
            "provisional": n < MIN_STABLE, "min_videos_stable": MIN_STABLE}
