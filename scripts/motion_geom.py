"""Tiny geometry for the motion-graphics QA gate: parts as boxes/spheres moved over time, no rendering.
Object space = three.js group space (y up). Pivots rotate about Z only (all current swings do)."""
import math

SAFE = {"sin": math.sin, "cos": math.cos, "exp": math.exp, "pi": math.pi, "sqrt": math.sqrt, "abs": abs,
        "min": min, "max": max, "pow": pow}


def _ease(x):
    return 1 - (1 - min(1, max(0, x))) ** 3


def _back(x):
    k = min(1, max(0, x))
    return 1 + 2.5 * (k - 1) ** 3 + 1.5 * (k - 1) ** 2


SAFE.update(ease=_ease, back=_back, clamp=lambda x, a=0, b=1: max(a, min(b, x)))


def ev(expr, t, vars_=None):
    """Evaluate a spec expression of t (and earlier named vars). Numbers pass through."""
    if isinstance(expr, (int, float)):
        return float(expr)
    env = dict(SAFE, t=t)
    for k, v in (vars_ or {}).items():
        env[k] = eval(v, {"__builtins__": {}}, env) if isinstance(v, str) else v
    return float(eval(expr, {"__builtins__": {}}, env))


def _rz(x, y, a):
    c, s = math.cos(a), math.sin(a)
    return x * c - y * s, x * s + y * c


def part_box(part, spec, t):
    """-> (cx, cy, cz, hx, hy, hz, ang): object-space centre, AABB half sizes and z-rotation of one part at time t."""
    d = part["dims"]
    hx, hy, hz = d[0] / 2, d[1] / 2, d[2] / 2
    ang = part.get("rotz", 0.0)
    cx, cy, cz = part["pos"]
    pv = spec.get("pivot")
    if part.get("pivot") and pv:
        a = ev(pv["rot"], t, pv.get("vars"))
        cx, cy = _rz(cx, cy, a)
        cx += pv["pos"][0]
        cy += pv["pos"][1] + ev(pv.get("dy", 0), t, pv.get("vars"))
        cz += pv["pos"][2]
        ang += a
    if part["shape"] not in ("sphere", "round_xy") and ang:
        c, s = abs(math.cos(ang)), abs(math.sin(ang))
        hx, hy = c * hx + s * hy, s * hx + c * hy     # exact for boxes and for cylinders seen in the xy plane
    r = spec.get("root", [0, 0, 0])
    return cx + r[0], cy + r[1], cz + r[2], hx, hy, hz, ang


def corners(part, spec, t):
    """8 box corners (26 directions for a sphere) in object space, for camera projection."""
    cx, cy, cz, _, _, _, ang = part_box(part, spec, t)
    d = part["dims"]
    hx, hy, hz = d[0] / 2, d[1] / 2, d[2] / 2
    if part["shape"] in ("sphere", "round_xy"):
        pts = []
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for k in (-1, 0, 1):
                    n = math.sqrt(i * i + j * j + k * k)
                    if n:
                        pts.append((cx + hx * i / n, cy + hy * j / n, cz + hz * k / n))
        return pts
    if part["shape"] == "cyl":     # upright round cylinder: 12-point rings at top and bottom (a box would add phantom corners)
        out = []
        for j in (-1, 1):
            for n in range(12):
                a = 2 * math.pi * n / 12
                x, y = _rz(hx * math.cos(a), j * hy, ang)
                out.append((cx + x, cy + y, cz + hz * math.sin(a)))
        return out
    out = []
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                x, y = _rz(i * hx, j * hy, ang)
                out.append((cx + x, cy + y, cz + k * hz))
    return out


def project(pt, pose, sc, vw, vh, cam=(0.0, 0.9, 5.0), fov=30.0):
    """Object point -> pixel in the card canvas (vw x vh). pose = (tilt, yaw, bob). Mirrors PotterScene ObjLayer."""
    tilt, yaw, bob = pose
    x, y, z = (pt[0] * sc, pt[1] * sc, pt[2] * sc)
    x, z = x * math.cos(yaw) + z * math.sin(yaw), -x * math.sin(yaw) + z * math.cos(yaw)       # Ry
    y, z = y * math.cos(tilt) - z * math.sin(tilt), y * math.sin(tilt) + z * math.cos(tilt)    # Rx
    y += bob
    dx, dy, dz = x - cam[0], y - cam[1], z - cam[2]
    n = math.sqrt(cam[0] ** 2 + cam[1] ** 2 + cam[2] ** 2)
    zc = (cam[0] / n, cam[1] / n, cam[2] / n)                      # camera looks at the origin
    xc = (zc[2], 0.0, -zc[0])
    ln = math.hypot(xc[0], xc[2]) or 1.0
    xc = (xc[0] / ln, 0.0, xc[2] / ln)
    yc = (zc[1] * xc[2] - zc[2] * xc[1], zc[2] * xc[0] - zc[0] * xc[2], zc[0] * xc[1] - zc[1] * xc[0])
    vx, vy, vz = (dx * xc[0] + dz * xc[2], dx * yc[0] + dy * yc[1] + dz * yc[2], dx * zc[0] + dy * zc[1] + dz * zc[2])
    th = math.tan(math.radians(fov) / 2)
    nx, ny = (vx / -vz) / (th * vw / vh), (vy / -vz) / th
    return (nx + 1) / 2 * vw, (1 - ny) / 2 * vh
