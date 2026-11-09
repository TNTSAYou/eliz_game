"""Leg-through-cloth test for the run cycle.

For every run frame, and for every leg / hair / shoe vertex that sits above the
hem line, cast a ray from the body axis outwards through that vertex:

  * first hit = the suit's inner wall  -> the vertex is inside the cavity
  * no hit, or the wall is closer than the vertex -> the leg pokes through

Prints CLIP:<json> and exits non-zero when any vertex is outside.
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

BLEND = ROOT / "art" / "blender" / "eliz_costume_v2.blend"
MARGIN = 0.004


def eval_pts(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    arm = bpy.data.objects["RIG_Eliz"]
    shell = bpy.data.objects["SUIT_Shell"]
    act = bpy.data.actions["run"]
    ad = arm.animation_data
    ad.action = act
    slots = list(getattr(act, "slots", []))
    if slots:
        ad.action_slot = slots[0]

    inner = [o for o in bpy.data.objects
             if o.name.startswith(("INNER_Leg", "INNER_Hair", "DUCKSHOE"))]

    worst = []
    total = 0
    for f in range(1, 25):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        shell_pts = eval_pts(shell)
        hem_z = min(p.z for p in shell_pts)
        bad = 0
        deepest = 0.0
        for obj in inner:
            for k, p in enumerate(eval_pts(obj)):
                if k % 5:
                    continue
                if p.z < hem_z + 0.01:
                    continue
                d = Vector((p.x, p.y, 0.0))
                if d.length < 1e-4:
                    continue
                d.normalize()
                origin = Vector((0.0, 0.0, p.z))
                # walk outwards collecting the cloth's inner and outer walls;
                # a limb between them is inside the fabric (real clipping)
                r_in = r_out = None
                o = origin
                for _ in range(12):
                    hit, loc, _n, _i, ob, _m = scene.ray_cast(dg, o, d)
                    if not hit:
                        break
                    if ob.name == "SUIT_Shell":
                        rr = (loc - origin).length
                        if r_in is None:
                            r_in = rr
                        else:
                            r_out = rr
                            break
                    o = loc + d * 0.002
                r_v = (p - origin).length
                if r_in is not None and r_out is not None and r_in - MARGIN < r_v < r_out + MARGIN:
                    bad += 1
                    deepest = max(deepest, min(r_v - r_in, r_out - r_v))
        total += bad
        worst.append({"f": f, "bad": bad, "deepest": round(deepest, 4)})

    print("CLIP:" + json.dumps({"total": total, "frames": worst}))
    if total:
        raise SystemExit(f"CLIP FAILED: {total} leg vertices outside the suit")


if __name__ == "__main__":
    main()
