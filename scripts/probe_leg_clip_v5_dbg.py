"""Leg-through-cloth test for v5 (includes the baked fold morphs)."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "art" / "blender" / "eliz_costume_v5.blend"
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
    shell.data.shape_keys.animation_data.action = bpy.data.actions["run_morph"]

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
                    bad += 1\n                    print("BAD", f, obj.name, tuple(round(x,3) for x in p), "r_v", round(r_v,3), "r_in", round(r_in,3), "r_out", round(r_out,3))\n                    deepest = max(deepest, min(r_v - r_in, r_out - r_v))
        total += bad
        worst.append({"f": f, "bad": bad, "deepest": round(deepest, 4)})

    print("CLIP:" + json.dumps({"total": total, "frames": worst}))
    print("CLIP_V5_" + ("OK" if total == 0 else "FAILED"))


if __name__ == "__main__":
    main()

