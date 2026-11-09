"""v4 soft-shell acceptance gates H1-H11 (docs/character_spec_v2.md 18.6).

Run:
    & "D:\\tools\\blender-4.5.15-windows-x64\\blender.exe" --background `
        --factory-startup --python-exit-code 1 --python "scripts\\check_soft_v4.py"

Opens art/blender/eliz_costume_v2.blend, plays `run` frame by frame and checks
that the suit actually deforms like cloth. Prints SOFT:<json> then SOFT_OK /
SOFT FAILED. Does not modify or save the blend.
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_eliz_v2 as B  # noqa: E402

BLEND = ROOT / "art" / "blender" / "eliz_costume_v2.blend"
GLB = ROOT / "art" / "exports" / "eliz_costume_v2.glb"

SOFT_OK_ANGLE = 12.0
HEM_TOL = 0.01


def eval_shell(shell):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = shell.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts


def rest_hem_indices(shell):
    return [i for i, v in enumerate(shell.data.vertices) if v.co.z < 0.08]


def plane_angle(pts):
    """Tilt of a fitted plane from horizontal, in degrees."""
    if len(pts) < 8:
        return 99.0
    p = np.array([[q.x, q.y, q.z] for q in pts], dtype=float)
    p = p - p.mean(axis=0)
    _u, _s, vt = np.linalg.svd(p, full_matrices=False)
    n = vt[2]
    n = n / (np.linalg.norm(n) or 1.0)
    return math.degrees(math.acos(min(1.0, abs(float(n[2])))))


def assign(arm, name):
    act = bpy.data.actions.get(name)
    if act is None:
        raise SystemExit(f"missing action {name}")
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    slots = list(getattr(act, "slots", []))
    if slots and hasattr(ad, "action_slot"):
        ad.action_slot = slots[0]
    return act


def glb_json(path):
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise SystemExit("bad glb header")
    length = int.from_bytes(data[12:16], "little")
    if int.from_bytes(data[16:20], "little") != 0x4E4F534A:
        raise SystemExit("first glb chunk is not JSON")
    return json.loads(data[20:20 + length].decode("utf-8"))


def main():
    if not BLEND.exists():
        raise SystemExit(f"missing blend: {BLEND}")
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    arm = bpy.data.objects["RIG_Eliz"]
    shell = bpy.data.objects["SUIT_Shell"]
    report = {}

    # ---- weights: H7 ----
    groups = {g.index: g.name for g in shell.vertex_groups}
    arm_below = 0
    bad_sum = 0
    hem_group_verts = 0
    for v in shell.data.vertices:
        w = {groups[g.group]: g.weight for g in v.groups}
        total = sum(w.values())
        if abs(total - 1.0) > 1e-3:
            bad_sum += 1
        if v.co.z < 0.55 and (w.get("arm_L", 0.0) + w.get("arm_R", 0.0)) > 0.0:
            arm_below += 1
        if any(k.startswith("hem_") for k in w):
            hem_group_verts += 1
    report["bones"] = len(arm.data.bones)
    report["arm_weight_below_055"] = arm_below
    report["weight_sum_bad"] = bad_sum
    report["hem_weighted_verts"] = hem_group_verts

    # ---- play the run cycle ----
    assign(arm, "run")
    hem_idx = rest_hem_indices(shell)
    # torso band on the rest mesh, tracked by index so the lift does not move it
    torso_idx = [i for i, v in enumerate(shell.data.vertices)
                 if 0.72 < v.co.z < 0.80 and abs(v.co.x) < 0.46]
    frames = list(range(1, 25))
    widths, extents, radii, hem_z, tilts, mesh_snaps = [], [], [], [], [], []
    for f in frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        pts = eval_shell(shell)
        hem_pts = [pts[i] for i in hem_idx]
        hz = min(p.z for p in hem_pts)
        widths.append(max(abs(pts[i].x) for i in torso_idx))
        extents.append(max(p.z for p in pts) - hz)
        radii.append(sum(math.hypot(p.x, p.y / 0.82) for p in hem_pts) / len(hem_pts))
        hem_z.append(hz)
        tilts.append(plane_angle(hem_pts))
        mesh_snaps.append(pts)

    lifts = [B.run_lift(f) for f in frames]

    w4, w10 = widths[3], widths[9]
    e4, e10 = extents[3], extents[9]
    report["width_f4_f10"] = [round(w4, 4), round(w10, 4)]
    report["width_gain"] = round((w4 - w10) / max(w10, 1e-6), 4)
    report["extent_f4_f10"] = [round(e4, 4), round(e10, 4)]
    report["extent_gain"] = round((e10 - e4) / e4, 4)
    report["radius_range"] = round(max(radii) - min(radii), 4)
    report["radius_gain"] = round(max(radii) - min(radii), 4)
    report["hem_z_min"] = round(min(hem_z), 4)
    report["hem_tilt_max"] = round(max(tilts), 2)

    # ---- H3: the hem flare lags the lift (radius, not height: the shell's own
    #      bounce dominates the hem height) ----
    def corr(lag):
        m_h = sum(radii) / 24.0
        m_l = sum(lifts) / 24.0
        num = sum((radii[i] - m_h) * (lifts[(i - lag) % 24] - m_l) for i in range(24))
        dh = math.sqrt(sum((v - m_h) ** 2 for v in radii))
        dl = math.sqrt(sum((v - m_l) ** 2 for v in lifts))
        return num / (dh * dl) if dh and dl else 0.0

    lags = {lag: round(corr(lag), 3) for lag in range(0, 7)}
    best_lag = max(lags, key=lags.get)
    report["lag_corr"] = lags
    report["hem_lag_frames"] = best_lag

    # ---- H6: legs / shoes must stay inside the cloth above the hem ----
    inner = [o for o in bpy.data.objects
             if o.name.startswith(("INNER_Leg", "INNER_Hair", "INNER_Foot"))]
    penetrations = 0
    for f in (4, 10, 16, 22):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        hz = min(p.z for p in eval_shell(shell))
        for obj in inner:
            ev = obj.evaluated_get(dg)
            me = ev.to_mesh()
            mw = ev.matrix_world
            for k, v in enumerate(me.vertices):
                if k % 7:
                    continue
                p = mw @ v.co
                if p.z < hz + HEM_TOL:
                    continue
                d = Vector((p.x, p.y / 0.82, 0.0))
                if d.length < 1e-6:
                    continue
                d.normalize()
                hit, _loc, _n, _i, _o, _m = scene.ray_cast(dg, p, d)
                if not hit:
                    penetrations += 1
            ev.to_mesh_clear()
    report["leg_penetrations"] = penetrations

    # ---- H8: loop closure (frame 25 is the loop point) ----
    scene.frame_set(25)
    bpy.context.view_layer.update()
    final_pts = eval_shell(shell)
    loop_delta = max((a - b).length for a, b in zip(mesh_snaps[0], final_pts))

    # ---- H10: GLB has a run animation with a shell scale channel ----
    glb_report = {"file": str(GLB), "bytes": GLB.stat().st_size if GLB.exists() else 0}
    scale_channel = False
    anim_names = []
    if GLB.exists():
        doc = glb_json(GLB)
        nodes = doc.get("nodes", [])
        for anim in doc.get("animations", []):
            anim_names.append(anim.get("name"))
            for ch in anim.get("channels", []):
                tgt = ch.get("target", {})
                node = nodes[tgt.get("node", -1)] if tgt.get("node", -1) < len(nodes) else {}
                if tgt.get("path") == "scale" and node.get("name", "").endswith("shell"):
                    scale_channel = True
    glb_report["animations"] = anim_names
    glb_report["shell_scale_channel"] = scale_channel
    report["glb"] = glb_report
    report["loop_mesh_delta"] = round(loop_delta, 6)

    # ---- H11: idle stays rigid ----
    assign(arm, "idle")
    scene.frame_set(1)
    bpy.context.view_layer.update()
    idle_pts = eval_shell(shell)
    idle_hem = [idle_pts[i] for i in hem_idx]
    report["idle_hem_tilt"] = round(plane_angle(idle_hem), 2)
    report["idle_scale"] = [round(s, 4) for s in arm.pose.bones["shell"].scale]

    print("SOFT:" + json.dumps(report, ensure_ascii=False, sort_keys=True))

    problems = []
    if report["bones"] != 32:
        problems.append(f"bones {report['bones']} != 32")
    if report["arm_weight_below_055"]:
        problems.append(f"{report['arm_weight_below_055']} verts below z=0.55 still arm-weighted")
    if report["weight_sum_bad"]:
        problems.append(f"{report['weight_sum_bad']} verts with weight sum != 1")
    if report["width_gain"] < 0.04:
        problems.append(f"H1 width gain {report['width_gain']} < 0.04")
    if report["extent_gain"] < 0.03:
        problems.append(f"H2 height gain {report['extent_gain']} < 0.03")
    if not (2 <= best_lag <= 4):
        problems.append(f"H3 hem lag {best_lag} not 2-4 frames")
    if report["radius_gain"] < 0.05:
        problems.append(f"H4 hem radius gain {report['radius_gain']} < 0.05")
    if report["hem_tilt_max"] > SOFT_OK_ANGLE:
        problems.append(f"H5 hem tilt {report['hem_tilt_max']} > {SOFT_OK_ANGLE}")
    if report["leg_penetrations"] > 0:
        problems.append(f"H6 leg pokes through the cloth ({report['leg_penetrations']} rays)")
    if report["loop_mesh_delta"] > 1e-4:
        problems.append(f"H8 loop mesh delta {report['loop_mesh_delta']}")
    if not scale_channel:
        problems.append("H10 GLB run animation has no shell scale channel")
    if report["idle_hem_tilt"] > 2.0:
        problems.append(f"H11 idle hem tilt {report['idle_hem_tilt']}")
    if any(abs(s - 1.0) > 1e-4 for s in report["idle_scale"]):
        problems.append(f"H11 idle shell scale {report['idle_scale']}")
    if problems:
        raise SystemExit("SOFT FAILED: " + "; ".join(problems))
    print("SOFT_OK")


if __name__ == "__main__":
    main()
