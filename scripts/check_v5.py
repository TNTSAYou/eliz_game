"""v5 acceptance: cloth folds, smooth material, morph actions, GLB animation."""
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "art" / "blender" / "eliz_costume_v5.blend"
GLB = ROOT / "art" / "exports" / "eliz_costume_v5.glb"
FAIL = []


def check(name, ok, detail=""):
    print(("OK   " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))
    if not ok:
        FAIL.append(name)


bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
shell = bpy.data.objects["SUIT_Shell"]
arm = bpy.data.objects["RIG_Eliz"]
ks = shell.data.shape_keys
keys = [k for k in ks.key_blocks if k.name.startswith("fold_")]
check("8 fold shape keys", len(keys) == 8, str([k.name for k in keys]))

basis = ks.key_blocks["Basis"].data
stats = []
for k in keys:
    ds = [(k.data[i].co - basis[i].co).length for i in range(len(shell.data.vertices))]
    ds.sort()
    stats.append((ds[len(ds) // 2], ds[len(ds) * 9 // 10], ds[-1]))
    print(f"  {k.name}: p90 {ds[len(ds)*9//10]*1000:.1f} mm max {ds[-1]*1000:.1f} mm")
check("fold p90 >= 13 mm", all(s[1] >= 0.013 for s in stats),
      f"min p90 {min(s[1] for s in stats)*1000:.1f} mm")
check("fold max <= 260 mm", all(s[2] <= 0.260 for s in stats),
      f"max {max(s[2] for s in stats)*1000:.1f} mm")

# radial fold count in the skirt band
k = keys[0]
bands = []
for i, v in enumerate(shell.data.vertices):
    if 0.42 < basis[i].co.z < 0.48:
        p, q = basis[i].co, k.data[i].co
        bands.append((math.degrees(math.atan2(p.y / 0.82, p.x)) % 360.0,
                      math.hypot(q.x, q.y / 0.82) - math.hypot(p.x, p.y / 0.82)))
bands.sort()
vals = [d for _, d in bands]
mean = sum(vals) / len(vals)
vals = [v - mean for v in vals]
n = len(vals)
for _ in range(2):
    vals = [(vals[i - 1] + 2 * vals[i] + vals[(i + 1) % n]) / 4 for i in range(n)]
peaks = sum(1 for i in range(n) if vals[i] > vals[i - 1] and vals[i] >= vals[(i + 1) % n]
            and vals[i] > 0.004)
check("6-12 radial folds at z~0.45", 6 <= peaks <= 12, f"{peaks} peaks, n={n}")

mat = bpy.data.materials["M_Suit"]
bsdf = mat.node_tree.nodes["Principled BSDF"]
check("no plush sheen", abs(bsdf.inputs["Sheen Weight"].default_value) < 1e-4)
check("no fibre normal map", not any(l.to_node == bsdf and l.to_socket.name == "Normal"
                                     for l in mat.node_tree.links))
check("smooth roughness 0.55-0.70", 0.55 <= bsdf.inputs["Roughness"].default_value <= 0.70,
      f"{bsdf.inputs['Roughness'].default_value:.2f}")

run_m = bpy.data.actions.get("run_morph")
idle_m = bpy.data.actions.get("idle_morph")
check("morph actions exist", bool(run_m and idle_m))

def values(act, frame):
    out = []
    for k in keys:
        fc = None
        for fcu in act.fcurves:
            if fcu.data_path == f'key_blocks["{k.name}"].value':
                fc = fcu
        out.append(fc.evaluate(frame) if fc else 0.0)
    return out

for f in (1, 4, 10, 16, 22, 25):
    w = values(run_m, f)
    check(f"run weights sum 1 at f{f}", abs(sum(w) - 1.0) < 1e-4, str([round(x, 2) for x in w]))
loop = all(abs(a - b) < 1e-5 for a, b in zip(values(run_m, 1), values(run_m, 25)))
check("run morph loops f1==f25", loop)
check("idle uses neutral drape key", abs(values(idle_m, 1)[0] - 1.0) < 1e-5
      and all(abs(x) < 1e-5 for x in values(idle_m, 1)[1:]), str(values(idle_m, 1)))

arm_tracks = {t.name for t in arm.animation_data.nla_tracks}
morph_tracks = {t.name for t in ks.animation_data.nla_tracks}
check("NLA tracks idle+run on rig", {"idle", "run"} <= arm_tracks, str(sorted(arm_tracks)))
check("NLA tracks idle+run on morphs", {"idle", "run"} <= morph_tracks, str(sorted(morph_tracks)))

# GLB
data = GLB.read_bytes()
off = 12
js = None
bin_chunk = None
while off < len(data):
    clen, ctype = struct.unpack_from("<II", data, off)
    off += 8
    chunk = data[off:off + clen]
    if ctype == 0x4E4F534A:
        js = json.loads(chunk)
    elif ctype == 0x004E4942:
        bin_chunk = chunk
    off += clen


def accessor(index):
    a = js["accessors"][index]
    bv = js["bufferViews"][a["bufferView"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
    return list(struct.unpack_from("<" + "f" * (a["count"] * ncomp), bin_chunk, start))


check("GLB <= 4 MB", len(data) <= 4 * 1024 * 1024, f"{len(data)/1048576:.2f} MB")
shell_mesh = next(m for m in js["meshes"] if m["name"] == "SUIT_Shell")
check("GLB shell has 8 morph targets", len(shell_mesh["primitives"][0]["targets"]) == 8)
anims = {a["name"]: a for a in js.get("animations", [])}
check("GLB idle+run", {"idle", "run"} <= set(anims), str(sorted(anims)))
for name in ("idle", "run"):
    paths = [c["target"]["path"] for c in anims[name]["channels"]]
    check(f"GLB {name} has weights channel", "weights" in paths,
          f"{len(anims[name]['channels'])} channels")


def weights_of(name):
    for ch in anims[name]["channels"]:
        if ch["target"]["path"] == "weights":
            s = anims[name]["samplers"][ch["sampler"]]
            w = accessor(s["output"])
            return w
    return []


w_idle = weights_of("idle")
w_run = weights_of("run")
n_keys = len(keys)
neutral = [1.0] + [0.0] * (n_keys - 1)
check("GLB idle weights = neutral drape", w_idle[:n_keys] == neutral,
      str([round(x, 2) for x in w_idle[:n_keys]]))
check("GLB run weights vary and loop", (max(w_run) - min(w_run)) > 0.9
      and w_run[:n_keys] == w_idle[:n_keys] and w_run[-n_keys:] == w_idle[:n_keys],
      f"range {min(w_run):.2f}..{max(w_run):.2f}")
check("GLB 32 joints", len(js["skins"][0]["joints"]) == 32)

print("\nCHECK_V5_" + ("OK" if not FAIL else "FAILED"))
if FAIL:
    raise SystemExit("failed: " + ", ".join(FAIL))

