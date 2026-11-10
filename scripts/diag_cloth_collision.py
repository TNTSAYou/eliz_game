"""Diagnose: does the inner body (legs/shoes/hair/pelvis) intersect the coat
during the run clip?  Measures, per frame and per object, the radial gap to the
coat's INNER wall (negative = inside the fabric) and vertices outside the OUTER
wall (poke-through).

Run:
  & D:\\tools\\blender-4.5.15-windows-x64\\blender.exe --background --factory-startup `
      --python-exit-code 1 --python "scripts\\diag_cloth_collision.py"
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "art" / "blender" / "eliz_costume_v5.blend"


def world_verts(obj, dg):
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

    # ---- inventory: what actually collides ----
    print("=== COLLISION INVENTORY ===")
    for o in bpy.data.objects:
        mods = [m.type for m in o.modifiers]
        if "COLLISION" in mods:
            c = o.collision
            print(f"collider: {o.name:18s} thick_outer={c.thickness_outer:.3f} "
                  f"friction={c.cloth_friction:.1f} hide_render={o.hide_render}")
        if "CLOTH" in mods:
            cs = o.modifiers["Cloth"].collision_settings
            print(f"cloth   : {o.name:18s} use_collision={cs.use_collision} "
                  f"dist_min={cs.distance_min:.3f} self={cs.use_self_collision}")
    print("shell mods:", [(m.type, m.name) for m in shell.modifiers])
    print("shell shape keys:", [k.name for k in shell.data.shape_keys.key_blocks])
    print("=== END INVENTORY ===")

    act = bpy.data.actions["run"]
    ad = arm.animation_data
    ad.action = act
    slots = list(getattr(act, "slots", []))
    if slots:
        ad.action_slot = slots[0]
    shell.data.shape_keys.animation_data.action = bpy.data.actions["run_morph"]

    inner = [o for o in bpy.data.objects
             if o.name.startswith(("INNER_", "DUCKSHOE_"))]
    report = []
    for f in range(1, 25):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        shell_pts = world_verts(shell, dg)
        shell_zmin = min(p.z for p in shell_pts)
        row = {"f": f, "shell_zmin": round(shell_zmin, 4), "objs": {}}
        for obj in inner:
            pts = world_verts(obj, dg)
            penetrations = []
            contacts = []
            below_hem = 0
            misses = 0
            for p in pts:
                d = Vector((p.x, p.y, 0.0))
                r_v = d.length
                if r_v < 1e-4:
                    continue
                d.normalize()
                origin = Vector((0.0, 0.0, p.z))
                r_in = r_out = None
                o = origin
                for _ in range(8):
                    hit, loc, _n, _i, ob, _m = scene.ray_cast(dg, o, d, distance=3.0)
                    if not hit:
                        break
                    if ob.name == "SUIT_Shell":
                        rr = (loc - origin).length
                        if r_in is None:
                            r_in = rr
                        else:
                            r_out = rr
                            break
                    o = loc + d * 0.001
                if r_in is None:
                    if p.z < shell_zmin + 0.002:
                        below_hem += 1
                    else:
                        misses += 1
                    continue
                if r_out is not None and r_v > r_out:
                    penetrations.append(r_v - r_out)
                elif r_v > r_in - 0.002:
                    contacts.append(r_in - r_v)
            name = obj.name
            row["objs"][name] = {
                "n": len(pts),
                "outside": len(penetrations),
                "max_pen_mm": round(max(penetrations) * 1000, 2) if penetrations else 0.0,
                "contact": len(contacts),
                "nearest_gap_mm": round(min(contacts) * 1000, 2) if contacts else None,
                "below_hem": below_hem,
                "no_hit": misses,
                "zmin": round(min(p.z for p in pts), 3),
                "zmax": round(max(p.z for p in pts), 3),
            }
        report.append(row)

    print("DIAG:" + json.dumps(report))
    # ---- compact per-frame table ----
    keys = sorted({k for r in report for k in r["objs"]})
    print("frame " + " ".join(f"{k:>26s}" for k in keys))
    for r in report:
        cells = []
        for k in keys:
            d = r["objs"].get(k)
            if not d:
                cells.append(f"{'-':>26s}")
                continue
            cells.append(f"out{d['outside']:>2d}/{d['max_pen_mm']:>5.1f}mm gap{d['nearest_gap_mm']}"[:26].rjust(26))
        print(f"{r['f']:>5d} " + " ".join(cells))


if __name__ == "__main__":
    main()
