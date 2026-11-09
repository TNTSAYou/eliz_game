"""Build the Elizabeth "mascot costume" v2 (docs/character_spec_v2.md).

Run (PowerShell):
    & "D:\\tools\\blender-4.5.15-windows-x64\\blender.exe" --background --factory-startup `
        --python-exit-code 1 --python "D:\\work\\eliz_game\\scripts\\build_eliz_v2.py"

Outputs (all under art/):
    blender/eliz_costume_v2.blend
    exports/eliz_costume_v2.glb
    renders/v2_*.png

Conventions: meters, Z up, character faces -Y, feet on Z=0.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Quaternion, Vector, noise

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "art"
BLENDS = ART / "blender"
EXPORTS = ART / "exports"
RENDERS = ART / "renders"
TEX = ART / "textures"

FPS = 30

# --------------------------------------------------------------------------
# Dimensions (spec v2 section 4/5)
# --------------------------------------------------------------------------
TOTAL_H = 1.80

HEM_Z = 0.02             # hem height (v3: robe reaches the floor)
HEM_FLARE = 1.02
BODY_R = 0.437           # half width -> 0.874 (measured: 141 px)
DEPTH_RATIO = 0.82
DOME_Z0 = 1.10           # soft shoulder: continuous egg profile from here to the top
DOME_H = TOTAL_H - DOME_Z0
DOME_P = 0.42
WALL_MIN = 0.024         # fabric thickness at the hem edge (thin folded edge)
WALL_MAX = 0.025         # thickness through the body
SEG_BODY = 88

# arm cross-section stations (z, cx, half width, half thickness), spec 4.2
ARM_STATIONS = [
    (1.120, 0.300, 0.070, 0.070),   # root cap, buried inside the body
    (1.105, 0.380, 0.068, 0.070),
    (1.075, 0.430, 0.068, 0.072),   # armhole (slanted oval on the body)
    (1.000, 0.470, 0.072, 0.070),
    (0.880, 0.500, 0.070, 0.064),
    (0.790, 0.505, 0.058, 0.056),
    (0.720, 0.502, 0.048, 0.046),
    (0.675, 0.496, 0.036, 0.036),
    (0.650, 0.490, 0.024, 0.024),
    (0.635, 0.484, 0.012, 0.012),
]
ARM_TIP = (0.480, 0.620)
SEG_ARM = 32


BILL_C = (0.0, -0.372, 1.340)   # bill centre
BILL_R = (0.220, 0.098, 0.135)  # half width / depth / height
BILL_SEAM_Z = 1.328
BILL_SEAM_SAG = 0.030           # spec 6.1 (A): ends drop 30 mm
BILL_SEAM_W = 0.205             # seam half width
BILL_GROOVE = 0.006             # groove depth
BILL_GROOVE_W = 0.018           # groove width
BILL_STEP = 0.004               # lower bill lip step

EYE_Z = 1.535            # measured: ~16% below the top
EYE_R = 0.080            # 0.16 diameter (measured)
EYE_X = 0.165            # +-0.165 -> 0.33 spacing (measured)
PUPIL_R = 0.013
LASH_LEN = 0.040
EYE_APPLIQUE = 0.004     # felt patch thickness

SHOE_X = 0.215           # ankle centre
SHOE_Y = -0.15           # v3: feet shifted forward, robe stays behind them
SHOE_TOE_OUT = math.radians(14.0)
SHOE_LEN_F = 0.390       # toe reach ahead of ankle
SHOE_LEN_B = 0.160       # heel behind ankle
SHOE_HALF_W = 0.200      # footprint half width
SHOE_TOP = 0.160         # flat foot: instep height
SHOE_SOLE = 0.020        # thin sole band at the outline

HIP_Z = 0.900
KNEE_Z = 0.500
ANKLE_Z = 0.120

PELVIS_Z = 0.930

SIGN_W = 0.600
SIGN_H = 0.400
SIGN_T = 0.020
ROD_LEN = 0.400

# --------------------------------------------------------------------------
# Palette (spec section 6) -- sRGB hex -> linear
# --------------------------------------------------------------------------
def srgb(hexstr):
    h = hexstr.lstrip("#")
    vals = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def lin(v):
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    return tuple(lin(v) for v in vals) + (1.0,)


PALETTE = {
    "M_Suit":      ("#E9E9E9", 0.85),
    "M_Liner":     ("#262626", 0.95),
    "M_Bill":      ("#F0B850", 0.62),
    "M_BillLower": ("#E3AC45", 0.60),
    "M_EyeWhite":  ("#FFFFFF", 0.20),
    "M_Pupil":     ("#050505", 0.90),
    "M_Line":      ("#2B2B2B", 0.60),
    "M_Skin":      ("#C98E6B", 0.65),
    "M_Hair":      ("#2A211C", 0.70),
    "M_Shorts":    ("#3A3A3A", 0.85),
    "M_Sign":      ("#F7F5EE", 0.80),
    "M_Debug":     ("#4A6FA5", 0.65),
}

MATS = {}


def build_materials():
    for name, (hexcol, rough) in PALETTE.items():
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        col = srgb(hexcol)
        bsdf.inputs["Base Color"].default_value = col
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = 0.0
        mat.diffuse_color = col          # Workbench / viewport
        mat.use_backface_culling = False  # keep inner faces visible in glTF
        MATS[name] = mat


def _image_node(nodes, path, non_color=False):
    img = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    node = nodes.new("ShaderNodeTexImage")
    node.image = img
    node.interpolation = "Linear"
    return node


def setup_fabric_material():
    """Short-pile fleece: subtle albedo + fibre normal + rough, sheen (spec 7.2)."""
    mat = MATS["M_Suit"]
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Sheen Weight"].default_value = 0.80
    bsdf.inputs["Sheen Roughness"].default_value = 0.25
    bsdf.inputs["Specular IOR Level"].default_value = 0.30
    bsdf.inputs["Sheen Tint"].default_value = (1.0, 0.98, 0.95, 1.0)

    albedo = _image_node(nodes, TEX / "fabric_albedo_1k.png")
    albedo.location = (-600, 300)
    links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])

    rough = _image_node(nodes, TEX / "fabric_rough_1k.jpg", non_color=True)
    rough.location = (-600, 0)
    links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])

    normal = _image_node(nodes, TEX / "fabric_normal_1k.jpg", non_color=True)
    normal.location = (-600, -300)
    nmap = nodes.new("ShaderNodeNormalMap")
    nmap.location = (-300, -300)
    nmap.inputs["Strength"].default_value = 0.90
    links.new(normal.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])


# --------------------------------------------------------------------------
# Scene helpers
# --------------------------------------------------------------------------
def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for bad in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures,
                bpy.data.actions, bpy.data.cameras, bpy.data.lights):
        for datablock in list(bad):
            bad.remove(datablock)


def make_collections():
    scene = bpy.context.scene
    colls = {}
    for name in ("SUIT", "INNER", "PROPS", "RIG", "RENDER", "DEBUG"):
        coll = bpy.data.collections.new(name)
        scene.collection.children.link(coll)
        colls[name] = coll
    return colls


def add_mesh(name, verts, faces, mat_name, coll, smooth=True):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate(verbose=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    if mat_name:
        obj.data.materials.append(MATS[mat_name])
    for poly in mesh.polygons:
        poly.use_smooth = smooth
    return obj


# --------------------------------------------------------------------------
# Primitive generators (return verts, faces)
# --------------------------------------------------------------------------
def lathe(profile, segments, cap_top=True, cap_bottom=False,
          top_z=None, bottom_z=None):
    """profile: list of (z, rx, ry) bottom -> top. Returns open tube + caps."""
    verts, faces = [], []
    rings = len(profile)
    for (z, rx, ry) in profile:
        for j in range(segments):
            a = 2.0 * math.pi * j / segments
            verts.append((rx * math.cos(a), ry * math.sin(a), z))
    for i in range(rings - 1):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            c = (i + 1) * segments + (j + 1) % segments
            d = (i + 1) * segments + j
            faces.append((a, b, c, d))
    if cap_top:
        z = profile[-1][0] if top_z is None else top_z
        pole = len(verts)
        verts.append((0.0, 0.0, z))
        base = (rings - 1) * segments
        for j in range(segments):
            faces.append((pole, base + j, base + (j + 1) % segments))
    if cap_bottom:
        z = profile[0][0] if bottom_z is None else bottom_z
        pole = len(verts)
        verts.append((0.0, 0.0, z))
        for j in range(segments):
            faces.append((pole, (j + 1) % segments, j))
    return verts, faces


def ellipsoid(seg, rings, center, radii):
    """Lat-long ellipsoid."""
    cx, cy, cz = center
    rx, ry, rz = radii
    verts = []
    for i in range(1, rings):
        phi = math.pi * i / rings          # 0 top -> pi bottom
        sp, cp = math.sin(phi), math.cos(phi)
        for j in range(seg):
            a = 2.0 * math.pi * j / seg
            verts.append((cx + rx * sp * math.cos(a),
                          cy + ry * sp * math.sin(a),
                          cz + rz * cp))
    top = len(verts)
    verts.append((cx, cy, cz + rz))
    bot = len(verts)
    verts.append((cx, cy, cz - rz))
    faces = []
    for i in range(rings - 2):
        for j in range(seg):
            a = i * seg + j
            b = i * seg + (j + 1) % seg
            c = (i + 1) * seg + (j + 1) % seg
            d = (i + 1) * seg + j
            faces.append((a, b, c, d))
    last = (rings - 2) * seg
    for j in range(seg):
        faces.append((top, j, (j + 1) % seg))
        faces.append((bot, last + (j + 1) % seg, last + j))
    return verts, faces


def cone(base, direction, length, r0, r1, sides=4):
    """Tapered spike from base along direction."""
    d = Vector(direction).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, 1, 0))
    u = d.cross(up).normalized()
    v = d.cross(u).normalized()
    b = Vector(base)
    verts = []
    for j in range(sides):
        a = 2.0 * math.pi * j / sides
        verts.append(tuple(b + (u * math.cos(a) + v * math.sin(a)) * r0))
    tip = b + d * length
    tip_i = len(verts)
    verts.append(tuple(tip))
    if r1 > 1e-5:
        base_ring = len(verts)
        for j in range(sides):
            a = 2.0 * math.pi * j / sides
            verts.append(tuple(b + d * length + (u * math.cos(a) + v * math.sin(a)) * r1))
        faces = []
        for j in range(sides):
            faces.append((j, (j + 1) % sides, base_ring + (j + 1) % sides))
            faces.append((j, base_ring + (j + 1) % sides, base_ring + j))
        faces.append((base_ring + 0, base_ring + 1, base_ring + 2))
        faces.append((base_ring + 0, base_ring + 2, base_ring + 3))
        return verts, faces
    faces = [(j, (j + 1) % sides, tip_i) for j in range(sides)]
    return verts, faces


# --------------------------------------------------------------------------
# Body parts
# --------------------------------------------------------------------------
def _smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def body_r(z):
    """Outer half width at z: soft egg shoulder, hem flare, pooling bulge at the floor."""
    if z > DOME_Z0:
        u = min(1.0, (z - DOME_Z0) / DOME_H)
        return BODY_R * max(0.0, 1.0 - u ** 3) ** DOME_P
    flare = 1.0 + (HEM_FLARE - 1.0) * (1.0 - _smoothstep((z - HEM_Z) / 0.18))
    flare += 0.040 * (1.0 - _smoothstep((z - HEM_Z) / 0.18))     # fabric spreads on the floor
    roll = 0.016 * math.exp(-((z - (HEM_Z + 0.026)) / 0.026) ** 2)   # folded hem
    return BODY_R * flare + roll


def shell_radius(z):
    r = body_r(z)
    return (r, r * DEPTH_RATIO)


def wall_t(z):
    """Fabric thickness: thin folded edge at the hem, full thickness above."""
    return WALL_MIN + (WALL_MAX - WALL_MIN) * _smoothstep((z - HEM_Z) / 0.10)


def inner_r(z):
    return max(0.02, body_r(z) - wall_t(z))


def _revolve(profile, seg, ratio=DEPTH_RATIO):
    """Revolve a closed (r, z) polyline around Z; r == 0 becomes a pole."""
    verts, rings = [], []
    for (r, z) in profile:
        if r < 1e-6:
            rings.append([len(verts)])
            verts.append((0.0, 0.0, z))
        else:
            ring = []
            for j in range(seg):
                a = 2.0 * math.pi * j / seg
                ring.append(len(verts))
                verts.append((r * math.cos(a), r * ratio * math.sin(a), z))
            rings.append(ring)
    faces = []
    for i in range(len(rings)):
        A, B = rings[i], rings[(i + 1) % len(rings)]
        if len(A) == 1 and len(B) == 1:
            continue
        if len(A) == 1:
            faces += [(A[0], B[(j + 1) % seg], B[j]) for j in range(seg)]
        elif len(B) == 1:
            faces += [(A[j], A[(j + 1) % seg], B[0]) for j in range(seg)]
        else:
            faces += [(A[j], A[(j + 1) % seg], B[(j + 1) % seg], B[j])
                      for j in range(seg)]
    return verts, faces


def recalc_normals(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def _boolean(obj, cutter, op):
    mod = obj.modifiers.new(f"Bool_{op}", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = cutter
    mod.material_mode = "TRANSFER"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def _bevel(obj, width, segments, angle_deg):
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle_deg)
    mod.use_clamp_overlap = True
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _arm_solid(sx):
    """Closed swept tube: buried root -> armhole -> hanging padded flipper."""
    pts = [(cx, z, a, b) for (z, cx, a, b) in ARM_STATIONS]
    verts, rings = [], []
    for i, (cx, z, a, b) in enumerate(pts):
        p = Vector((cx, 0.0, z))
        if i == 0:
            t = Vector((pts[1][0] - cx, 0.0, pts[1][1] - z))
        elif i == len(pts) - 1:
            t = Vector((cx - pts[i - 1][0], 0.0, z - pts[i - 1][1]))
        else:
            t = Vector((pts[i + 1][0] - pts[i - 1][0], 0.0, pts[i + 1][1] - pts[i - 1][1]))
        t.normalize()
        e1 = t.cross(Vector((0.0, 1.0, 0.0))).normalized()
        e2 = Vector((0.0, 1.0, 0.0))
        ring = []
        for j in range(SEG_ARM):
            th = 2.0 * math.pi * j / SEG_ARM
            q = p + e1 * (a * math.cos(th)) + e2 * (b * math.sin(th))
            ring.append(len(verts))
            verts.append((sx * q.x, q.y, q.z))
        rings.append(ring)

    faces = []
    c0 = len(verts)
    verts.append((sx * pts[0][0], 0.0, pts[0][1]))
    for j in range(SEG_ARM):
        faces.append((c0, rings[0][(j + 1) % SEG_ARM], rings[0][j]))
    c1 = len(verts)
    verts.append((sx * ARM_TIP[0], 0.0, ARM_TIP[1]))
    for j in range(SEG_ARM):
        faces.append((rings[-1][j], rings[-1][(j + 1) % SEG_ARM], c1))
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        for j in range(SEG_ARM):
            faces.append((A[j], A[(j + 1) % SEG_ARM], B[(j + 1) % SEG_ARM], B[j]))
    return verts, faces


def _cavity_solid():
    """Inner void: open at the bottom (cuts through the hem), flat ceiling."""
    zs = [0.06, 0.10, 0.15, 0.22, 0.31, 0.40, 0.50, 0.61, 0.72, 0.83, 0.93,
          1.03, 1.12, 1.21, 1.31, 1.41, 1.50, 1.58, 1.64]
    prof = [(0.0, -0.02), (inner_r(HEM_Z), -0.02), (inner_r(HEM_Z), HEM_Z)]
    for z in zs:
        prof.append((inner_r(z), z))
    prof.append((0.0, 1.680))          # flat inner ceiling, thick top wall
    return _revolve(prof, SEG_BODY)


def apply_folds(obj):
    """Deterministic soft folds: hanging wrinkles, hem pooling, wavy hem."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    for v in bm.verts:
        p = v.co.copy()
        ang = math.atan2(p.y / DEPTH_RATIO, p.x)
        fall = 1.0 - _smoothstep((p.z - 0.30) / 0.90)
        # hanging folds, stronger near the floor (fabric pooling)
        pool = 1.0 - _smoothstep((p.z - 0.02) / 0.34)
        fold = 0.0050 * math.sin(ang * 9.0 + 0.6) * fall
        fold += 0.0025 * math.sin(ang * 14.0 + 2.1) * fall
        fold += 0.0100 * math.sin(ang * 13.0 + 0.9) * pool ** 1.5
        fold += 0.0180 * math.sin(ang * 7.0 + 2.2) * pool ** 2
        lump = 0.0028 * noise.noise(p * 3.2) + 0.0012 * noise.noise(p * 7.5)
        guard = _smoothstep((p.z - (HEM_Z + 0.012)) / 0.04)
        radial = Vector((p.x, p.y / DEPTH_RATIO, 0.0))
        if radial.length > 1e-6 and v.normal.dot(radial) > 0.0:
            # only the outer wall gets the folds, so the lining never pokes through
            v.co = p + v.normal * (fold + lump) * guard
        # fabric sags forward between the feet (fills the gap with white)
        if p.y < 0.0 and abs(p.x) < 0.18 and p.z < 0.36:
            w = math.exp(-(p.x / 0.10) ** 2) * (1.0 - _smoothstep((p.z - 0.04) / 0.26))
            v.co.y -= 0.055 * w
        if p.z < HEM_Z + 0.03:            # pool edge: fabric bunches on the floor
            t = 1.0 - (p.z - HEM_Z) / 0.03
            v.co.z += (0.0180 * math.sin(ang * 7.0 + 2.2) + 0.0070 * math.sin(ang * 13.0 + 0.9)) * t
            v.co.z = max(v.co.z, 0.010)
        fold = fold * (1.0 + 0.6 * (1.0 - _smoothstep((p.z - 0.02) / 0.12)))
    bm.to_mesh(obj.data)
    bm.free()
    for poly in obj.data.polygons:
        poly.use_smooth = True


def apply_cylindrical_uv(obj):
    """Seamless cylindrical UV for the fleece: 6 tiles around, 0.5 m per tile."""
    me = obj.data
    uv = me.uv_layers.new(name="UVMap")
    tiles = 6
    for poly in me.polygons:
        loops = [(li, me.vertices[me.loops[li].vertex_index].co) for li in poly.loop_indices]
        us = []
        for _li, co in loops:
            ang = math.atan2(co.y / DEPTH_RATIO, co.x)
            us.append(((ang / (2.0 * math.pi)) % 1.0) * tiles)
        if max(us) - min(us) > tiles * 0.5:
            us = [u + tiles if u < tiles * 0.5 else u for u in us]
        for (li, co), u in zip(loops, us):
            uv.data[li].uv = (u, co.z / 0.5)


def build_shell(colls):
    zs = [HEM_Z, 0.04, 0.07, 0.10, 0.14, 0.20, 0.23, 0.27, 0.32, 0.38, 0.45, 0.53, 0.62, 0.72,
          0.82, 0.92, 1.02, 1.10, 1.18, 1.27, 1.37, 1.47, 1.57, 1.65,
          1.71, 1.755, 1.782, 1.793]
    profile = [(0.0, HEM_Z)] + [(body_r(z), z) for z in zs] + [(0.0, TOTAL_H)]
    verts, faces = _revolve(profile, SEG_BODY)
    shell = add_mesh("SUIT_Shell", verts, faces, "M_Suit", colls["SUIT"])
    recalc_normals(shell)
    for poly in shell.data.polygons:
        poly.use_smooth = True

    # one-piece suit: the sleeves are unioned into the body (spec 4.3)
    for side, sx in (("L", 1.0), ("R", -1.0)):
        av, af = _arm_solid(sx)
        arm = add_mesh(f"_Arm_{side}", av, af, "M_Suit", colls["SUIT"])
        recalc_normals(arm)
        _boolean(shell, arm, "UNION")

    # hollow it out; the cutter carries the dark liner material
    cv, cf = _cavity_solid()
    cutter = add_mesh("_Cavity", cv, cf, "M_Liner", colls["SUIT"], smooth=False)
    recalc_normals(cutter)
    _boolean(shell, cutter, "DIFFERENCE")

    # soft 14 mm fillet along the armholes and the hem rim
    _bevel(shell, width=0.016, segments=4, angle_deg=30.0)
    apply_folds(shell)
    apply_cylindrical_uv(shell)
    bpy.context.view_layer.update()
    return shell


def build_hem_roll(colls):
    """Rolled hem: a soft fabric roll wrapped around the bottom edge."""
    rx = body_r(HEM_Z) - 0.002
    hv, hf = _elliptic_torus(rx, rx * DEPTH_RATIO, 0.019, SEG_BODY, 10, HEM_Z + 0.005)
    hem = add_mesh("SUIT_Hem", hv, hf, "M_Suit", colls["SUIT"])
    recalc_normals(hem)
    for poly in hem.data.polygons:
        poly.use_smooth = True
    return hem


def _elliptic_torus(rx, ry, minor, seg_major, seg_minor, z):
    verts, faces = [], []
    for i in range(seg_major):
        a = 2.0 * math.pi * i / seg_major
        ca, sa = math.cos(a), math.sin(a)
        n = Vector((ca / rx, sa / ry, 0.0)).normalized()
        for j in range(seg_minor):
            b = 2.0 * math.pi * j / seg_minor
            p = Vector((rx * ca, ry * sa, z)) + n * (minor * math.cos(b))
            p.z += minor * math.sin(b)
            verts.append(tuple(p))
    for i in range(seg_major):
        for j in range(seg_minor):
            a = i * seg_minor + j
            b = i * seg_minor + (j + 1) % seg_minor
            c = ((i + 1) % seg_major) * seg_minor + (j + 1) % seg_minor
            d = ((i + 1) % seg_major) * seg_minor + j
            faces.append((a, b, c, d))
    return verts, faces


def surface_y(x, z):
    """Front (-Y) surface of the shell at (x, z)."""
    rx, ry = shell_radius(z)
    k = min(1.0, abs(x) / max(rx, 1e-6))
    return -ry * math.sqrt(max(0.0, 1.0 - k * k))


def disc_on_surface(cx, cz, radius, offset, rings=3, segs=20):
    """Flat disc lying on the shell surface, pushed forward by `offset`."""
    verts = [(cx, surface_y(cx, cz) - offset, cz)]
    for i in range(1, rings + 1):
        u = i / rings
        for j in range(segs):
            a = 2.0 * math.pi * j / segs
            x = cx + radius * u * math.cos(a)
            z = cz + radius * u * math.sin(a)
            verts.append((x, surface_y(x, z) - offset, z))
    faces = []
    for j in range(segs):
        faces.append((0, 1 + j, 1 + (j + 1) % segs))
    for i in range(rings - 1):
        base = 1 + i * segs
        nxt = base + segs
        for j in range(segs):
            faces.append((base + j, base + (j + 1) % segs,
                          nxt + (j + 1) % segs, nxt + j))
    return verts, faces


def annulus_on_surface(cx, cz, r_in, r_out, offset, segs=24):
    verts, faces = [], []
    for radius in (r_in, r_out):
        for j in range(segs):
            a = 2.0 * math.pi * j / segs
            x = cx + radius * math.cos(a)
            z = cz + radius * math.sin(a)
            verts.append((x, surface_y(x, z) - offset, z))
    for j in range(segs):
        a = j
        b = (j + 1) % segs
        faces.append((a, b, segs + b, segs + a))
    return verts, faces


def _pancake(cx, cy, cz, rx, ry, h, up=True, seg=20, rings=3):
    """Flattened dome (superellipse crown) with a flat base at z=cz."""
    verts, faces = [], []
    rim = []
    for j in range(seg):
        a = 2.0 * math.pi * j / seg
        rim.append(len(verts))
        verts.append((cx + rx * math.cos(a), cy + ry * math.sin(a), cz))
    base_c = len(verts)
    verts.append((cx, cy, cz))
    for j in range(seg):
        faces.append((base_c, rim[(j + 1) % seg], rim[j]))
    prev = rim
    for i in range(1, rings + 1):
        u = 1.0 - i / rings
        if u <= 1e-6:
            apex = len(verts)
            verts.append((cx, cy, cz + (h if up else -h)))
            for j in range(seg):
                faces.append((prev[j], prev[(j + 1) % seg], apex))
            break
        z = cz + (h if up else -h) * math.sqrt(max(0.0, 1.0 - u ** 4))
        ring = []
        for j in range(seg):
            a = 2.0 * math.pi * j / seg
            ring.append(len(verts))
            verts.append((cx + rx * u * math.cos(a), cy + ry * u * math.sin(a), z))
        for j in range(seg):
            faces.append((prev[j], prev[(j + 1) % seg],
                          ring[(j + 1) % seg], ring[j]))
        prev = ring
    return verts, faces


def _flat_disc(cx, cy, cz, rx, ry, seg=20, rings=2):
    verts = [(cx, cy, cz)]
    faces, prev = [], []
    for i in range(1, rings + 1):
        u = i / rings
        ring = []
        for j in range(seg):
            a = 2.0 * math.pi * j / seg
            ring.append(len(verts))
            verts.append((cx + rx * u * math.cos(a), cy + ry * u * math.sin(a), cz))
        if i == 1:
            for j in range(seg):
                faces.append((0, ring[j], ring[(j + 1) % seg]))
        else:
            for j in range(seg):
                faces.append((prev[j], prev[(j + 1) % seg],
                              ring[(j + 1) % seg], ring[j]))
        prev = ring
    return verts, faces


def bill_seam_z(x):
    """Seam of the upper/lower bill: A (ends drop 30 mm), spec 6.1."""
    return BILL_SEAM_Z - BILL_SEAM_SAG * (x / BILL_SEAM_W) ** 2


def build_bills(colls):
    """Duck bill with a real curved groove + lip step; lower half follows the jaw."""
    rx, ry, rz = BILL_R
    cx, cy, cz = BILL_C
    n_theta, n_phi = 88, 64
    verts, faces = [], []
    for i in range(n_phi + 1):
        phi = -math.pi / 2.0 + math.pi * i / n_phi
        for j in range(n_theta):
            th = 2.0 * math.pi * j / n_theta
            x = cx + rx * math.cos(phi) * math.cos(th)
            y = cy + ry * math.cos(phi) * math.sin(th)
            z = cz + rz * math.sin(phi)
            # groove: pull toward the bill centre around the seam curve
            d = z - bill_seam_z(x)
            groove = BILL_GROOVE * math.exp(-(d / (BILL_GROOVE_W * 0.5)) ** 2)
            if abs(x) < BILL_SEAM_W + 0.01:
                p = Vector((x, y, z)) - Vector((cx, cy, cz))
                p *= 1.0 - groove / max(1e-6, p.length)
                x, y, z = cx + p.x, cy + p.y, cz + p.z
            # lip step: the lower bill sits 4 mm further back (smooth, no stairs)
            if d < BILL_GROOVE_W * 0.5:
                y += BILL_STEP * _smoothstep((-d - BILL_GROOVE_W * 0.5) / 0.006)
            verts.append((x, y, z))
    for i in range(n_phi):
        for j in range(n_theta):
            a = i * n_theta + j
            b = i * n_theta + (j + 1) % n_theta
            c = (i + 1) * n_theta + (j + 1) % n_theta
            d = (i + 1) * n_theta + j
            faces.append((a, b, c, d))
    bill = add_mesh("SUIT_Bill_Upper", verts, faces, "M_Bill", colls["SUIT"])
    bill.data.materials.append(MATS["M_BillLower"])
    for poly in bill.data.polygons:
        zc = sum(bill.data.vertices[i].co.z for i in poly.vertices) / len(poly.vertices)
        xc = sum(bill.data.vertices[i].co.x for i in poly.vertices) / len(poly.vertices)
        poly.material_index = 1 if zc < bill_seam_z(xc) else 0
    return bill


def applique_on_surface(cx, cz, radius, lift, rings=3, segs=24):
    """Sewn-on felt patch: rim on the shell, wall of `lift`, rounded top disc."""
    verts, faces = [], []
    bottom = []
    for j in range(segs):
        a = 2.0 * math.pi * j / segs
        x = cx + radius * math.cos(a)
        z = cz + radius * math.sin(a)
        bottom.append(len(verts))
        verts.append((x, surface_y(x, z) - 0.0015, z))
    wall = []
    for j in range(segs):
        a = 2.0 * math.pi * j / segs
        x = cx + radius * math.cos(a)
        z = cz + radius * math.sin(a)
        wall.append(len(verts))
        verts.append((x, surface_y(x, z) - lift, z))
    for j in range(segs):
        faces.append((bottom[j], bottom[(j + 1) % segs],
                      wall[(j + 1) % segs], wall[j]))
    # rounded top: two rings shrinking toward the centre
    prev = wall
    for k in (0.55, 1.0):
        ring = []
        for j in range(segs):
            a = 2.0 * math.pi * j / segs
            x = cx + radius * (1.0 - k) * math.cos(a)
            z = cz + radius * (1.0 - k) * math.sin(a)
            ring.append(len(verts))
            verts.append((x, surface_y(x, z) - lift - 0.0015 * k, z))
        for j in range(segs):
            faces.append((prev[j], prev[(j + 1) % segs],
                          ring[(j + 1) % segs], ring[j]))
        prev = ring
    c = len(verts)
    verts.append((cx, surface_y(cx, cz) - lift - 0.002, cz))
    for j in range(segs):
        faces.append((prev[j], prev[(j + 1) % segs], c))
    return verts, faces


def build_eyes(colls):
    objs = {}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        cx = sx * EYE_X
        ev, ef = applique_on_surface(cx, EYE_Z, EYE_R, EYE_APPLIQUE, rings=3, segs=28)
        objs[f"eye_{side}"] = add_mesh(f"SUIT_Eye_{side}", ev, ef, "M_EyeWhite", colls["SUIT"])

        pv, pf = disc_on_surface(cx, EYE_Z, PUPIL_R, EYE_APPLIQUE + 0.004, rings=1, segs=12)
        objs[f"pupil_{side}"] = add_mesh(f"SUIT_Pupil_{side}", pv, pf, "M_Pupil", colls["SUIT"])

        rv, rf = annulus_on_surface(cx, EYE_Z, EYE_R + 0.001, EYE_R + 0.005,
                                    EYE_APPLIQUE + 0.0008, segs=28)
        objs[f"rim_{side}"] = add_mesh(f"SUIT_EyeRim_{side}", rv, rf, "M_Line", colls["SUIT"])

        lv, lf = [], []
        for ang in (-0.55, 0.0, 0.55):
            ex = cx + EYE_R * 0.96 * math.sin(ang) * sx
            ez = EYE_Z + EYE_R * 0.96 * math.cos(ang)
            base = Vector((ex, surface_y(ex, ez) - EYE_APPLIQUE - 0.002, ez))
            direction = Vector((math.sin(ang) * 0.55 * sx, -0.12, math.cos(ang))).normalized()
            v, f = cone(base, direction, LASH_LEN, 0.006, 0.0008, sides=4)
            off = len(lv)
            lv += v
            lf += [tuple(i + off for i in face) for face in f]
        objs[f"lash_{side}"] = add_mesh(f"SUIT_Lash_{side}", lv, lf, "M_Line", colls["SUIT"])
    return objs


TOES = (-0.90, 0.0, 0.90)
TOE_W = 0.40


def _toe_shape(theta):
    """1 at each toe tip, 0 at the web notches; sharp V between toes."""
    best = 0.0
    for ang in TOES:
        d = abs((theta - ang + math.pi) % (2.0 * math.pi) - math.pi)
        if d < TOE_W:
            best = max(best, (1.0 - d / TOE_W) ** 0.62)
    return best


def _toe_peak(theta):
    """Pointed toe crown: 1 at the tip, falling fast to the web."""
    best = 0.0
    for ang in TOES:
        d = abs((theta - ang + math.pi) % (2.0 * math.pi) - math.pi)
        best = max(best, math.exp(-(d / 0.26) ** 1.25))
    return best


def _shoe_outline(theta):
    """Polar radius of the duck shoe around the ankle (0 = forward, + = outward)."""
    c = math.cos(theta)
    if c >= 0.0:
        base = SHOE_HALF_W + (SHOE_LEN_F - SHOE_HALF_W) * c ** 0.9
    else:
        base = SHOE_HALF_W + (SHOE_LEN_B - SHOE_HALF_W) * (-c) ** 0.9
    return base - 0.020 + 0.130 * _toe_shape(theta)


def _shoe_height(u, theta=0.0):
    """Puffy instep, thin webbing, three toe ridges."""
    h = SHOE_SOLE + (SHOE_TOP - SHOE_SOLE) * max(0.0, 1.0 - u ** 3) ** 0.42
    h += 0.070 * _toe_shape(theta) ** 0.8 * u ** 2
    return h


def build_shoes(colls):
    objs = {}
    seg = 64
    us = (0.08, 0.20, 0.33, 0.46, 0.59, 0.71, 0.81, 0.89, 0.95, 0.985, 1.0)
    ca, sa = math.cos(SHOE_TOE_OUT), math.sin(SHOE_TOE_OUT)
    for side, sx in (("L", 1.0), ("R", -1.0)):
        verts, faces = [], []
        rings = []
        for u in us:
            ring = []
            for j in range(seg):
                th = 2.0 * math.pi * j / seg
                h = _shoe_height(u, th)
                taper = 1.0 - 0.24 * (h / SHOE_TOP)     # narrower at the ankle
                R = _shoe_outline(th) * u * taper
                lx, ly = R * math.sin(th), -R * math.cos(th)
                wx, wy = lx * ca - ly * sa, lx * sa + ly * ca
                ring.append(len(verts))
                world_x = sx * (SHOE_X + wx)
                # flat inner wall -> a 6 cm gap between the two feet
                world_x = max(world_x, 0.030) if sx > 0 else min(world_x, -0.030)
                verts.append((world_x, wy + SHOE_Y, h))
            rings.append(ring)
        apex = len(verts)
        verts.append((sx * SHOE_X, SHOE_Y, SHOE_TOP))
        for j in range(seg):
            faces.append((apex, rings[0][j], rings[0][(j + 1) % seg]))
        for a, b in zip(rings, rings[1:]):
            for j in range(seg):
                faces.append((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
        # sole band (z = SOLE -> 0) + flat sole at z=0
        rim = rings[-1]
        sole = []
        for j in range(seg):
            x, y, _ = verts[rim[j]]
            sole.append(len(verts))
            verts.append((x, y, 0.0))
        for j in range(seg):
            faces.append((rim[j], rim[(j + 1) % seg], sole[(j + 1) % seg], sole[j]))
        sole_c = len(verts)
        verts.append((sx * SHOE_X, SHOE_Y, 0.0))
        for j in range(seg):
            faces.append((sole_c, sole[(j + 1) % seg], sole[j]))
        objs[side] = add_mesh(f"DUCKSHOE_{side}", verts, faces, "M_Bill", colls["SUIT"])
        recalc_normals(objs[side])
    return objs


LEG_STATIONS = [
    (0.900, 0.092), (0.800, 0.090), (0.700, 0.086), (0.600, 0.082),
    (KNEE_Z + 0.06, 0.078), (KNEE_Z, 0.076), (KNEE_Z - 0.06, 0.074),
    (0.380, 0.072), (0.300, 0.068), (0.220, 0.060), (0.170, 0.050),
    (ANKLE_Z, 0.044), (0.080, 0.042), (0.040, 0.040),
]


def leg_radius(z):
    for (z0, r0), (z1, r1) in zip(LEG_STATIONS, LEG_STATIONS[1:]):
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1)
            return r0 + (r1 - r0) * t
    return LEG_STATIONS[-1][1]


def build_legs(colls):
    objs = {}
    seg = 14
    for side, sx in (("L", 1.0), ("R", -1.0)):
        x0 = sx * SHOE_X
        profile = [(z, r, r) for (z, r) in LEG_STATIONS]
        verts, faces = lathe(profile, seg, cap_top=True, cap_bottom=True)
        verts = [(x + x0, y, z) for (x, y, z) in verts]
        objs[side] = add_mesh(f"INNER_Leg_{side}", verts, faces, "M_Skin", colls["INNER"])
    return objs


def build_hair(colls):
    verts, faces = [], []
    for side, sx in (("L", 1.0), ("R", -1.0)):
        x0 = sx * SHOE_X
        for k in range(16):
            z = 0.300 + 0.022 * k
            ang = (k * 2.399) % (2 * math.pi)
            r = leg_radius(z) + 0.004
            base = Vector((x0 + r * math.cos(ang), r * math.sin(ang), z))
            out = Vector((math.cos(ang), math.sin(ang), -1.0)).normalized()
            length = 0.045 + 0.012 * ((k * 5) % 3)
            v, f = cone(base, out, length, 0.022, 0.001, sides=4)
            off = len(verts)
            verts += v
            faces += [tuple(i + off for i in face) for face in f]
    return add_mesh("INNER_Hair", verts, faces, "M_Hair", colls["INNER"])


def build_pelvis(colls):
    v, f = ellipsoid(16, 10, (0.0, 0.0, PELVIS_Z), (0.190, 0.150, 0.135))
    return add_mesh("INNER_Pelvis", v, f, "M_Shorts", colls["INNER"])


def build_sign(colls):
    cx, cy, cz = -0.850, -0.200, 0.780
    verts, faces = [], []

    # board (box)
    hw, hh, ht = SIGN_W / 2, SIGN_H / 2, SIGN_T / 2
    corners = [(-hw, -ht, -hh), (hw, -ht, -hh), (hw, ht, -hh), (-hw, ht, -hh),
               (-hw, -ht, hh), (hw, -ht, hh), (hw, ht, hh), (-hw, ht, hh)]
    verts += [(cx + x, cy + y, cz + z) for (x, y, z) in corners]
    for quad in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
                 (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        faces.append(quad)

    # rod: from the flipper tip up to the back of the board
    start = Vector((-0.484, 0.000, 0.640))
    end = Vector((-0.850, -0.190, 0.780))
    rod_v, rod_f = _tube(start, end, 0.012, sides=8)
    off = len(verts)
    verts += rod_v
    faces += [tuple(i + off for i in face) for face in rod_f]

    return add_mesh("PROP_Sign", verts, faces, "M_Sign", colls["PROPS"], smooth=False)


def _tube(a, b, r, sides=8):
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(up).normalized()
    v = d.cross(u).normalized()
    verts, faces = [], []
    for end_p in (a, b):
        for j in range(sides):
            t = 2.0 * math.pi * j / sides
            verts.append(tuple(end_p + (u * math.cos(t) + v * math.sin(t)) * r))
    for j in range(sides):
        faces.append((j, (j + 1) % sides, sides + (j + 1) % sides, sides + j))
    # triangle fans instead of n-gon caps (spec: no stray n-gons)
    c0 = len(verts)
    verts.append(tuple(a))
    for j in range(sides):
        faces.append((c0, (j + 1) % sides, j))
    c1 = len(verts)
    verts.append(tuple(b))
    for j in range(sides):
        faces.append((c1, sides + j, sides + (j + 1) % sides))
    return verts, faces


# --------------------------------------------------------------------------
# Rig
# --------------------------------------------------------------------------
BONES = [
    ("root", (0, 0, 0), (0, -0.20, 0), None),
    ("pelvis", (0, 0, HIP_Z), (0, 0, 1.00), "root"),
    ("thigh_L", (SHOE_X, 0, HIP_Z), (SHOE_X, 0, KNEE_Z), "pelvis"),
    ("shin_L", (SHOE_X, 0, KNEE_Z), (SHOE_X, 0, ANKLE_Z), "thigh_L"),
    ("foot_L", (SHOE_X, 0, ANKLE_Z), (SHOE_X, -0.20, 0.060), "shin_L"),
    ("thigh_R", (-SHOE_X, 0, HIP_Z), (-SHOE_X, 0, KNEE_Z), "pelvis"),
    ("shin_R", (-SHOE_X, 0, KNEE_Z), (-SHOE_X, 0, ANKLE_Z), "thigh_R"),
    ("foot_R", (-SHOE_X, 0, ANKLE_Z), (-SHOE_X, -0.20, 0.060), "shin_R"),
    ("shell", (0, 0, HIP_Z), (0, 0, TOTAL_H), "pelvis"),
    ("jaw", (0, -0.200, 1.300), (0, -0.360, 1.285), "shell"),
    ("arm_L", (0.437, 0, 1.105), (0.484, 0, 0.640), "shell"),
    ("arm_R", (-0.437, 0, 1.105), (-0.484, 0, 0.640), "shell"),
    ("sign_socket", (-0.484, 0.000, 0.640), (-0.850, -0.190, 0.780), "arm_R"),
]


def build_armature(colls):
    arm = bpy.data.armatures.new("RIG_Eliz")
    obj = bpy.data.objects.new("RIG_Eliz", arm)
    colls["RIG"].objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    created = {}
    for name, head, tail, parent in BONES:
        eb = arm.edit_bones.new(name)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        eb.use_connect = False
        created[name] = eb
    info = {name: (head, tail) for name, head, tail, _ in BONES}
    for name, _, _, parent in BONES:
        if not parent:
            continue
        created[name].parent = created[parent]
        if (Vector(info[name][0]) - Vector(info[parent][1])).length < 1e-6:
            created[name].use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in obj.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return obj


def _leg_weights(z):
    """Smooth thigh/shin/foot weights for hairy legs."""
    w_thigh = _smoothstep((z - 0.42) / (0.58 - 0.42))
    rest = 1.0 - w_thigh
    t = _smoothstep((z - 0.08) / (0.16 - 0.08))
    return {"thigh": w_thigh, "shin": rest * t, "foot": rest * (1.0 - t)}


def bind(obj, arm_obj, weights_fn):
    """weights_fn(obj) -> {bone_name: weight} or per-vertex callable."""
    arm_mod = obj.modifiers.new("Armature", "ARMATURE")
    arm_mod.object = arm_obj
    obj.parent = arm_obj


def add_vertex_groups(obj, per_vertex):
    groups = {}
    for i, weights in enumerate(per_vertex):
        for bone, w in weights.items():
            if w <= 0.0001:
                continue
            vg = groups.get(bone)
            if vg is None:
                vg = obj.vertex_groups.new(name=bone)
                groups[bone] = vg
            vg.add([i], w, "REPLACE")


def arm_weight(x, z):
    """0 on the body, 1 on the sleeve; narrow blend across the armhole."""
    w = _smoothstep((abs(x) - body_r(z) + 0.015) / 0.055)
    w *= 1.0 - _smoothstep((z - 1.20) / 0.05)
    return w


def bind_suit(colls, arm_obj, shell, extras):
    per = []
    for v in shell.data.vertices:
        w = arm_weight(v.co.x, v.co.z)
        side = "L" if v.co.x > 0 else "R"
        per.append({"shell": 1.0 - w, f"arm_{side}": w})
    add_vertex_groups(shell, per)
    bind(shell, arm_obj, None)
    for obj in extras:
        add_vertex_groups(obj, [{"shell": 1.0}] * len(obj.data.vertices))
        bind(obj, arm_obj, None)


def bind_legs(arm_obj, legs, hair):
    for side, obj in legs.items():
        bone_suffix = side
        vg = {bone: obj.vertex_groups.new(name=f"{bone}_{bone_suffix}") for bone in ("thigh", "shin", "foot")}
        for i, v in enumerate(obj.data.vertices):
            w = _leg_weights(v.co.z)
            for bone, weight in w.items():
                if weight > 0.0001:
                    vg[bone].add([i], weight, "REPLACE")
        bind(obj, arm_obj, None)
    # hair follows the nearest leg bone weights
    vg_hair = {b: hair.vertex_groups.new(name=b) for b in
               ("thigh_L", "shin_L", "foot_L", "thigh_R", "shin_R", "foot_R")}
    for i, v in enumerate(hair.data.vertices):
        side = "L" if v.co.x > 0 else "R"
        w = _leg_weights(v.co.z)
        for bone, weight in w.items():
            if weight > 0.0001:
                vg_hair[f"{bone}_{side}"].add([i], weight, "REPLACE")
    bind(hair, arm_obj, None)


def bind_rigid(arm_obj, obj, bone):
    add_vertex_groups(obj, [{bone: 1.0}] * len(obj.data.vertices))
    bind(obj, arm_obj, None)


# --------------------------------------------------------------------------
# Modifiers
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Pose helpers (world-axis, independent of bone roll)
# --------------------------------------------------------------------------
def _bone_local_axis(pb, world_axis):
    R = pb.bone.matrix_local.to_3x3()
    return (R.inverted() @ Vector(world_axis)).normalized()


def pose_rotate(pb, world_axis, degrees):
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion(_bone_local_axis(pb, world_axis), math.radians(degrees))


def pose_translate(pb, world_offset):
    R = pb.bone.matrix_local.to_3x3()
    pb.location = R.inverted() @ Vector(world_offset)


def reset_pose(arm_obj):
    for pb in arm_obj.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)


def apply_pose(arm_obj, shell_lift=0.0, shell_tilt=0.0, legs=None, arms=None):
    reset_pose(arm_obj)
    pb = arm_obj.pose.bones
    if shell_lift or shell_tilt:
        pose_translate(pb["shell"], (0, 0, shell_lift))
        if shell_tilt:
            pose_rotate(pb["shell"], (1, 0, 0), shell_tilt)
    for name, (axis, deg) in (legs or {}).items():
        pose_rotate(pb[name], axis, deg)
    for name, (axis, deg) in (arms or {}).items():
        pose_rotate(pb[name], axis, deg)


# --------------------------------------------------------------------------
# Animations (stashed to NLA for glTF export)
# --------------------------------------------------------------------------
def begin_action(arm_obj):
    ad = arm_obj.animation_data or arm_obj.animation_data_create()
    ad.action = None
    reset_pose(arm_obj)
    return ad


def finish_action(arm_obj, name):
    ad = arm_obj.animation_data
    act = ad.action
    if act is None:
        raise RuntimeError(f"no action was created for {name}")
    act.name = name
    act.use_fake_user = True
    ad.action = None
    return act


def build_actions(arm_obj):
    actions = []
    pb = arm_obj.pose.bones

    # ---- idle: 60 frames, shell settles + tiny breathing ----
    begin_action(arm_obj)
    for f, lift in ((1, 0.0), (30, 0.006), (60, 0.0)):
        reset_pose(arm_obj)
        pose_translate(pb["shell"], (0, 0, lift))
        pb["shell"].keyframe_insert("location", frame=f)
        for name in ("thigh_L", "thigh_R", "shin_L", "shin_R", "foot_L", "foot_R"):
            pb[name].keyframe_insert("rotation_quaternion", frame=f)
    actions.append(finish_action(arm_obj, "idle"))

    # ---- run: 24 frame loop, shell lifted 0.17m and tilted back 8 deg ----
    begin_action(arm_obj)
    keys = [
        (1,  (-30, 20, 10), (25, 45, -20), 14.0),
        (7,  (0, 55, -5), (0, 10, 0), 0.0),
        (13, (25, 45, -20), (-30, 20, 10), -14.0),
        (19, (0, 10, 0), (0, 55, -5), 0.0),
        (25, (-30, 20, 10), (25, 45, -20), 14.0),
    ]
    for f, left, right, arm_swing in keys:
        reset_pose(arm_obj)
        pose_translate(pb["shell"], (0, 0, 0.265 + 0.010 * math.sin(f / 24.0 * 2 * math.pi)))
        pose_rotate(pb["shell"], (1, 0, 0), -8.0)
        pb["shell"].keyframe_insert("location", frame=f)
        pb["shell"].keyframe_insert("rotation_quaternion", frame=f)
        for name, (thigh, shin, foot) in (("L", left), ("R", right)):
            pose_rotate(pb[f"thigh_{name}"], (1, 0, 0), thigh)
            pb[f"thigh_{name}"].keyframe_insert("rotation_quaternion", frame=f)
            pose_rotate(pb[f"shin_{name}"], (1, 0, 0), shin)
            pb[f"shin_{name}"].keyframe_insert("rotation_quaternion", frame=f)
            pose_rotate(pb[f"foot_{name}"], (1, 0, 0), foot)
            pb[f"foot_{name}"].keyframe_insert("rotation_quaternion", frame=f)
        pose_rotate(pb["arm_L"], (1, 0, 0), arm_swing)
        pose_rotate(pb["arm_R"], (1, 0, 0), -arm_swing)
        pb["arm_L"].keyframe_insert("rotation_quaternion", frame=f)
        pb["arm_R"].keyframe_insert("rotation_quaternion", frame=f)
    actions.append(finish_action(arm_obj, "run"))

    ad = arm_obj.animation_data
    for act in actions:
        track = ad.nla_tracks.new()
        track.name = act.name
        try:
            strip = track.strips.new(act.name, 1, act)
            slots = list(getattr(act, "slots", []))
            if slots and hasattr(strip, "action_slot"):
                strip.action_slot = slots[0]
        except Exception as exc:  # keep going: actions still exist for export
            print(f"WARN: could not stash {act.name} to NLA: {exc}")
        track.mute = True
    reset_pose(arm_obj)
    return actions


# --------------------------------------------------------------------------
# Render rig
# --------------------------------------------------------------------------
def setup_world():
    world = bpy.data.worlds.new("W_Studio")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.28, 0.30, 0.34, 1.0)
    bg.inputs[1].default_value = 0.63


def add_light(name, kind, loc, energy, size=2.0, target=(0, 0, 1.0), color=(1, 1, 1)):
    light_data = bpy.data.lights.new(name, kind)
    light_data.energy = energy
    light_data.color = color
    if kind == "AREA":
        light_data.size = size
    obj = bpy.data.objects.new(name, light_data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    direction = Vector(target) - Vector(loc)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


def setup_render_rig(colls):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 32
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = -0.28
    scene.view_settings.look = "None"
    scene.render.fps = FPS

    # Freestyle gives the thin dark outline the reference art has
    scene.render.use_freestyle = True
    scene.render.line_thickness_mode = "ABSOLUTE"
    view_layer = bpy.context.scene.view_layers[0]
    view_layer.use_freestyle = True
    fs = view_layer.freestyle_settings
    for old_ls in list(fs.linesets):          # default linesets have no linestyle
        fs.linesets.remove(old_ls)
    ls = fs.linesets.new("Outline")
    ls.linestyle = bpy.data.linestyles.new("LS_Outline")
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = True
    ls.select_edge_mark = False
    ls.linestyle.color = (0.12, 0.12, 0.12)
    ls.linestyle.thickness = 4.5

    cam_data = bpy.data.cameras.new("CAM_View")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 2.05
    cam = bpy.data.objects.new("CAM_View", cam_data)
    colls["RENDER"].objects.link(cam)
    scene.camera = cam

    add_light("L_Key", "SUN", (-2.5, -3.0, 4.0), 3.5, target=(0, 0, 1.0))
    add_light("L_Fill", "AREA", (2.6, -2.6, 2.2), 230.0, size=3.5, target=(0, 0, 1.0))
    add_light("L_Rim", "AREA", (0.4, 3.2, 2.8), 260.0, size=2.5, target=(0, 0, 1.2))
    return cam


def place_camera(cam, loc, target, ortho_scale):
    cam.location = loc
    direction = Vector(target) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = ortho_scale
    bpy.context.view_layer.update()


def render_to(path, res=(800, 1000)):
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_ref_match(cam, arm_obj, sign_obj):
    """Front view framed like art/refs/eliz_front.jpg: flat light, black bg."""
    scene = bpy.context.scene
    world = scene.world
    bg = world.node_tree.nodes["Background"]
    old_color = tuple(bg.inputs[0].default_value)
    old_strength = bg.inputs[1].default_value
    old_film = scene.render.film_transparent
    old_use_nodes = scene.use_nodes

    bg.inputs[0].default_value = (0.62, 0.62, 0.62, 1.0)
    bg.inputs[1].default_value = 0.63
    light_energy = {}
    for name in ("L_Key", "L_Fill", "L_Rim"):
        light_obj = bpy.data.objects.get(name)
        if light_obj is not None:
            light_energy[name] = light_obj.data.energy
            light_obj.data.energy *= 0.63
    scene.render.film_transparent = True
    old_exposure = scene.view_settings.exposure
    scene.view_settings.exposure = -0.28

    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    rl = tree.nodes.new("CompositorNodeRLayers")
    black = tree.nodes.new("CompositorNodeRGB")
    black.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    over = tree.nodes.new("CompositorNodeAlphaOver")
    comp = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(black.outputs[0], over.inputs[1])
    tree.links.new(rl.outputs["Image"], over.inputs[2])
    tree.links.new(over.outputs[0], comp.inputs[0])

    apply_pose(arm_obj)
    if sign_obj is not None:
        sign_obj.hide_render = True
    place_camera(cam, (0.0, -6.0, 1.45), (0.0, 0.0, 0.86), 1.99)
    render_to(RENDERS / "v2_front_match.png", res=(600, 885))

    if sign_obj is not None:
        sign_obj.hide_render = False
    bg.inputs[0].default_value = old_color
    bg.inputs[1].default_value = old_strength
    scene.render.film_transparent = old_film
    scene.view_settings.exposure = old_exposure
    for name, energy in light_energy.items():
        bpy.data.objects[name].data.energy = energy
    tree.nodes.clear()
    scene.use_nodes = old_use_nodes


def render_all_views(cam, sign_obj=None, hide_sign_in=("front", "back", "side", "three_quarter")):
    views = [
        ("v2_front", (0, -6, 0.90), (0, 0, 0.90), 2.05),
        ("v2_side", (-6, 0, 0.90), (0, 0, 0.90), 2.05),
        ("v2_back", (0, 6, 0.90), (0, 0, 0.90), 2.05),
        ("v2_three_quarter", (-3.6, -4.0, 1.65), (0, 0, 0.92), 2.60),
    ]
    for name, loc, target, scale in views:
        short = name.split("_", 1)[1]
        if sign_obj is not None:
            sign_obj.hide_render = short in hide_sign_in
        place_camera(cam, loc, target, scale)
        render_to(RENDERS / f"{name}.png")
    if sign_obj is not None:
        sign_obj.hide_render = False


def render_details(cam, arm_obj):
    """Macro shots for the fabric / seams (no Freestyle, so the material reads)."""
    scene = bpy.context.scene
    scene.render.use_freestyle = False
    old_exp = scene.view_settings.exposure
    scene.view_settings.exposure = -1.05
    bpy.context.view_layer.update()
    views = [
        ("v2_detail_hem", (0.55, -1.10, 0.32), (0.26, -0.30, 0.24), 0.40),
        ("v2_detail_armhole", (1.05, -0.95, 1.32), (0.42, -0.20, 1.06), 0.40),
        ("v2_detail_mouth", (0.22, -1.20, 1.44), (0.0, -0.40, 1.33), 0.42),
        ("v2_detail_fabric", (0.32, -0.95, 0.58), (0.0, -0.36, 0.56), 0.20),
    ]
    for name, loc, target, scale in views:
        place_camera(cam, loc, target, scale)
        render_to(RENDERS / f"{name}.png", res=(700, 700))
    scene.render.use_freestyle = True
    scene.view_settings.exposure = old_exp


def build_wearer(colls):
    """Hidden performer inside the suit (validation only, never exported/rendered)."""
    objs = []
    v, f = ellipsoid(18, 12, (0.0, 0.0, 1.20), (0.155, 0.125, 0.26))
    objs.append(add_mesh("DEBUG_Torso", v, f, "M_Debug", colls["DEBUG"]))
    v, f = ellipsoid(16, 10, (0.0, 0.0, 0.93), (0.150, 0.120, 0.105))
    objs.append(add_mesh("DEBUG_Hips", v, f, "M_Debug", colls["DEBUG"]))
    v, f = ellipsoid(16, 12, (0.0, -0.02, 1.52), (0.110, 0.110, 0.115))
    objs.append(add_mesh("DEBUG_Head", v, f, "M_Debug", colls["DEBUG"]))
    for side, sx in (("L", 1.0), ("R", -1.0)):
        v, f = _tube((sx * 0.17, 0.0, 1.38), (sx * 0.215, -0.01, 0.98), 0.050, sides=10)
        objs.append(add_mesh(f"DEBUG_Arm_{side}", v, f, "M_Debug", colls["DEBUG"]))
        v, f = _tube((sx * 0.11, 0.0, 0.92), (sx * 0.20, 0.0, 0.12), 0.070, sides=10)
        objs.append(add_mesh(f"DEBUG_Leg_{side}", v, f, "M_Debug", colls["DEBUG"]))
        v, f = ellipsoid(14, 10, (sx * 0.215, -0.08, 0.09), (0.075, 0.130, 0.045))
        objs.append(add_mesh(f"DEBUG_Foot_{side}", v, f, "M_Debug", colls["DEBUG"]))
    for o in objs:
        o.hide_render = True          # only shown in the cutaway render
    return objs


def render_wearer_cutaway(cam, shell, wearer):
    """Bisect the suit open and show the performer inside (spec 3.3)."""
    scene = bpy.context.scene
    cut = shell.copy()
    cut.data = shell.data.copy()
    cut.name = "_Cutaway"
    cut.data.name = "_Cutaway"
    scene.collection.objects.link(cut)
    bm = bmesh.new()
    bm.from_mesh(cut.data)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                           plane_co=(0.0, 0.0, 0.0), plane_no=(0.0, 1.0, 0.0),
                           clear_inner=True)
    bm.to_mesh(cut.data)
    bm.free()
    for poly in cut.data.polygons:
        poly.use_smooth = True

    hidden = []
    for o in bpy.data.objects:
        if o.type == "MESH" and o is not cut and o.name.startswith(("SUIT_", "PROP_", "INNER_", "DUCKSHOE_")):
            hidden.append(o)
            o.hide_render = True
    for o in wearer:
        o.hide_render = False
    place_camera(cam, (-3.4, -4.6, 1.55), (0.0, 0.0, 0.95), 2.30)
    render_to(RENDERS / "v2_wearer_cutaway.png")

    for o in hidden:
        o.hide_render = False
    for o in wearer:
        o.hide_render = True
    bpy.data.objects.remove(cut, do_unlink=True)


# --------------------------------------------------------------------------
# Stats / verification
# --------------------------------------------------------------------------
def tri_count(obj):
    return sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons)


RUN_POSE = dict(
    shell_lift=0.265,
    shell_tilt=-6.0,
    legs={
        "thigh_L": ((1, 0, 0), -20), "shin_L": ((1, 0, 0), 25), "foot_L": ((1, 0, 0), -5),
        "thigh_R": ((1, 0, 0), 15), "shin_R": ((1, 0, 0), 18), "foot_R": ((1, 0, 0), -33),
    },
    arms={"arm_L": ((1, 0, 0), -16), "arm_R": ((1, 0, 0), 16)},
)


def collect_stats(mesh_objs, arm_obj, actions):
    import json
    per = {o.name: {"tris": tri_count(o), "verts": len(o.data.vertices)} for o in mesh_objs}
    body = [o for o in mesh_objs if not o.name.startswith("PROP_")]
    all_v = [o.matrix_world @ v.co for o in body for v in o.data.vertices]
    xs = [v.x for v in all_v]
    ys = [v.y for v in all_v]
    zs = [v.z for v in all_v]
    stats = {
        "total_tris": sum(d["tris"] for d in per.values()),
        "objects": per,
        "bounds": {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)],
                   "z": [min(zs), max(zs)]},
        "height": max(zs) - min(zs),
        "width": max(xs) - min(xs),
        "depth": max(ys) - min(ys),
        "bones": len(arm_obj.data.bones),
        "bone_names": [b.name for b in arm_obj.data.bones],
        "actions": [a.name for a in actions],
    }
    print("STATS:" + json.dumps(stats, ensure_ascii=False))
    return stats


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    for d in (RENDERS, BLENDS, EXPORTS):
        d.mkdir(parents=True, exist_ok=True)

    clean_scene()
    build_materials()
    setup_fabric_material()
    colls = make_collections()

    shell = build_shell(colls)
    bill = build_bills(colls)
    eyes = build_eyes(colls)
    shoes = build_shoes(colls)
    legs = build_legs(colls)
    hair = build_hair(colls)
    pelvis = build_pelvis(colls)
    sign = build_sign(colls)
    wearer = build_wearer(colls)

    arm_obj = build_armature(colls)

    bind_suit(colls, arm_obj, shell, list(eyes.values()))
    # bill: upper half follows the shell, lower half follows the jaw
    add_vertex_groups(bill, [{"shell": 1.0 - w, "jaw": w} for w in
                             [_smoothstep((bill_seam_z(v.co.x) - v.co.z) / 0.02)
                              for v in bill.data.vertices]])
    bind(bill, arm_obj, None)
    bind_legs(arm_obj, legs, hair)
    bind_rigid(arm_obj, pelvis, "pelvis")
    bind_rigid(arm_obj, sign, "sign_socket")
    for side in ("L", "R"):
        bind_rigid(arm_obj, shoes[side], f"foot_{side}")

    cam = setup_render_rig(colls)
    setup_world()

    mesh_objs = [shell, bill] + list(eyes.values()) + list(shoes.values()) \
        + list(legs.values()) + [hair, pelvis, sign]

    # ---- idle pose renders ----
    apply_pose(arm_obj)
    render_all_views(cam, sign)

    # ---- run / reveal pose render ----
    apply_pose(arm_obj, **RUN_POSE)
    place_camera(cam, (-3.2, -4.2, 1.55), (0, 0, 0.95), 2.35)
    sign.hide_render = True
    render_to(RENDERS / "v2_run_reveal.png")

    # ---- prop check: sign held at the right side (wider frame) ----
    apply_pose(arm_obj)
    sign.hide_render = False
    place_camera(cam, (-3.6, -4.5, 1.60), (0, 0, 0.95), 3.00)
    render_to(RENDERS / "v2_sign_pose.png")

    # ---- reference-matched front view ----
    render_ref_match(cam, arm_obj, sign)

    # ---- macro detail shots (fabric, hem, armhole, mouth) ----
    apply_pose(arm_obj)
    render_details(cam, arm_obj)

    # ---- cutaway: performer inside the suit ----
    apply_pose(arm_obj)
    render_wearer_cutaway(cam, shell, wearer)

    # ---- animations ----
    actions = build_actions(arm_obj)

    # ---- stats on rest pose ----
    apply_pose(arm_obj)
    bpy.context.view_layer.update()
    stats = collect_stats(mesh_objs, arm_obj, actions)

    # ---- save .blend ----
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 60
    bpy.context.scene.frame_set(1)
    blend_path = BLENDS / "eliz_costume_v2.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    # ---- export GLB (asset only, no render rig) ----
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objs + [arm_obj]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    glb_path = EXPORTS / "eliz_costume_v2.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_yup=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print(f"SAVED:{blend_path}")
    print(f"EXPORTED:{glb_path}")
    print(f"TRIS:{stats['total_tris']} HEIGHT:{stats['height']:.3f}")


if __name__ == "__main__":
    main()
