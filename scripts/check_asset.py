"""Acceptance checks for the v1 blockout (docs/character_spec.md section 11).

Run:
    & "D:\\tools\\blender-4.5.15-windows-x64\\blender.exe" --background --factory-startup `
        --python-exit-code 1 --python "D:\\work\\eliz_game\\scripts\\check_asset.py"

Opens art/blender/eliz_costume_v1.blend, measures topology / weights / pose
behaviour / front-view occlusion, prints CHECK:<json> and exits non-zero if a
hard check fails. Does not save the .blend.
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_eliz_v1 as B  # noqa: E402

BLEND = B.BLENDS / "eliz_costume_v1.blend"


def evaluated_positions(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in mesh.vertices]
    ev.to_mesh_clear()
    return pts


def centroid(pts):
    n = len(pts)
    return sum(pts, Vector()) / n


def max_delta(a, b):
    return max((p - q).length for p, q in zip(a, b))


def ngons(obj):
    return [p.index for p in obj.data.polygons if len(p.vertices) > 4]


def weight_problems(obj):
    bad = 0
    for v in obj.data.vertices:
        total = sum(g.weight for g in v.groups)
        if not v.groups or abs(total - 1.0) > 1e-3:
            bad += 1
    return bad


def ray_visible_inner(arm, pose_kwargs, samples=44):
    """Count front-view rays that hit INNER_Leg*/INNER_Hair in the given pose."""
    B.apply_pose(arm, **pose_kwargs)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    hits = {}
    total = 0
    xs = [-0.55 + 1.10 * i / samples for i in range(samples + 1)]
    zs = [0.02 + 1.76 * i / samples for i in range(samples + 1)]
    for z in zs:
        for x in xs:
            ok, _loc, _n, _i, obj, _m = scene.ray_cast(
                dg, Vector((x, -6.0, z)), Vector((0.0, 1.0, 0.0)))
            if ok and obj is not None:
                total += 1
                hits[obj.name] = hits.get(obj.name, 0) + 1
    inner = sum(v for k, v in hits.items() if k.startswith(("INNER_Leg", "INNER_Hair")))
    return inner, hits


def inner_visible_span(arm, pose_kwargs, zstep=0.004, xstep=0.010):
    """Vertical extent of INNER_Leg*/INNER_Hair that the front camera can see."""
    B.apply_pose(arm, **pose_kwargs)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    zs = [0.02 + zstep * i for i in range(int((0.95 - 0.02) / zstep))]
    xs = [xstep * i for i in range(1, 20)] + [-xstep * i for i in range(1, 20)]
    zmins, zmaxs = [], []
    for z in zs:
        for x in xs:
            ok, _loc, _n, _i, obj, _m = scene.ray_cast(
                dg, Vector((x, -6.0, z)), Vector((0.0, 1.0, 0.0)))
            if ok and obj is not None and obj.name.startswith(("INNER_Leg", "INNER_Hair")):
                zmins.append(z)
                zmaxs.append(z)
    if not zmins:
        return 0.0, 0
    return max(zmaxs) - min(zmins), len(zmins)


def action_fcurves(act):
    """F-curves of an action across Blender 4.4+ slotted actions."""
    try:
        if len(act.layers) and len(act.slots):
            bag = act.layers[0].strips[0].channelbag(act.slots[0])
            if bag is not None:
                return list(bag.fcurves)
    except Exception:
        pass
    return list(act.fcurves)


def loop_problems(arm):
    """Run cycle must start and end on the same pose (frame 1 == frame 25)."""
    act = bpy.data.actions.get("run")
    if act is None:
        return ["missing run action"]
    bad = []
    for fc in action_fcurves(act):
        pts = {round(k.co[0]): k.co[1] for k in fc.keyframe_points}
        if 1 in pts and 25 in pts and abs(pts[1] - pts[25]) > 1e-6:
            bad.append(fc.data_path)
    return bad


def main():
    if not BLEND.exists():
        raise SystemExit(f"missing blend: {BLEND}")
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))

    scene = bpy.context.scene
    arm = bpy.data.objects["RIG_Eliz"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    suit = sorted(o.name for o in meshes if o.name.startswith("SUIT_"))
    inner = sorted(o.name for o in meshes if o.name.startswith("INNER_"))

    report = {"suit": suit, "inner": inner}

    # ---- 1. asset hygiene ----
    report["ngons"] = {o.name: len(ngons(o)) for o in meshes if ngons(o)}
    report["weight_problems"] = {o.name: n for o in meshes if (n := weight_problems(o))}
    bad_xform = []
    for o in meshes:
        m = o.matrix_world
        ident = all(abs(m[i][j] - (1.0 if i == j else 0.0)) < 1e-6
                    for i in range(4) for j in range(4))
        if not ident or o.scale != Vector((1, 1, 1)):
            bad_xform.append(o.name)
    report["bad_transforms"] = bad_xform

    # shell must be 100% on the shell bone
    shell = bpy.data.objects["SUIT_Shell"]
    shell_groups = {g.name for g in shell.vertex_groups}
    shell_off_bone = sum(1 for v in shell.data.vertices
                         if [g.group for g in v.groups] !=
                         [shell.vertex_groups["shell"].index])
    report["shell_groups"] = sorted(shell_groups)
    report["shell_verts_not_pure"] = shell_off_bone

    # ---- 2. shell / leg isolation ----
    B.apply_pose(arm)
    bpy.context.view_layer.update()
    shell_rest = evaluated_positions(shell)
    leg = bpy.data.objects["INNER_Leg_L"]
    leg_rest = evaluated_positions(leg)

    B.apply_pose(arm, legs={"thigh_L": ((1, 0, 0), 40)})
    bpy.context.view_layer.update()
    shell_posed = evaluated_positions(shell)
    leg_posed = evaluated_positions(leg)
    report["shell_delta_on_leg_pose"] = round(max_delta(shell_rest, shell_posed), 6)
    report["leg_delta_on_leg_pose"] = round(max_delta(leg_rest, leg_posed), 4)

    # ---- 3. shoe follows the foot bone ----
    shoe = bpy.data.objects["DUCKSHOE_L"]
    shoe_rest = evaluated_positions(shoe)
    B.apply_pose(arm, legs={"foot_L": ((1, 0, 0), 35)})
    bpy.context.view_layer.update()
    shoe_posed = evaluated_positions(shoe)
    shell_after_foot = evaluated_positions(shell)
    report["shoe_delta_on_foot_pose"] = round(max_delta(shoe_rest, shoe_posed), 4)
    report["shell_delta_on_foot_pose"] = round(max_delta(shell_rest, shell_after_foot), 6)

    # ---- 4. jaw opens only the lower bill ----
    bill = bpy.data.objects["SUIT_Bill_Upper"]
    bill_rest = evaluated_positions(bill)
    upper_idx = [i for i, v in enumerate(bill.data.vertices) if v.co.z > 1.40]
    lower_idx = [i for i, v in enumerate(bill.data.vertices) if v.co.z < 1.25]
    B.apply_pose(arm)
    arm.pose.bones["jaw"].rotation_mode = "QUATERNION"
    B.pose_rotate(arm.pose.bones["jaw"], (1, 0, 0), 40.0)
    bpy.context.view_layer.update()
    bill_posed = evaluated_positions(bill)
    report["upper_bill_delta_on_jaw"] = round(
        max((bill_posed[i] - bill_rest[i]).length for i in upper_idx), 6)
    report["lower_bill_delta_on_jaw"] = round(
        max((bill_posed[i] - bill_rest[i]).length for i in lower_idx), 4)

    # ---- 5. idle hides skin/hair, run reveals them (front ortho rays) ----
    idle_inner, idle_hits = ray_visible_inner(arm, {})
    run_inner, run_hits = ray_visible_inner(arm, B.RUN_POSE)
    report["idle_inner_hits"] = idle_inner
    report["run_inner_hits"] = run_inner
    report["idle_hit_objects"] = idle_hits

    # geometric exposure: vertical span of skin/hair that front rays actually reach
    exposed, run_hits = inner_visible_span(arm, B.RUN_POSE)
    report["exposed_leg_m"] = round(exposed, 4)

    # ---- 6. ground / height ----
    B.apply_pose(arm)
    bpy.context.view_layer.update()
    all_pts = [p for o in meshes for p in evaluated_positions(o)]
    report["height"] = round(max(p.z for p in all_pts) - min(p.z for p in all_pts), 4)
    report["min_z"] = round(min(p.z for p in all_pts), 4)
    report["max_z"] = round(max(p.z for p in all_pts), 4)

    report["run_loop_mismatches"] = loop_problems(arm)

    print("CHECK:" + json.dumps(report, ensure_ascii=False, sort_keys=True))

    problems = []
    if report["ngons"]:
        problems.append(f"n-gons: {report['ngons']}")
    if report["weight_problems"]:
        problems.append(f"weights: {report['weight_problems']}")
    if report["bad_transforms"]:
        problems.append(f"transforms: {report['bad_transforms']}")
    if report["shell_verts_not_pure"]:
        problems.append("shell has vertices not 100% on shell bone")
    if report["shell_delta_on_leg_pose"] > 1e-4:
        problems.append("shell moves when legs move")
    if report["leg_delta_on_leg_pose"] < 0.05:
        problems.append("leg does not move when thigh rotates")
    if report["shoe_delta_on_foot_pose"] < 0.02:
        problems.append("shoe does not follow the foot bone")
    if report["shell_delta_on_foot_pose"] > 1e-4:
        problems.append("shell moves when foot moves")
    if report["upper_bill_delta_on_jaw"] > 1e-4:
        problems.append("upper bill follows jaw (should stay with shell)")
    if report["lower_bill_delta_on_jaw"] < 0.02:
        problems.append("lower bill does not open with jaw")
    if report["idle_inner_hits"] != 0:
        problems.append(f"idle shows skin/hair ({report['idle_inner_hits']} rays)")
    if report["run_inner_hits"] < 5:
        problems.append(f"run reveals too little skin/hair ({report['run_inner_hits']} rays)")
    if report["exposed_leg_m"] < 0.15:
        problems.append(f"exposed leg {report['exposed_leg_m']}m < 0.15m")
    if abs(report["height"] - 1.8) > 0.005:
        problems.append(f"height {report['height']}")
    if abs(report["min_z"]) > 0.002:
        problems.append(f"min_z {report['min_z']}")
    if report["run_loop_mismatches"]:
        problems.append(f"run loop mismatch: {report['run_loop_mismatches'][:3]}")
    if problems:
        raise SystemExit("CHECK FAILED: " + "; ".join(problems))
    print("CHECK_OK")


if __name__ == "__main__":
    main()
