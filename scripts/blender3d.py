"""Free photoreal 3D plates with Blender (bpy, Cycles CPU). No downloaded models: everything is procedural.

First look: `organic_tunnel` = macro inside-the-body tunnel (wet tissue, veins, cilia hairs, mucus drops, air wisps,
dust), slow push-in, shallow depth of field. Matches the warm macro-anatomy look of ref reel-Dfm-f2iDcKc.
Run only through `./run blender ...` (measured with stage()).
"""
import json
import math
import random
import time
from pathlib import Path

LOOKS = {
    # numbers measured from ref reel-Dfm-f2iDcKc metrics_summary (palette, brightness 0.375, saturation 0.44)
    "warm_tissue": {"base": "#B86A62", "dark": "#8A4842", "light": "#DA978C", "vein": "#9A3A36",
                    "hair": "#E8C8B8", "wisp": "#DCE4F0", "dust": "#B89A78", "world": "#120706"},
}


def _rgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def _centre(t):
    """Gently curving centre line of the tunnel, t in metres along the passage."""
    return (0.35 * math.sin(t * 0.55), t, 0.25 * math.sin(t * 0.8 + 1.0))


def _tunnel_mesh(bpy, length=14.0, rings=180, seg=96, seed=7):
    import bmesh
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6.28) for _ in range(8)]
    me = bpy.data.meshes.new("tunnel")
    bm = bmesh.new()
    grid = []
    for i in range(rings):
        t = length * i / (rings - 1)
        cx, cy, cz = _centre(t)
        row = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            # folds: lengthwise ridges + slow bulges, like turbinates
            r = 1.0 + 0.28 * math.sin(3 * a + ph[0] + 0.6 * t) + 0.12 * math.sin(5 * a + ph[1] - 0.3 * t) \
                + 0.18 * math.sin(0.9 * t + ph[2]) * math.cos(2 * a + ph[3]) 
            r *= 1.0 + 0.25 * math.sin(0.35 * t + ph[4])
            row.append(bm.verts.new((cx + r * math.cos(a), cy, cz + r * math.sin(a))))
        grid.append(row)
    for i in range(rings - 1):
        for j in range(seg):
            k = (j + 1) % seg
            bm.faces.new((grid[i][j], grid[i][k], grid[i + 1][k], grid[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # normals point inward, camera is inside
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return bpy.data.objects.new("tunnel", me)


def _tissue_material(bpy, look):
    m = bpy.data.materials.new("wet_tissue")
    m.use_nodes = True
    nt = m.node_tree
    n, ln = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord")
    big = n.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 1.6; big.inputs["Detail"].default_value = 6
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = _rgb(look["dark"]); ramp.color_ramp.elements[1].color = _rgb(look["light"])
    mid = ramp.color_ramp.elements.new(0.5); mid.color = _rgb(look["base"])
    ln.new(tc.outputs["Object"], big.inputs["Vector"]); ln.new(big.outputs["Fac"], ramp.inputs["Fac"])
    # veins: thin voronoi edges, darker red
    vor = n.new("ShaderNodeTexVoronoi"); vor.feature = "DISTANCE_TO_EDGE"; vor.inputs["Scale"].default_value = 5.0
    vr = n.new("ShaderNodeMapRange"); vr.inputs["From Min"].default_value = 0.0; vr.inputs["From Max"].default_value = 0.02
    vr.inputs["To Min"].default_value = 0.3; vr.inputs["To Max"].default_value = 0.0
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["B"].default_value = _rgb(look["vein"])
    warp = n.new("ShaderNodeTexNoise"); warp.inputs["Scale"].default_value = 3.0
    wmix = n.new("ShaderNodeMix"); wmix.data_type = "VECTOR"; wmix.inputs["Factor"].default_value = 0.35
    ln.new(tc.outputs["Object"], wmix.inputs["A"]); ln.new(warp.outputs["Color"], wmix.inputs["B"])
    ln.new(tc.outputs["Object"], warp.inputs["Vector"])
    ln.new(wmix.outputs["Result"], vor.inputs["Vector"]); ln.new(vor.outputs["Distance"], vr.inputs["Value"])
    ln.new(vr.outputs["Result"], mix.inputs["Factor"]); ln.new(ramp.outputs["Color"], mix.inputs["A"])
    ln.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.42
    bsdf.inputs["Subsurface Weight"].default_value = 0.35
    bsdf.inputs["Subsurface Radius"].default_value = (0.9, 0.25, 0.15)
    bsdf.inputs["Subsurface Scale"].default_value = 0.08
    bsdf.inputs["Coat Weight"].default_value = 1.0      # wet mucus film
    bsdf.inputs["Coat Roughness"].default_value = 0.05
    # fine bumps + wet ripples
    fine = n.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 60; fine.inputs["Detail"].default_value = 8
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15; bump.inputs["Distance"].default_value = 0.02
    ln.new(tc.outputs["Object"], fine.inputs["Vector"]); ln.new(fine.outputs["Fac"], bump.inputs["Height"])
    ln.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    wet = n.new("ShaderNodeTexNoise"); wet.inputs["Scale"].default_value = 22; wet.inputs["Distortion"].default_value = 0.8
    cb = n.new("ShaderNodeBump"); cb.inputs["Strength"].default_value = 0.12
    ln.new(tc.outputs["Object"], wet.inputs["Vector"]); ln.new(wet.outputs["Fac"], cb.inputs["Height"])
    ln.new(cb.outputs["Normal"], bsdf.inputs["Coat Normal"])
    return m


def _simple_mat(bpy, name, colour, rough=0.4, transmission=0.0, emission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = _rgb(colour)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Transmission Weight"].default_value = transmission
    if transmission:
        b.inputs["IOR"].default_value = 1.34
    return m


def _scatter(bpy, obj, count, seed):
    """Random points on the tunnel wall (world space) with their normals."""
    rnd = random.Random(seed)
    me = obj.data
    polys = list(me.polygons)
    out = []
    for _ in range(count):
        p = polys[rnd.randrange(len(polys))]
        out.append((obj.matrix_world @ p.center, p.normal.copy()))
    return out


def build_organic_tunnel(bpy, look="warm_tissue", seed=7, hair=6000, drops=60, dust=40):
    look = LOOKS[look]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    tun = _tunnel_mesh(bpy, seed=seed)
    sc.collection.objects.link(tun)
    sub = tun.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 2
    tex = bpy.data.textures.new("folds", "CLOUDS"); tex.noise_scale = 0.6
    dis = tun.modifiers.new("disp", "DISPLACE"); dis.texture = tex; dis.strength = -0.08; dis.texture_coords = "OBJECT"
    tun.data.materials.append(_tissue_material(bpy, look))
    # cilia hairs
    ps = tun.modifiers.new("cilia", "PARTICLE_SYSTEM").particle_system
    st = ps.settings
    st.type = "HAIR"; st.count = hair; st.hair_length = 0.07; st.use_advanced_hair = True
    st.use_rotations = True; st.rotation_mode = "NOR"
    st.child_type = "INTERPOLATED"; st.rendered_child_count = 6; st.child_parting_factor = 0.2
    st.root_radius = 0.006; st.tip_radius = 0.0005
    st.material = 2
    tun.data.materials.append(_simple_mat(bpy, "hair", look["hair"], rough=0.35))
    ps.seed = seed
    # mucus drops
    dmat = _simple_mat(bpy, "mucus", "#F4E6E0", rough=0.03, transmission=1.0)
    for i, (co, nrm) in enumerate(_scatter(bpy, tun, drops, seed + 1)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=random.Random(i).uniform(0.012, 0.045), location=co - nrm * 0.01,
                                             segments=24, ring_count=12)
        o = bpy.context.object; o.scale = (1, 1, 0.55); o.data.materials.append(dmat)
        for p in o.data.polygons:
            p.use_smooth = True
    # dust specks floating in the air
    dmat2 = _simple_mat(bpy, "dust", look["dust"], rough=0.9)
    rnd = random.Random(seed + 2)
    for i in range(dust):
        t = rnd.uniform(2.6, 8.0)
        cx, cy, cz = _centre(t)
        bpy.ops.mesh.primitive_ico_sphere_add(radius=rnd.uniform(0.003, 0.009), subdivisions=2,
                                              location=(cx + rnd.uniform(-0.6, 0.6), cy, cz + rnd.uniform(-0.5, 0.5)))
        o = bpy.context.object; o.data.materials.append(dmat2)
        o.scale = (rnd.uniform(0.6, 1.4), rnd.uniform(0.6, 1.4), rnd.uniform(0.6, 1.4))
    # air wisps: thin volume along the passage
    bpy.ops.mesh.primitive_cube_add(size=1, location=_centre(5.0))
    vol = bpy.context.object; vol.scale = (1.4, 10.0, 1.2)
    vm = bpy.data.materials.new("air"); vm.use_nodes = True
    nt = vm.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    pv = nt.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = _rgb(look["wisp"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.5; nz.inputs["Detail"].default_value = 4
    nz.inputs["Distortion"].default_value = 3.0
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.5, 0.35, 2.5)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs["From Min"].default_value = 0.66; rr.inputs["From Max"].default_value = 0.8
    rr.inputs["To Max"].default_value = 1.6
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], pv.inputs["Density"])
    nt.links.new(pv.outputs["Volume"], nt.nodes["Material Output"].inputs["Volume"])
    vol.data.materials.append(vm)
    # wisps drift forward
    nz.noise_dimensions = "4D"
    nz.inputs["W"].default_value = 0.0
    nz.inputs["W"].keyframe_insert("default_value", frame=1)
    nz.inputs["W"].default_value = 0.6
    nz.inputs["W"].keyframe_insert("default_value", frame=300)
    # camera with endoscope-like light
    cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 22; cam_d.dof.use_dof = True
    cam_d.dof.focus_distance = 1.1; cam_d.dof.aperture_fstop = 5.6
    cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    l1 = bpy.data.lights.new("key", "POINT"); l1.energy = 70; l1.shadow_soft_size = 0.06; l1.color = (1.0, 0.92, 0.86)
    lo = bpy.data.objects.new("key", l1); sc.collection.objects.link(lo); lo.parent = cam; lo.location = (0.25, 0.3, 0)
    l2 = bpy.data.lights.new("deep", "POINT"); l2.energy = 6; l2.shadow_soft_size = 1.5; l2.color = (1.0, 0.75, 0.7)
    do = bpy.data.objects.new("deep", l2); sc.collection.objects.link(do); do.location = _centre(5.5)
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = _rgb(look["world"])
    return sc, cam


def animate_push(bpy, cam, frames, t0=0.4, t1=2.2):
    """Slow push-in along the passage (measured ref: 'slow' camera, zoom in)."""
    for f, t in ((1, t0), (frames, t1)):
        cx, cy, cz = _centre(t)
        nx, ny, nz = _centre(t + 1.0)
        cam.location = (cx, cy, cz)
        d = (nx - cx, ny - cy, nz - cz)
        # point camera down the tunnel (camera looks along -Z local)
        yaw = math.atan2(-d[0], d[1])
        pitch = math.atan2(d[2], math.hypot(d[0], d[1]))
        cam.rotation_euler = (math.pi / 2 + pitch, 0, yaw + 0.04 * (f > 1))
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    for fc in cam.animation_data.action.fcurves if hasattr(cam.animation_data.action, "fcurves") else []:
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"


def setup_render(bpy, sc, out_dir, w, h, fps, frames, samples):
    r = sc.render
    r.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 4; sc.cycles.volume_bounces = 0
    sc.cycles.volume_step_rate = 8.0; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.05
    r.use_persistent_data = True
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
    r.fps = fps
    sc.frame_start, sc.frame_end = 1, frames
    r.image_settings.file_format = "PNG"
    r.filepath = str(Path(out_dir) / "f_")
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Base Contrast"; sc.view_settings.exposure = 0.6
    except TypeError:
        pass


def render_sample(out_dir, seconds=5.0, w=540, h=960, fps=30, samples=24, only_frames=None, seed=7):
    import bpy
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    frames = int(round(seconds * fps))
    sc, cam = build_organic_tunnel(bpy, seed=seed)
    animate_push(bpy, cam, frames)
    setup_render(bpy, sc, out, w, h, fps, frames, samples)
    t = time.time()
    todo = only_frames or range(1, frames + 1)
    per = []
    for f in todo:
        s = time.time()
        sc.frame_set(f)
        sc.render.filepath = str(out / f"f_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        per.append(round(time.time() - s, 2))
    rep = {"frames": len(per), "of": frames, "w": w, "h": h, "fps": fps, "samples": samples,
           "sec_per_frame": round(sum(per) / len(per), 2), "total_s": round(time.time() - t, 1), "per_frame": per}
    (out / "render_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def contact_sheet(out_dir, max_tiles=6, tile_w=400):
    """Collage of rendered frames (what Claude looks at; never single raw frames)."""
    from PIL import Image, ImageDraw
    fs = sorted(Path(out_dir).glob("f_*.png"))
    if len(fs) > max_tiles:
        step = (len(fs) - 1) / (max_tiles - 1)
        fs = [fs[round(i * step)] for i in range(max_tiles)]
    ims = [Image.open(f).convert("RGB") for f in fs]
    th = round(ims[0].height * tile_w / ims[0].width)
    sheet = Image.new("RGB", (tile_w * len(ims), th), "black")
    for i, (f, im) in enumerate(zip(fs, ims)):
        sheet.paste(im.resize((tile_w, th)), (i * tile_w, 0))
        ImageDraw.Draw(sheet).text((i * tile_w + 6, 6), f.stem, fill="white")
    p = Path(out_dir) / "collage.jpg"
    sheet.save(p, quality=88)
    return str(p)
