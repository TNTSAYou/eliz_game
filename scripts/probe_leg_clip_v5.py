"""Leg-through-cloth test for v5 (includes the baked fold morphs).

Two numbers:
  * through  = a limb vertex outside the suit's OUTER wall (visible poke-through)
  * contact  = a limb vertex inside the fabric thickness (inner..outer wall)

v5.2 (KI-01): every limb vertex above the hem opening is tested, including the
shoes.  Before this, the probe skipped everything below z=0.20 m, which is
exactly where the shoes live, so it reported OK while a shoe poked 19 cm out.
Acceptance: through == 0, contact depth <= 8 mm.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "art" / "blender" / "eliz_costume_v5.blend"
MARGIN = 0.004
MAX_CONTACT = 0.008
MAX_THROUGH = 0


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
    frames = []
    through_total = 0
    contact_total = 0
    deepest = 0.0
    for f in range(1, 25):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        shell_pts = eval_pts(shell)
        hem_z = min(p.z for p in shell_pts)
        through = contact = 0
        worst = 0.0
        for obj in inner:
            for p in eval_pts(obj):
                # only the fabric above the hem opening can be pierced
                if p.z < hem_z + 0.008:
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
                if r_in is None:
                    continue
                if r_out is not None and r_v > r_out:
                    through += 1
                    worst = max(worst, r_v - r_out)
                elif r_in - MARGIN < r_v < (r_out if r_out is not None else r_in):
                    contact += 1
                    deepest = max(deepest, min(r_v - r_in,
                                               (r_out - r_v) if r_out is not None else 0.0))
        through_total += through
        contact_total += contact
        frames.append({"f": f, "through": through, "contact": contact,
                       "worst_mm": round(worst * 1000, 1)})

    print("CLIP_V5:" + json.dumps({"through": through_total, "contact": contact_total,
                                   "deepest": round(deepest, 4), "frames": frames}))
    ok = through_total <= MAX_THROUGH and deepest <= MAX_CONTACT
    print("CLIP_V5_" + ("OK" if ok else "FAILED"))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
