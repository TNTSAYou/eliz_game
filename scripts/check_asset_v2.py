"""Acceptance checks for the v2 suit (docs/character_spec_v2.md sections 0/11).

Run:
    & "D:\\tools\\blender-4.5.15-windows-x64\\blender.exe" --background --factory-startup `
        --python-exit-code 1 --python "D:\\work\\eliz_game\\scripts\\check_asset_v2.py"

Opens art/blender/eliz_costume_v2.blend, measures topology / weights / pose
behaviour / occlusion / bill seam, prints CHECK:<json> and exits non-zero if a
hard check fails. Does not save the .blend.
"""

import json
import math
import sys
from collections import deque
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_eliz_v2 as B  # noqa: E402

BLEND = B.BLENDS / "eliz_costume_v2.blend"


def evaluated_positions(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in mesh.vertices]
    ev.to_mesh_clear()
    return pts


def max_delta(a, b):
    return max((p - q).length for p, q in zip(a, b))


def weight_problems(obj):
    bad = 0
    for v in obj.data.vertices:
        total = sum(g.weight for g in v.groups)
        if not v.groups or abs(total - 1.0) > 1e-3:
            bad += 1
    return bad


def connectivity(obj):
    """(connected components, boundary edges, non-manifold edges)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    seen = set()
    comps = 0
    for v in bm.verts:
        if v.index in seen:
            continue
        comps += 1
        q = deque([v])
        seen.add(v.index)
        while q:
            cur = q.popleft()
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    q.append(o)
    boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    bm.free()
    return comps, boundary, nonman


def tri_count(obj):
    return sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons)


def ray_visible_inner(arm, pose_kwargs, samples=44):
    B.apply_pose(arm, **pose_kwargs)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    hits = {}
    xs = [-0.55 + 1.10 * i / samples for i in range(samples + 1)]
    zs = [0.02 + 1.76 * i / samples for i in range(samples + 1)]
    for z in zs:
        for x in xs:
            ok, _loc, _n, _i, obj, _m = scene.ray_cast(
                dg, Vector((x, -6.0, z)), Vector((0.0, 1.0, 0.0)))
            if ok and obj is not None:
                hits[obj.name] = hits.get(obj.name, 0) + 1
    inner = sum(v for k, v in hits.items() if k.startswith(("INNER_Leg", "INNER_Hair")))
    return inner, hits


def inner_visible_span(arm, pose_kwargs, zstep=0.004, xstep=0.010):
    B.apply_pose(arm, **pose_kwargs)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    zs = [0.02 + zstep * i for i in range(int((0.95 - 0.02) / zstep))]
    xs = [xstep * i for i in range(1, 20)] + [-xstep * i for i in range(1, 20)]
    seen = []
    for z in zs:
        for x in xs:
            ok, _loc, _n, _i, obj, _m = scene.ray_cast(
                dg, Vector((x, -6.0, z)), Vector((0.0, 1.0, 0.0)))
            if ok and obj is not None and obj.name.startswith(("INNER_Leg", "INNER_Hair")):
                seen.append(z)
    if not seen:
        return 0.0, 0
    return max(seen) - min(seen), len(seen)


def action_fcurves(act):
    try:
        if len(act.layers) and len(act.slots):
            bag = act.layers[0].strips[0].channelbag(act.slots[0])
            if bag is not None:
                return list(bag.fcurves)
    except Exception:
        pass
    return list(act.fcurves)


def loop_problems(arm):
    act = bpy.data.actions.get("run")
    if act is None:
        return ["missing run action"]
    bad = []
    for fc in action_fcurves(act):
        pts = {round(k.co[0]): k.co[1] for k in fc.keyframe_points}
        if 1 in pts and 25 in pts and abs(pts[1] - pts[25]) > 1e-6:
            bad.append(fc.data_path)
    return bad


def bill_seam_measure(bill):
    """Seam z per x from the lower/upper material boundary (SAG) + lip step."""
    verts = bill.data.vertices
    seam = {}
    for poly in bill.data.polygons:
        if poly.material_index != 1:          # lower bill only
            continue
        for i in poly.vertices:
            v = verts[i]
            key = round(v.co.x, 2)
            seam[key] = max(seam.get(key, -9.0), v.co.z)
    center = seam.get(0.0)
    sides = [seam.get(0.2), seam.get(-0.2)]
    return center, sides


def main():
    if not BLEND.exists():
        raise SystemExit(f"missing blend: {BLEND}")
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))

    scene = bpy.context.scene
    arm = bpy.data.objects["RIG_Eliz"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("DEBUG_")]
    suit = sorted(o.name for o in meshes if o.name.startswith("SUIT_"))
    report = {"suit": suit}

    # ---- 1. geometry: one piece, manifold, thickness, tip ----
    shell = bpy.data.objects["SUIT_Shell"]
    comps, boundary, nonman = connectivity(shell)
    report["shell_components"] = comps
    report["shell_boundary_edges"] = boundary
    report["shell_nonmanifold_edges"] = nonman
    report["shell_tris"] = tri_count(shell)
    report["total_tris"] = sum(tri_count(o) for o in meshes)

    root = [v.co for v in shell.data.vertices
            if 0.46 < abs(v.co.x) < 0.54 and 0.96 < v.co.z < 1.04]
    report["arm_root_thickness"] = round(max(v.y for v in root) - min(v.y for v in root), 4) if root else 0
    tip = [v.co for v in shell.data.vertices if v.co.z < 0.665 and abs(v.co.x) > 0.44]
    report["arm_tip_halfwidth"] = round(max(abs(v.x) - 0.44 for v in tip), 4) if tip else 0

    report["weight_problems"] = {o.name: n for o in meshes if (n := weight_problems(o))}

    # arms must be driven by the arm bones, not the shell
    arm_groups = [g.name for g in shell.vertex_groups]
    report["shell_groups"] = arm_groups
    tip_idx = [v.index for v in shell.data.vertices
               if 0.56 < v.co.z < 0.70 and abs(v.co.x) > 0.47]
    tip_w = [sum(g.weight for g in shell.data.vertices[i].groups
                 if shell.vertex_groups[g.group].name.startswith("arm_")) for i in tip_idx]
    report["arm_tip_weight_min"] = round(min(tip_w), 3) if tip_w else 0

    # ---- 2. pose behaviour ----
    B.apply_pose(arm)
    bpy.context.view_layer.update()
    shell_rest = evaluated_positions(shell)
    leg = bpy.data.objects["INNER_Leg_L"]
    leg_rest = evaluated_positions(leg)

    B.apply_pose(arm, legs={"thigh_L": ((1, 0, 0), 40)})
    bpy.context.view_layer.update()
    report["shell_delta_on_leg_pose"] = round(max_delta(shell_rest, evaluated_positions(shell)), 6)
    report["leg_delta_on_leg_pose"] = round(max_delta(leg_rest, evaluated_positions(leg)), 4)

    shoe = bpy.data.objects["DUCKSHOE_L"]
    B.apply_pose(arm)
    bpy.context.view_layer.update()
    shoe_rest = evaluated_positions(shoe)
    B.apply_pose(arm, legs={"foot_L": ((1, 0, 0), 35)})
    bpy.context.view_layer.update()
    report["shoe_delta_on_foot_pose"] = round(max_delta(shoe_rest, evaluated_positions(shoe)), 4)

    # ---- 3. jaw + bill seam ----
    bill = bpy.data.objects["SUIT_Bill_Upper"]
    B.apply_pose(arm)
    bpy.context.view_layer.update()
    bill_rest = evaluated_positions(bill)
    upper_idx = [i for i, v in enumerate(bill.data.vertices) if v.co.z > 1.36]
    lower_idx = [i for i, v in enumerate(bill.data.vertices) if v.co.z < 1.30]
    arm.pose.bones["jaw"].rotation_mode = "QUATERNION"
    B.pose_rotate(arm.pose.bones["jaw"], (1, 0, 0), 40.0)
    bpy.context.view_layer.update()
    bill_posed = evaluated_positions(bill)
    report["upper_bill_delta_on_jaw"] = round(
        max((bill_posed[i] - bill_rest[i]).length for i in upper_idx), 6)
    report["lower_bill_delta_on_jaw"] = round(
        max((bill_posed[i] - bill_rest[i]).length for i in lower_idx), 4)

    center, sides = bill_seam_measure(bill)
    report["bill_seam_center_z"] = round(center, 4) if center else None
    report["bill_seam_side_z"] = [round(s, 4) if s else None for s in sides]
    if center and all(sides):
        report["bill_seam_sag"] = round(center - sum(sides) / 2.0, 4)
    else:
        report["bill_seam_sag"] = None

    # ---- 4. idle / run occlusion ----
    idle_inner, idle_hits = ray_visible_inner(arm, {})
    run_inner, run_hits = ray_visible_inner(arm, B.RUN_POSE)
    exposed, run_samples = inner_visible_span(arm, B.RUN_POSE)
    report["idle_inner_hits"] = idle_inner
    report["run_inner_hits"] = run_inner
    report["exposed_leg_m"] = round(exposed, 4)

    # ---- 5. hem / shoe dimensions on the rest pose ----
    B.apply_pose(arm)
    bpy.context.view_layer.update()
    shell_pts = evaluated_positions(shell)
    report["hem_min_z"] = round(min(p.z for p in shell_pts), 4)
    shoe_pts = evaluated_positions(shoe)
    report["shoe_bbox"] = [
        round(max(p.x for p in shoe_pts) - min(p.x for p in shoe_pts), 3),
        round(max(p.y for p in shoe_pts) - min(p.y for p in shoe_pts), 3),
        round(max(p.z for p in shoe_pts) - min(p.z for p in shoe_pts), 3),
    ]
    report["shoe_visible_h"] = round(min(p.z for p in shell_pts) - 0.0, 3)

    # ---- 6. hidden performer is fully inside the suit ----
    wearer = [o for o in bpy.data.objects if o.name.startswith("DEBUG_")]
    outside = 0
    wtop = -9.0
    wlow = 9.0
    for o in wearer:
        for v in o.data.vertices:
            p = v.co
            wtop = max(wtop, p.z)
            wlow = min(wlow, p.z)
            if p.z >= B.HEM_Z + 0.02:
                rr = math.hypot(p.x, p.y / B.DEPTH_RATIO)
                if rr > B.inner_r(p.z) - 0.015:
                    outside += 1
            else:
                if abs(abs(p.x) - B.SHOE_X) > 0.17 or abs(p.y) > 0.32:
                    outside += 1
    report["wearer_objects"] = len(wearer)
    report["wearer_vertices"] = sum(len(o.data.vertices) for o in wearer)
    report["wearer_outside"] = outside
    report["wearer_top"] = round(wtop, 3)
    report["wearer_head_clearance"] = round(1.80 - wtop, 3)

    # ---- 7. overall ----
    all_pts = [p for o in meshes for p in evaluated_positions(o)]
    report["height"] = round(max(p.z for p in all_pts) - min(p.z for p in all_pts), 4)
    report["min_z"] = round(min(p.z for p in all_pts), 4)
    report["run_loop_mismatches"] = loop_problems(arm)

    print("CHECK:" + json.dumps(report, ensure_ascii=False, sort_keys=True))

    problems = []
    if report["shell_components"] != 1:
        problems.append(f"shell has {report['shell_components']} components")
    if report["shell_boundary_edges"]:
        problems.append(f"{report['shell_boundary_edges']} boundary edges")
    if report["shell_nonmanifold_edges"]:
        problems.append(f"{report['shell_nonmanifold_edges']} non-manifold edges")
    if not (0.09 <= report["arm_root_thickness"] <= 0.16):
        problems.append(f"arm root thickness {report['arm_root_thickness']}")
    if report["arm_tip_halfwidth"] < 0.03:
        problems.append(f"arm tip half width {report['arm_tip_halfwidth']}")
    if report["arm_tip_weight_min"] < 0.85:
        problems.append(f"arm tip not weighted to arm bone ({report['arm_tip_weight_min']})")
    if report["weight_problems"]:
        problems.append(f"weights: {report['weight_problems']}")
    if report["shell_delta_on_leg_pose"] > 1e-4:
        problems.append("shell moves when legs move")
    if report["leg_delta_on_leg_pose"] < 0.05:
        problems.append("leg does not move when thigh rotates")
    if report["shoe_delta_on_foot_pose"] < 0.02:
        problems.append("shoe does not follow the foot bone")
    if report["upper_bill_delta_on_jaw"] > 1e-4:
        problems.append("upper bill follows jaw")
    if report["lower_bill_delta_on_jaw"] < 0.02:
        problems.append("lower bill does not open with jaw")
    if (report["bill_seam_sag"] or 0) < 0.015:
        problems.append(f"bill seam sag {report['bill_seam_sag']} (want ~0.03)")
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
    if not (0.16 <= report["hem_min_z"] <= 0.20):
        problems.append(f"hem z {report['hem_min_z']}")
    if report["wearer_outside"] > 0:
        problems.append(f"wearer pokes out of the suit ({report['wearer_outside']} verts)")
    if report["wearer_head_clearance"] < 0.10:
        problems.append(f"head clearance {report['wearer_head_clearance']}m < 0.10m")
    if report["run_loop_mismatches"]:
        problems.append(f"run loop mismatch: {report['run_loop_mismatches'][:3]}")
    if problems:
        raise SystemExit("CHECK FAILED: " + "; ".join(problems))
    print("CHECK_OK")


if __name__ == "__main__":
    main()
