"""How much hairy leg is actually visible through the run cycle (v4 check).

Casts a front grid and a side grid at every run frame and reports the number
of rays that reach INNER_Leg / INNER_Hair, plus the exposed z span.  Used to
confirm the cloth flare did not swallow the leg-reveal gag.

    blender --background --factory-startup --python-exit-code 1 \
        --python scripts/probe_leg_visibility.py
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

BLEND = ROOT / "art" / "blender" / "eliz_costume_v2.blend"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    arm = bpy.data.objects["RIG_Eliz"]
    act = bpy.data.actions["run"]
    ad = arm.animation_data
    ad.action = act
    slots = list(getattr(act, "slots", []))
    if slots:
        ad.action_slot = slots[0]

    out = []
    for f in range(1, 25):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        spans = {}
        for view, origin, direction in (
            ("front", Vector((0, -6.0, 0)), Vector((0, 1, 0))),
            ("side", Vector((-6.0, 0, 0)), Vector((1, 0, 0))),
        ):
            zs = []
            for zi in range(0, 90):
                for xi in range(-14, 15):
                    if view == "front":
                        start = Vector((xi * 0.02, origin.y, 0.02 + zi * 0.06))
                    else:
                        start = Vector((origin.x, xi * 0.02, 0.02 + zi * 0.06))
                    ok, _l, _n, _i, obj, _m = scene.ray_cast(dg, start, direction)
                    if ok and obj is not None and obj.name.startswith(("INNER_Leg", "INNER_Hair")):
                        zs.append(start.z)
            spans[view] = (len(zs), round(max(zs) - min(zs), 3) if zs else 0.0)
        out.append({"f": f, "front": spans["front"], "side": spans["side"]})
    print("VIS:" + json.dumps(out))


if __name__ == "__main__":
    main()
