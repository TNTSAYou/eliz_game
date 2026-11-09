"""Third probe: does the mis-weighted hem (arm-driven verts) actually move?

Reports, per frame, the residual vs the `shell` rigid transform for vertices
below z=0.40 (the skirt) and for the sleeve region, separately.
"""

from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "art" / "blender" / "eliz_costume_v2.blend"
FRAMES = (1, 7, 13, 19)


def coords(obj, dg):
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
    if list(getattr(act, "slots", [])):
        ad.action_slot = list(act.slots)[0]

    dg = bpy.context.evaluated_depsgraph_get()
    scene.frame_set(1)
    dg.update()
    p1 = coords(shell, dg)
    z1 = [v.co.z for v in shell.data.vertices]
    M1 = (arm.matrix_world @ arm.pose.bones["shell"].matrix).copy()

    hem = [i for i, z in enumerate(z1) if z < 0.40]
    body = [i for i, z in enumerate(z1) if 0.40 <= z <= 1.30]
    print(f"hem verts={len(hem)} body verts={len(body)}")

    for f in FRAMES:
        scene.frame_set(f)
        dg.update()
        pf = coords(shell, dg)
        R = (arm.matrix_world @ arm.pose.bones["shell"].matrix) @ M1.inverted()
        def stats(sel):
            mags = [((R @ p1[i]) - pf[i]).length for i in sel]
            return max(mags), sum(mags) / len(mags)
        hm, ha = stats(hem)
        bm, ba = stats(body)
        print(f"f{f:02d} hem max={hm:.4f} mean={ha:.5f} | body max={bm:.4f} mean={ba:.5f}")


if __name__ == "__main__":
    main()
