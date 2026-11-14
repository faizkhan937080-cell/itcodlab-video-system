"""Real 3D camera moves on a still (2.5D parallax, the documentary "3D photo" move). Free, CPU only.
1) depth map: Depth Anything V2 Small (Apache-2.0) via transformers, 2) Blender: the picture becomes a 3D relief
(near parts stand out), lit by its own colours (emission), 3) a camera flies through it (push / drift / rise / orbit).
Near things slide past far things, so it reads as a real 3D shot, not a flat zoom. ./run parallax ... (measured)."""
import json
import math
import time
from pathlib import Path

MOVES = {  # camera keys: (dolly as share of distance, x shift, y shift, roll deg) at start -> end
    "push": ((0.0, 0.00, 0.00, 0.0), (0.16, 0.00, 0.00, 0.0)),
    "push_drift": ((0.0, -0.03, 0.00, -0.6), (0.14, 0.03, 0.01, 0.6)),
    "rise": ((0.02, 0.00, -0.04, 0.0), (0.12, 0.00, 0.04, 0.0)),
    "orbit": ((0.04, -0.05, 0.00, -1.0), (0.10, 0.05, 0.00, 1.0)),
    "pull": ((0.16, 0.00, 0.00, 0.0), (0.02, 0.00, 0.00, 0.0)),
}


def depth_map(image_path, out_path):
    """Depth Anything V2 Small on CPU -> 16-bit PNG (white = near)."""
    import numpy as np
    from PIL import Image
    from transformers import pipeline
    pipe = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=-1)
    im = Image.open(image_path).convert("RGB")
    d = np.asarray(pipe(im)["predicted_depth"].squeeze().cpu().numpy(), dtype="float32")
    d = (d - d.min()) / max(1e-6, d.max() - d.min())
    Image.fromarray((d * 65535).astype("uint16")).resize(im.size, Image.BICUBIC).save(out_path)
    return out_path


def _smooth(d, k=9):
    """Soften depth edges so the relief does not tear at object borders."""
    from PIL import Image, ImageFilter
    import numpy as np
    im = Image.fromarray((d * 65535).astype("uint16")).convert("I;16")
    im = Image.fromarray((np.asarray(im, dtype="float32") / 65535 * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(k / 3))
    return np.asarray(im, dtype="float32") / 255.0


def build(bpy, image_path, depth_path, w, h, relief=0.22, grid=(180, 320), overscan=1.18):
    import numpy as np
    from PIL import Image
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    aspect = w / h
    gx, gy = grid
    dep = Image.open(depth_path)
    d = np.asarray(dep, dtype="float32")
    d = d / (65535.0 if d.max() > 255 else 255.0)
    d = _smooth(d)
    dsmall = np.asarray(Image.fromarray((d * 255).astype("uint8")).resize((gx + 1, gy + 1), Image.BILINEAR), dtype="float32") / 255.0
    verts, uvs, faces = [], [], []
    for j in range(gy + 1):
        for i in range(gx + 1):
            u, v = i / gx, 1 - j / gy
            z = relief * float(dsmall[j, i])
            # push near points toward the camera and shrink them back so the framing stays the same
            s = 1.0 - z / 2.2
            verts.append(((u - 0.5) * 2 * aspect * s * overscan, (v - 0.5) * 2 * s * overscan, z))  # overscan: edges never show
            uvs.append((u, v))
    for j in range(gy):
        for i in range(gx):
            a = j * (gx + 1) + i
            faces.append((a, a + 1, a + gx + 2, a + gx + 1))
    me = bpy.data.meshes.new("relief")
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="uv")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    ob = bpy.data.objects.new("relief", me)
    sc.collection.objects.link(ob)
    m = bpy.data.materials.new("pic")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(image_path))
    tex.extension = "EXTEND"
    em = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    me.materials.append(m)
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 50
    cam_d.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new("cam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    # distance that frames the full picture height at 50 mm (vertical sensor 24 mm)
    dist = 1.0 / math.tan(math.atan(12 / 50)) * 1.06
    w_ = bpy.data.worlds.new("w")
    sc.world = w_
    return sc, cam, dist


def animate(cam, dist, frames, move="push"):
    a, b = MOVES[move]
    for f, (dl, x, y, roll) in ((1, a), (frames, b)):
        cam.location = (x, y, dist * (1 - dl))
        cam.rotation_euler = (0, 0, math.radians(roll))
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)


def render_clip(image_path, depth_path, out_dir, seconds, move="push", w=1080, h=1920, fps=30, relief=0.22):
    """PNG frames f_0001.png.. in out_dir; returns timing report. The caller (script) encodes the mp4."""
    import bpy
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    frames = max(2, int(round(seconds * fps)))
    sc, cam, dist = build(bpy, image_path, depth_path, w, h, relief)
    animate(cam, dist, frames, move)
    r = sc.render
    r.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 1
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 0
    r.use_persistent_data = True
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
    r.fps = fps
    r.filter_size = 0.9
    sc.frame_start, sc.frame_end = 1, frames
    try:
        sc.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    r.image_settings.file_format = "PNG"
    r.filepath = str(out / "f_")
    t = time.time()
    bpy.ops.render.render(animation=True)
    rep = {"frames": frames, "w": w, "h": h, "move": move, "total_s": round(time.time() - t, 1),
           "sec_per_frame": round((time.time() - t) / frames, 3)}
    (out / "parallax_report.json").write_text(json.dumps(rep), encoding="utf-8")
    return rep
