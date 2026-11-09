"""Check the actual vertex-group weights on SUIT_Shell: which regions the
arm bones own, and whether the hem is accidentally arm-driven.
"""

from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "art" / "blender" / "eliz_costume_v2.blend"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    shell = bpy.data.objects["SUIT_Shell"]
    names = [g.name for g in shell.vertex_groups]
    print("groups:", names)
    idx = {g.index: g.name for g in shell.vertex_groups}

    low_arm = 0
    low_total = 0
    worst = (0.0, None)
    high_arm = 0
    for v in shell.data.vertices:
        w = {idx[g.group]: g.weight for g in v.groups}
        arm = max(w.get("arm_L", 0.0), w.get("arm_R", 0.0))
        if v.co.z < 0.60:
            low_total += 1
            if arm > 0.02:
                low_arm += 1
                if arm > worst[0]:
                    worst = (arm, (round(v.co.x, 3), round(v.co.y, 3), round(v.co.z, 3)))
        if v.co.z > 1.2 and arm > 0.02:
            high_arm += 1
    print(f"verts below z=0.60: {low_total}, with arm weight>0.02: {low_arm}")
    print(f"worst low arm weight: {worst[0]:.3f} at {worst[1]}")
    print(f"verts above z=1.20 with arm weight>0.02: {high_arm}")


if __name__ == "__main__":
    main()
