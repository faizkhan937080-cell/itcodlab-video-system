"""Tools inventory: everything we already own, in about twenty lines. Read BEFORE choosing how to build anything.
Rule: a plan that skips an owned tool must say why (never a silent shortcut like zoom on stills for "3D motion graphics")."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _json(p):
    try:
        return json.loads((ROOT / p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def facts():
    pk = _json("remotion/package.json") or {}
    deps = sorted(k for k in {**pk.get("dependencies", {}), **pk.get("devDependencies", {})} if k.startswith("@remotion/") or k in ("three", "lottie-web", "@react-three/fiber"))
    reg = _json("remotion/src/ext/REGISTRY.json") or {}
    skills = sorted(p.name for p in (ROOT / "remotion" / "vendor-skills").glob("remotion-*")) if (ROOT / "remotion" / "vendor-skills").exists() else []
    vg = (ROOT / "scripts" / "videogen.py").read_text(encoding="utf-8", errors="ignore")
    models = re.findall(r'"(\w+)": "([\w./-]+)"', vg.split("MODEL =")[1].split("\n")[0]) if "MODEL =" in vg else []
    secrets = sorted({m for f in (ROOT / ".github" / "workflows").glob("*.yml") for m in re.findall(r"secrets\.([A-Z0-9_]+)", f.read_text(encoding="utf-8"))} - {"GITHUB_TOKEN"})
    health = _json("work/health.json")
    return {"remotion_packages": deps, "ext_components": sorted(reg), "remotion_skills": skills,
            "three_in_remotion": "@remotion/three" in deps, "ai_video_models": dict(models) | {"minimax": "MiniMaxAI/MiniMax-H3 (needs Faiz Y)"},
            "own_3d": ["Blender bpy (scripts/blender3d.py, Cycles CPU)", "parallax = camera move on a STILL (NOT motion graphics)"],
            "runners": ["GitHub Actions (free)", "Modal L40S (free credit; scripts/modal_app.py)", "Kaggle GPU (queue can stall)"],
            "secret_names": secrets, "health": health}


def render(f=None):
    f = f or facts()
    L = ["TOOLS WE OWN (use these first; skipping one needs a stated reason):",
         "remotion: " + ", ".join(f["remotion_packages"]),
         "  3D inside Remotion (@remotion/three): " + ("yes" if f["three_in_remotion"] else "NOT installed (add before building 3D scenes)"),
         "  outside components: " + ", ".join(f["ext_components"]),
         "  official skills: " + ", ".join(f["remotion_skills"]),
         "AI video models (real moving footage): " + "; ".join(f"{k}={v}" for k, v in f["ai_video_models"].items()),
         "3D: " + " | ".join(f["own_3d"]),
         "runners: " + " | ".join(f["runners"]),
         "secret names used by workflows (a name here is not proof the value is set or right): " + ", ".join(f["secret_names"])]
    if f["health"]:
        L.append("health today: " + ", ".join(f"{k}={'OK' if v.get('ok') else 'DOWN'}" if isinstance(v, dict) else f"{k}={v}" for k, v in f["health"].items()))
    L.append("Zoom/pan on stills is NOT 3D motion graphics. Say so before using it.")
    return "\n".join(L)
