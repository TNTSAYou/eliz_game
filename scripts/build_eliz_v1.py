"""Build the Elizabeth "mascot costume" blockout (v1) from docs/character_spec.md.

Run (PowerShell):
    & "D:\\tools\\blender-4.5.15-windows-x64\\blender.exe" --background --factory-startup `
        --python-exit-code 1 --python "D:\\work\\eliz_game\\scripts\\build_eliz_v1.py"

Outputs (all under art/):
    blender/eliz_costume_v1.blend
    exports/eliz_costume_v1.glb
    renders/v1_front.png, v1_side.png, v1_back.png, v1_three_quarter.png, v1_run_reveal.png

Conventions: meters, Z up, character faces -Y, feet on Z=0.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "art"
BLENDS = ART / "blender"
EXPORTS = ART / "exports"
RENDERS = ART / "renders"

FPS = 30

# --------------------------------------------------------------------------
# Dimensions (spec section 5)
# --------------------------------------------------------------------------
TOTAL_H = 1.80

SHELL_Z0 = 0.15          # hem height (idle)
SHELL_Z1 = 1.80          # top
BODY_R = 0.425           # half width -> 0.85 wide
DEPTH_RATIO = 0.70 / 0.85
SHELL_T = 0.020
DOME_C = 1.03            # dome origin, measured from art/refs/eliz_front.jpg
DOME_H = 0.77            # dome height above DOME_C
DOME_P = 0.50            # dome profile exponent (0.5 = smooth apex)
HEM_FLARE = 1.02
RIM_RX = 0.250           # visible opening half width  -> 0.50 wide
RIM_RY = 0.190           # visible opening half depth  -> 0.38 deep


BILL_Z = 1.310
BILL_W = 0.140           # half width  -> 0.28
EYE_Z = 1.440
EYE_R = 0.065            # 0.13 diameter
EYE_X = 0.090            # +-0.09 -> 0.18 spacing
PUPIL_R = 0.0125
LASH_LEN = 0.040

ARM_Z0 = 1.080
ARM_Z1 = 0.620
ARM_X = 0.470
ARM_RX = 0.072           # front view width 0.14
ARM_RY = 0.035

SHOE_X = 0.100
SHOE_LEN_F = 0.215       # toe reach ahead of ankle
SHOE_LEN_B = 0.150       # heel behind ankle
SHOE_HALF_W = 0.110
SHOE_TOP = 0.100
ANKLE_COLLAR_TOP = 0.150

HIP_Z = 0.900
KNEE_Z = 0.500
ANKLE_Z = 0.120
THIGH_R = 0.090
CALF_R = 0.072

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
    "M_Bill":      ("#FBC55B", 0.55),
    "M_BillLower": ("#D99A2B", 0.55),
    "M_EyeWhite":  ("#FFFFFF", 0.20),
    "M_Pupil":     ("#111111", 0.30),
    "M_Line":      ("#2B2B2B", 0.60),
    "M_Skin":      ("#C98E6B", 0.65),
    "M_Hair":      ("#2A211C", 0.70),
    "M_Shorts":    ("#3A3A3A", 0.85),
    "M_Sign":      ("#F7F5EE", 0.80),
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
    for name in ("SUIT", "INNER", "PROPS", "RIG", "RENDER"):
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
    """Outer half width at height z (capsule body + reference-measured dome)."""
    if z >= DOME_C:
        u = min(1.0, (z - DOME_C) / DOME_H)
        return BODY_R * max(0.0, 1.0 - u * u) ** DOME_P
    flare = 1.0 + (HEM_FLARE - 1.0) * (1.0 - _smoothstep((z - SHELL_Z0) / 0.15))
    return BODY_R * flare


def shell_radius(z):
    r = body_r(z)
    return (r, r * DEPTH_RATIO)


FUNNEL = [(0.250, 0.168), (0.280, 0.195), (0.320, 0.250),
          (0.360, 0.330), (0.405, 0.400)]


def inner_r(z):
    """Inner wall radius; the hem funnel blends into the wall."""
    if z >= FUNNEL[-1][1]:
        return max(0.02, body_r(z) - SHELL_T)
    for (r0, z0), (r1, z1) in zip(FUNNEL, FUNNEL[1:]):
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return r0 + (r1 - r0) * t
    return FUNNEL[0][0]


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


def build_shell(colls):
    seg = 36
    zs_body = [0.150, 0.165, 0.185, 0.210, 0.245, 0.285, 0.330, 0.385,
               0.450, 0.525, 0.610, 0.705, 0.805, 0.910, 1.010, 1.050]
    profile = [(body_r(z), z) for z in zs_body]
    n = 11
    us = [math.sin(math.pi / 2.0 * i / n) for i in range(1, n + 1)]
    for u in us:
        z = DOME_C + DOME_H * u
        profile.append((body_r(z), z))          # last point is the apex pole
    for u in reversed(us[1:]):
        z = DOME_C + DOME_H * u
        profile.append((max(0.02, body_r(z) - SHELL_T), z))
    for z in reversed(zs_body[::2][1:]):
        profile.append((max(0.02, body_r(z) - SHELL_T), z))
    profile += list(reversed(FUNNEL))
    profile += [(0.300, 0.152), (0.370, 0.148)]
    verts, faces = _revolve(profile, seg)
    shell = add_mesh("SUIT_Shell", verts, faces, "M_Suit", colls["SUIT"])
    recalc_normals(shell)
    for poly in shell.data.polygons:
        poly.use_smooth = True

    # rolled hem band around the rim (reads as the costume's hem edge)
    rx = body_r(SHELL_Z0)
    hv, hf = _elliptic_torus(rx, rx * DEPTH_RATIO, 0.013, seg, 6, SHELL_Z0 + 0.002)
    hem = add_mesh("SUIT_Hem", hv, hf, "M_Suit", colls["SUIT"])
    return shell, hem


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


def build_liner(colls):
    seg = 32
    zs = [0.168, 0.200, 0.240, 0.290, 0.350, 0.430, 0.520, 0.630, 0.760, 0.880]
    profile = []
    for z in zs:
        r = max(0.03, inner_r(z) - 0.006)
        profile.append((z, r, r * DEPTH_RATIO))
    verts, faces = lathe(profile, seg, cap_top=True, top_z=0.980)
    return add_mesh("SUIT_Liner", verts, faces, "M_Liner", colls["SUIT"])


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
    """Half-ellipsoid dome with a flat base at z=cz (a duck-bill half)."""
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
        z = cz + (h if up else -h) * math.sqrt(1.0 - u * u)
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


def build_bills(colls):
    uv, uf = _pancake(0.0, -0.345, 1.345, 0.140, 0.085, 0.038, up=True)
    upper = add_mesh("SUIT_Bill_Upper", uv, uf, "M_Bill", colls["SUIT"])
    lv, lf = _pancake(0.0, -0.335, 1.338, 0.132, 0.078, 0.024, up=False)
    lower = add_mesh("SUIT_Bill_Lower", lv, lf, "M_BillLower", colls["SUIT"])
    mv, mf = _flat_disc(0.0, -0.340, 1.3415, 0.134, 0.079)
    mouth = add_mesh("SUIT_Mouth_Line", mv, mf, "M_Line", colls["SUIT"])
    return upper, lower, mouth


def build_eyes(colls):
    objs = {}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        cx = sx * EYE_X
        ev, ef = disc_on_surface(cx, EYE_Z, EYE_R, 0.004, rings=3, segs=24)
        objs[f"eye_{side}"] = add_mesh(f"SUIT_Eye_{side}", ev, ef, "M_EyeWhite", colls["SUIT"])

        pv, pf = disc_on_surface(cx, EYE_Z, PUPIL_R, 0.010, rings=1, segs=12)
        objs[f"pupil_{side}"] = add_mesh(f"SUIT_Pupil_{side}", pv, pf, "M_Pupil", colls["SUIT"])

        rv, rf = annulus_on_surface(cx, EYE_Z, EYE_R + 0.001, EYE_R + 0.009, 0.006, segs=24)
        objs[f"rim_{side}"] = add_mesh(f"SUIT_EyeRim_{side}", rv, rf, "M_Line", colls["SUIT"])

        lv, lf = [], []
        for ang in (-0.55, 0.0, 0.55):
            ex = cx + EYE_R * 0.96 * math.sin(ang) * sx
            ez = EYE_Z + EYE_R * 0.96 * math.cos(ang)
            base = Vector((ex, surface_y(ex, ez) - 0.006, ez))
            direction = Vector((math.sin(ang) * 0.55 * sx, -0.12, math.cos(ang))).normalized()
            v, f = cone(base, direction, LASH_LEN, 0.006, 0.0008, sides=4)
            off = len(lv)
            lv += v
            lf += [tuple(i + off for i in face) for face in f]
        objs[f"lash_{side}"] = add_mesh(f"SUIT_Lash_{side}", lv, lf, "M_Line", colls["SUIT"])
    return objs


def build_arms(colls):
    objs = {}
    seg, rings = 14, 9
    for side, sx in (("L", 1.0), ("R", -1.0)):
        profile = []
        for i in range(rings):
            t = i / (rings - 1)                   # 0 top -> 1 tip
            z = ARM_Z0 + (ARM_Z1 - ARM_Z0) * t
            r = max(0.10, (1.0 - t ** 2.0) ** 0.6)
            profile.append((z, ARM_RX * r, ARM_RY * r))
        verts, faces = lathe(profile, seg, cap_top=True, cap_bottom=True)
        verts = [(x + sx * (0.470 + 0.015 * (ARM_Z0 - z) / (ARM_Z0 - ARM_Z1)),
                  y, z) for (x, y, z) in verts]
        objs[side] = add_mesh(f"SUIT_Arm_{side}", verts, faces, "M_Suit", colls["SUIT"])
    return objs


def _shoe_outline(theta):
    """Polar radius of a webbed duck foot. theta 0 = forward (-Y)."""
    base = 0.145
    toe = 0.0
    for ang in (-0.56, 0.0, 0.56):
        d = (theta - ang + math.pi) % (2 * math.pi) - math.pi
        toe += 0.070 * math.exp(-(d / 0.26) ** 2)
    r = base + toe
    if abs(theta) > math.pi * 0.72:
        r = max(r, 0.145)
    return r


def build_shoes(colls):
    objs = {}
    seg = 36
    us = (0.2, 0.4, 0.6, 0.8, 1.0)
    for side, sx in (("L", 1.0), ("R", -1.0)):
        x0 = sx * SHOE_X
        y0 = 0.010
        verts, faces = [], []
        rings = []
        rot = -sx * 0.35   # toes splayed outwards
        ca, sa = math.cos(rot), math.sin(rot)
        for u in us:
            ring = []
            for j in range(seg):
                theta = 2.0 * math.pi * j / seg
                R = _shoe_outline(theta) * u
                toe = 0.0
                for ang in (-0.56, 0.0, 0.56):
                    d = (theta - ang + math.pi) % (2 * math.pi) - math.pi
                    toe += 0.030 * math.exp(-(d / 0.30) ** 2)
                h = 0.020 + toe * (0.35 + 0.65 * u) + 0.095 * (1.0 - u) ** 2.2
                dx, dy = R * math.sin(theta), -R * math.cos(theta)
                ring.append(len(verts))
                verts.append((x0 + dx * ca - dy * sa, y0 + dx * sa + dy * ca, h))
            rings.append(ring)
        apex = len(verts)
        verts.append((x0, y0, 0.100))
        for j in range(seg):
            faces.append((apex, rings[0][j], rings[0][(j + 1) % seg]))
        for a, b in zip(rings, rings[1:]):
            for j in range(seg):
                faces.append((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
        # side wall down to the ground
        rim = rings[-1]
        bottom = []
        for j in range(seg):
            x, y, _ = verts[rim[j]]
            bottom.append(len(verts))
            verts.append((x, y, 0.0))
        for j in range(seg):
            faces.append((rim[j], rim[(j + 1) % seg],
                          bottom[(j + 1) % seg], bottom[j]))
        sole_c = len(verts)
        verts.append((x0, y0, 0.0))
        for j in range(seg):
            faces.append((sole_c, bottom[(j + 1) % seg], bottom[j]))
        # ankle cuff (covers the leg down to the shoe)
        cv, cf = _collar(x0, 0.0)   # ankle opening centred on the leg
        off = len(verts)
        verts += cv
        faces += [tuple(i + off for i in f) for f in cf]
        objs[side] = add_mesh(f"DUCKSHOE_{side}", verts, faces, "M_Bill", colls["SUIT"])
    return objs


def _collar(x0, y0):
    seg = 20
    profile = [(0.050, 0.064, 0.064), (0.100, 0.060, 0.060), (0.162, 0.054, 0.054)]
    verts, faces = lathe(profile, seg, cap_top=False, cap_bottom=False)
    verts = [(x + x0, y + y0, z) for (x, y, z) in verts]
    return verts, faces


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
        for k in range(18):
            z = 0.190 + 0.024 * k
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
    start = Vector((-0.490, 0.000, ARM_Z1 + 0.020))
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
    ("shell", (0, 0, HIP_Z), (0, 0, SHELL_Z1), "pelvis"),
    ("jaw", (0, -0.200, 1.300), (0, -0.360, 1.285), "shell"),
    ("arm_L", (ARM_X, 0, ARM_Z0), (ARM_X, 0, ARM_Z1), "shell"),
    ("arm_R", (-ARM_X, 0, ARM_Z0), (-ARM_X, 0, ARM_Z1), "shell"),
    ("sign_socket", (-0.500, 0.000, ARM_Z1 + 0.010), (-0.660, -0.040, 1.020), "arm_R"),
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


def bind_suit(colls, arm_obj, objs):
    # 100% shell
    for obj in objs:
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
        pose_translate(pb["shell"], (0, 0, 0.170 + 0.010 * math.sin(f / 24.0 * 2 * math.pi)))
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
    bg.inputs[1].default_value = 0.55


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
    scene.view_settings.look = "None"
    scene.render.fps = FPS

    cam_data = bpy.data.cameras.new("CAM_View")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 2.05
    cam = bpy.data.objects.new("CAM_View", cam_data)
    colls["RENDER"].objects.link(cam)
    scene.camera = cam

    add_light("L_Key", "SUN", (-2.5, -3.0, 4.0), 4.0, target=(0, 0, 1.0))
    add_light("L_Fill", "AREA", (2.6, -2.6, 2.2), 260.0, size=3.5, target=(0, 0, 1.0))
    add_light("L_Rim", "AREA", (0.4, 3.2, 2.8), 300.0, size=2.5, target=(0, 0, 1.2))
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


def render_all_views(cam, sign_obj=None, hide_sign_in=("front", "back", "side", "three_quarter")):
    views = [
        ("v1_front", (0, -6, 0.90), (0, 0, 0.90), 2.05),
        ("v1_side", (-6, 0, 0.90), (0, 0, 0.90), 2.05),
        ("v1_back", (0, 6, 0.90), (0, 0, 0.90), 2.05),
        ("v1_three_quarter", (-3.6, -4.0, 1.65), (0, 0, 0.92), 2.60),
    ]
    for name, loc, target, scale in views:
        short = name.split("_", 1)[1]
        if sign_obj is not None:
            sign_obj.hide_render = short in hide_sign_in
        place_camera(cam, loc, target, scale)
        render_to(RENDERS / f"{name}.png")
    if sign_obj is not None:
        sign_obj.hide_render = False


# --------------------------------------------------------------------------
# Stats / verification
# --------------------------------------------------------------------------
def tri_count(obj):
    return sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons)


RUN_POSE = dict(
    shell_lift=0.190,
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
    colls = make_collections()

    shell, hem = build_shell(colls)
    liner = build_liner(colls)
    bill_u, bill_l, mouth = build_bills(colls)
    eyes = build_eyes(colls)
    arms = build_arms(colls)
    shoes = build_shoes(colls)
    legs = build_legs(colls)
    hair = build_hair(colls)
    pelvis = build_pelvis(colls)
    sign = build_sign(colls)

    arm_obj = build_armature(colls)

    suit_objs = ([shell, hem, liner, bill_u, mouth] + list(eyes.values())
                 + list(arms.values()))
    bind_suit(colls, arm_obj, suit_objs)
    bind_rigid(arm_obj, bill_l, "jaw")
    bind_legs(arm_obj, legs, hair)
    bind_rigid(arm_obj, pelvis, "pelvis")
    bind_rigid(arm_obj, sign, "sign_socket")
    for side in ("L", "R"):
        bind_rigid(arm_obj, shoes[side], f"foot_{side}")

    cam = setup_render_rig(colls)
    setup_world()

    mesh_objs = suit_objs + [bill_l] + list(shoes.values()) + list(legs.values()) + [hair, pelvis, sign]

    # ---- idle pose renders ----
    apply_pose(arm_obj)
    render_all_views(cam, sign)

    # ---- run / reveal pose render ----
    apply_pose(arm_obj, **RUN_POSE)
    place_camera(cam, (-3.2, -4.2, 1.55), (0, 0, 0.95), 2.35)
    sign.hide_render = True
    render_to(RENDERS / "v1_run_reveal.png")

    # ---- prop check: sign held at the right side (wider frame) ----
    apply_pose(arm_obj)
    sign.hide_render = False
    place_camera(cam, (-3.6, -4.5, 1.60), (0, 0, 0.95), 3.00)
    render_to(RENDERS / "v1_sign_pose.png")

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
    blend_path = BLENDS / "eliz_costume_v1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    # ---- export GLB (asset only, no render rig) ----
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objs + [arm_obj]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    glb_path = EXPORTS / "eliz_costume_v1.glb"
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
