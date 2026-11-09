"""Measure how much the suit shell actually deforms during the `run` action.

Opens the saved v2 blend, evaluates SUIT_Shell at several frames and reports:

  * pairwise vertex distances vs frame 1 (a rigid body keeps them constant)
  * world bbox extents per frame
  * lowest hem point per frame

Usage:
    blender --background --factory-startup --python-exit-code 1 \
        --python scripts/probe_shell_rigidity.py
"""

import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "art" / "blender" / "eliz_costume_v2.blend"
FRAMES = (1, 4, 7, 10, 13, 16, 19, 22)
PAIRS = 400


def evaluated_world_coords(obj, depsgraph):
    ev = obj.evaluated_get(depsgraph)
    mesh = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in mesh.vertices]
    ev.to_mesh_clear()
    return pts


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    arm = bpy.data.objects.get("RIG_Eliz")
    shell = bpy.data.objects.get("SUIT_Shell")
    if arm is None or shell is None:
        raise SystemExit("missing RIG_Eliz or SUIT_Shell")

    act = bpy.data.actions.get("run")
    if act is None:
        raise SystemExit("missing run action")
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    slots = list(getattr(act, "slots", []))
    if slots and hasattr(ad, "action_slot"):
        try:
            ad.action_slot = slots[0]
        except Exception as exc:
            print("WARN slot:", exc)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    snap = {}
    for f in FRAMES:
        scene.frame_set(f)
        depsgraph.update()
        snap[f] = evaluated_world_coords(shell, depsgraph)

    base = snap[FRAMES[0]]
    n = len(base)
    idx = [(i * 7919) % n for i in range(PAIRS)]
    pairs = [(idx[i], idx[(i * 13 + 7) % PAIRS]) for i in range(PAIRS)]
    d0 = [(base[a] - base[b]).length for a, b in pairs]

    print(f"verts={n}")
    print("frame  max|d-d1|  bbox_x  bbox_y  bbox_z  min_z  shell_loc_z")

    for f in FRAMES:
        pts = snap[f]
        worst = 0.0
        for k, (a, b) in enumerate(pairs):
            if a == b:
                continue
            d = (pts[a] - pts[b]).length
            worst = max(worst, abs(d - d0[k]))
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        zs = [p.z for p in pts]
        pb = arm.pose.bones["shell"]
        loc = (arm.matrix_world @ pb.matrix).translation
        print(
            f"{f:5d}  {worst:.6f}  {max(xs)-min(xs):.4f}  {max(ys)-min(ys):.4f}"
            f"  {max(zs)-min(zs):.4f}  {min(zs):.4f}  {loc.z:.4f}"
        )

    # scale check: any non-uniform bone scale would already soften the shell
    scales = []
    for f in FRAMES:
        scene.frame_set(f)
        scales.append(tuple(round(v, 4) for v in arm.pose.bones["shell"].scale))
    print("shell_scale_frames:", scales)


if __name__ == "__main__":
    main()
