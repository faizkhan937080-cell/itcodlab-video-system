"""Group similar scenes so the collage shows each look only once.
Nothing is deleted: removed scenes stay in scenes.json and in the cluster map.
"""
import numpy as np
from skimage.metrics import structural_similarity

from .analyze import hamming_hex


def _similar(a, b, ham_max, ssim_min):
    if hamming_hex(a["phash"], b["phash"]) > ham_max:
        return False
    return structural_similarity(a["_thumb"], b["_thumb"], data_range=255) >= ssim_min


def cluster_scenes(scenes, ham_max, ssim_min):
    clusters = []  # each: {"rep": scene, "members": [scene,...]}
    for sc in scenes:
        if not sc.get("phash"):
            continue
        for c in clusters:
            if _similar(sc, c["rep"], ham_max, ssim_min):
                c["members"].append(sc)
                break
        else:
            clusters.append({"rep": sc, "members": [sc]})
    return clusters


def dedup(scenes, capacity, lim):
    """Cluster scenes; relax thresholds until the unique count fits `capacity` frames.
    Returns (clusters_json, report)."""
    d = lim["dedup"]
    ham, ssim = d["phash_hamming_max_start"], d["ssim_min_start"]
    rounds = 0
    clusters = cluster_scenes(scenes, ham, ssim)
    while len(clusters) > capacity and rounds < d["relax_max_rounds"]:
        ham += d["relax_phash_step"]
        ssim = max(0.2, ssim - d["relax_ssim_step"])
        clusters = cluster_scenes(scenes, ham, ssim)
        rounds += 1
    dropped = []
    if len(clusters) > capacity:
        # still too many: keep an evenly spaced subset in the collage, keep all in metrics
        keep_idx = set(np.linspace(0, len(clusters) - 1, capacity).round().astype(int).tolist())
        dropped = [c["rep"]["id"] for i, c in enumerate(clusters) if i not in keep_idx]
        for i, c in enumerate(clusters):
            c["collage"] = i in keep_idx
    else:
        for c in clusters:
            c["collage"] = True
    out = []
    for n, c in enumerate(clusters, start=1):
        for m in c["members"]:
            m["cluster"] = n
        out.append({
            "cluster": n, "rep_scene": c["rep"]["id"],
            "members": [m["id"] for m in c["members"]], "count": len(c["members"]),
            "total_duration_s": round(sum(m["duration_s"] for m in c["members"]), 3),
            "in_collage": c["collage"],
        })
    report = {"phash_hamming_max": ham, "ssim_min": round(ssim, 3), "relax_rounds": rounds,
              "scenes_total": len(scenes), "clusters": len(out), "capacity": capacity,
              "scenes_not_in_collage_clusters": dropped}
    return out, report
