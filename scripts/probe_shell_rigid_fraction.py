"""Second probe: how much of SUIT_Shell follows the shell bone rigidly?

For each frame, fit the rigid transform from frame 1 to frame f using the
`shell` pose bone, then measure the residual per vertex.  A cloth-like suit
would show a large, smooth residual field; a hard shell shows ~0 everywhere
except the sleeve blend.
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
    slots = list(getattr(act, "slots", []))
    if slots:
        ad.action_slot = slots[0]

    dg = bpy.context.evaluated_depsgraph_get()
    scene.frame_set(1)
    dg.update()
    p1 = coords(shell, dg)
    M1 = (arm.matrix_world @ arm.pose.bones["shell"].matrix).copy()

    for f in FRAMES:
        scene.frame_set(f)
        dg.update()
        pf = coords(shell, dg)
        Mf = arm.matrix_world @ arm.pose.bones["shell"].matrix
        R = Mf @ M1.inverted()
        res = [(R @ p) - q for p, q in zip(p1, pf)]
        mags = sorted(v.length for v in res)
        n = len(mags)
        over1 = sum(1 for m in mags if m > 0.001)
        over5 = sum(1 for m in mags if m > 0.005)
        over20 = sum(1 for m in mags if m > 0.02)
        # z range of the deformed verts
        zs = [p1[i].z for i, v in enumerate(res) if v.length > 0.005]
        print(
            f"f{f:02d} max={mags[-1]:.4f} mean={sum(mags)/n:.5f} "
            f">1mm={over1/n*100:.1f}% >5mm={over5/n*100:.1f}% >20mm={over20/n*100:.1f}%"
            f" z_range_of_deformed={min(zs):.2f}-{max(zs):.2f}" if zs else f"f{f:02d} rigid"
        )


if __name__ == "__main__":
    main()
