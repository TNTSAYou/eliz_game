"""Build Elizabeth v5: v4.1 silhouette/rig + baked cloth folds + smooth coat.

Run (PowerShell):
    & "D:\\tools\\blender-4.5.15-windows-x64\\blender.exe" --background `
        --python-exit-code 1 --python "scripts\\build_eliz_v5.py"

Outputs:
    art/blender/eliz_costume_v5.blend
    art/exports/eliz_costume_v5.glb
    art/renders/v5_*.png
    tools/v5_run_frames/{three_quarter,side}/frame_XXX.png
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_eliz_v2 as B  # noqa: E402
import cloth_v5 as C  # noqa: E402

RENDERS = ROOT / "art" / "renders"
BLENDS = ROOT / "art" / "blender"
EXPORTS = ROOT / "art" / "exports"
FRAMES = ROOT / "tools" / "v5_run_frames"

# v5.1: the coat drags.  Lift is only a small bob, so the hem stays near the
# floor; the hem panels and shell squash/stretch from v4.1 are gone.
V5_LIFT = [
    (1, 0.035), (4, 0.020), (7, 0.055), (10, 0.090),
    (13, 0.035), (16, 0.020), (19, 0.055), (22, 0.090), (25, 0.035),
]


def run_lift_v5(f):
    f = ((f - 1) % 24) + 1
    prev = V5_LIFT[0]
    for cur in V5_LIFT[1:]:
        if prev[0] <= f <= cur[0]:
            span = cur[0] - prev[0]
            t = (f - prev[0]) / span if span else 0.0
            return prev[1] + (cur[1] - prev[1]) * t
        prev = cur
    return V5_LIFT[0][1]


def setup_smooth_fabric():
    """Smooth cotton: no sheen, no fibre normal, no plush maps (v5 D9)."""
    mat = B.MATS["M_Suit"]
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    for l in list(nt.links):
        if l.to_node == bsdf and l.to_socket.name in ("Base Color", "Roughness", "Normal"):
            nt.links.remove(l)
    col = B.srgb("#ECEBE7")
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = 0.62
    bsdf.inputs["Specular IOR Level"].default_value = 0.28
    bsdf.inputs["Sheen Weight"].default_value = 0.0
    bsdf.inputs["Metallic"].default_value = 0.0
    mat.diffuse_color = col


def regroup_for_outline(shell):
    """Coat and detail get separate Freestyle linesets: the coat uses only its
    external contour (folds must not become ink scratches), the face/shoes keep
    normal silhouettes."""
    coat = bpy.data.collections.get("COAT") or bpy.data.collections.new("COAT")
    detail = bpy.data.collections.get("DETAIL") or bpy.data.collections.new("DETAIL")
    for c in (coat, detail):
        if c.name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(c)
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name.startswith(("CLOTH_", "DEBUG_")):
            continue
        for c in list(o.users_collection):
            c.objects.unlink(o)
        (coat if o is shell else detail).objects.link(o)
    return coat, detail


def fix_freestyle(scene, coat, detail):
    """Folds are geometry, not ink lines: coat = external contour only."""
    fs = scene.view_layers[0].freestyle_settings
    for ls in list(fs.linesets):
        fs.linesets.remove(ls)
    base = bpy.data.linestyles.new("LS_Outline_v5")
    base.color = (0.12, 0.12, 0.12)

    coat_ls = fs.linesets.new("Coat")
    coat_ls.linestyle = base
    coat_ls.select_by_collection = True
    coat_ls.collection = coat
    coat_ls.select_silhouette = False
    coat_ls.select_external_contour = True
    coat_ls.select_border = False
    coat_ls.select_crease = False
    coat_ls.select_contour = False
    coat_ls.select_material_boundary = False

    det_ls = fs.linesets.new("Detail")
    det_ls.linestyle = base
    det_ls.select_by_collection = True
    det_ls.collection = detail
    det_ls.select_silhouette = True
    det_ls.select_external_contour = False
    det_ls.select_border = True
    det_ls.select_crease = False
    det_ls.select_contour = False
    det_ls.select_material_boundary = False


def set_action(arm, name):
    act = bpy.data.actions[name]
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    slots = list(getattr(act, "slots", []))
    if slots and hasattr(ad, "action_slot"):
        ad.action_slot = slots[0]


def set_morph_action(shell, act):
    ad = shell.data.shape_keys.animation_data_create()
    ad.action = act


def mute_nla(arm, shell, mute=True):
    for tr in arm.animation_data.nla_tracks:
        tr.mute = mute
    for tr in shell.data.shape_keys.animation_data.nla_tracks:
        tr.mute = mute


def retune_run(arm):
    """v5.1 run: no hem-panel flare/curl, no shell squash/stretch, small lift."""
    act = bpy.data.actions["run"]
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    slots = list(getattr(act, "slots", []))
    if slots and hasattr(ad, "action_slot"):
        ad.action_slot = slots[0]
    for fc in list(act.fcurves):
        dp = fc.data_path
        if "hem_" in dp and "hem_root" not in dp:
            act.fcurves.remove(fc)
        elif dp == 'pose.bones["shell"].scale':
            act.fcurves.remove(fc)
        elif dp == 'pose.bones["shell"].location':
            act.fcurves.remove(fc)
    pb = arm.pose.bones["shell"]
    for f in range(1, 26):
        bpy.context.scene.frame_set(f)
        pb.scale = (1.0, 1.0, 1.0)
        B.pose_translate(pb, (0.0, 0.0, run_lift_v5(f)))
        pb.keyframe_insert("location", frame=f)
    B.reset_pose(arm)
    ad.action = None


def render_views(cam, shell, idle_act, sign):
    arm = bpy.data.objects["RIG_Eliz"]
    arm.animation_data.action = None
    B.apply_pose(arm)
    set_morph_action(shell, idle_act)
    bpy.context.scene.frame_set(1)
    if sign:
        sign.hide_render = True
    for name, loc, target, scale in (
        ("front", (0.0, -6.0, 0.95), (0.0, 0.0, 0.95), 2.30),
        ("side", (-6.0, 0.0, 0.95), (0.0, 0.0, 0.95), 2.30),
        ("back", (0.0, 6.0, 0.95), (0.0, 0.0, 0.95), 2.30),
        ("three_quarter", (-3.6, -4.0, 1.65), (0.0, 0.0, 0.92), 2.60),
    ):
        B.place_camera(cam, loc, target, scale)
        B.render_to(RENDERS / f"v5_{name}.png")


def render_fold_detail(cam, arm, shell, run_act):
    sign = bpy.data.objects.get("PROP_Sign")
    if sign:
        sign.hide_render = True
    set_action(arm, "run")
    set_morph_action(shell, run_act)
    bpy.context.scene.render.resolution_x = 800
    bpy.context.scene.render.resolution_y = 1000
    bpy.context.scene.frame_set(10)
    B.place_camera(cam, (-3.0, -3.6, 1.35), (0.0, -0.10, 0.55), 1.80)
    B.render_to(RENDERS / "v5_detail_folds.png")


def render_run(cam, arm, shell, run_act):
    set_action(arm, "run")
    set_morph_action(shell, run_act)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 480, 600
    scene.render.use_freestyle = True
    for view, loc, target, scale in (
        ("three_quarter", (-3.6, -4.0, 1.65), (0.0, 0.0, 0.92), 2.60),
        ("side", (-6.0, 0.0, 0.95), (0.0, 0.0, 0.95), 2.30),
    ):
        out = FRAMES / view
        out.mkdir(parents=True, exist_ok=True)
        B.place_camera(cam, loc, target, scale)
        for f in range(1, 25):
            scene.frame_set(f)
            scene.render.filepath = str(out / f"frame_{f:03d}.png")
            bpy.ops.render.render(write_still=True)
        print("RENDERED", view)


def main():
    for d in (RENDERS, BLENDS, EXPORTS, FRAMES):
        d.mkdir(parents=True, exist_ok=True)

    B.clean_scene()
    B.build_materials()
    setup_smooth_fabric()
    colls = B.make_collections()
    cloth_coll = bpy.data.collections.new("CLOTH")
    bpy.context.scene.collection.children.link(cloth_coll)

    shell = B.build_shell(colls)
    # v5.1: the v4.1 hem bones used to flare the lower coat by ~20掳.  With them
    # gone the long coat collapses onto the legs; add a static 12% flare so the
    # cloth stays outside the wearer, without the curled bell edge.
    for v in shell.data.vertices:
        if v.co.z < 0.55:
            f = 1.0 + 0.22 * (1.0 - B._smoothstep((v.co.z - 0.05) / 0.50))
            v.co.x *= f
            v.co.y *= f
    bill = B.build_bills(colls)
    eyes = B.build_eyes(colls)
    shoes = B.build_shoes(colls)
    legs = B.build_legs(colls)
    hair = B.build_hair(colls)
    # v5: the cloth folds inward by up to 3 cm; pull the crotch hair spikes 20%
    # towards their leg so they cannot sit inside the fabric thickness
    for v in hair.data.vertices:
        side = 1.0 if v.co.x >= 0.0 else -1.0
        cx = side * B.SHOE_X
        v.co.x = cx + (v.co.x - cx) * 0.55
        v.co.y *= 0.55
    pelvis = B.build_pelvis(colls)
    sign = B.build_sign(colls)
    wearer = B.build_wearer(colls)

    arm_obj = B.build_armature(colls)
    B.bind_suit(colls, arm_obj, shell, list(eyes.values()))
    B.add_vertex_groups(bill, [{"shell_top": 1.0 - w, "jaw": w} for w in
                               [B._smoothstep((B.bill_seam_z(v.co.x) - v.co.z) / 0.02)
                                for v in bill.data.vertices]])
    B.bind(bill, arm_obj, None)
    B.bind_legs(arm_obj, legs, hair)
    B.bind_rigid(arm_obj, pelvis, "pelvis")
    B.bind_rigid(arm_obj, sign, "sign_socket")
    for side in ("L", "R"):
        B.bind_rigid(arm_obj, shoes[side], f"foot_{side}")

    cam = B.setup_render_rig(colls)
    coat, detail = regroup_for_outline(shell)
    fix_freestyle(bpy.context.scene, coat, detail)
    B.setup_world()

    mesh_objs = [shell, bill] + list(eyes.values()) + list(shoes.values()) \
        + list(legs.values()) + [hair, pelvis, sign]

    # a -10 deg shell pitch collapses the long coat's back onto the leg; -3 deg
    # keeps the lean without the coat cutting into the wearer.  The thigh swing
    # is halved: the long coat covers the legs now, and a smaller step keeps
    # them inside the back wall.
    def _leg(v):
        return (v[0] * 0.5, v[1], v[2])

    B.RUN_KEY_TABLE = [(f, lift, -3.0, roll, _leg(left), _leg(right), arm)
                       for (f, lift, _tilt, roll, left, right, arm) in B.RUN_KEY_TABLE]
    actions = B.build_actions(arm_obj)
    retune_run(arm_obj)
    B.run_lift = run_lift_v5
    # cloth bake reads the run lift curve, not the armature pose
    cloth = C.build(cloth_coll, shell)
    mute_nla(arm_obj, shell, True)

    # ---- stills ----
    render_views(cam, shell, cloth["idle_act"], sign)

    # ---- run frames ----
    if sign:
        sign.hide_render = True
    render_run(cam, arm_obj, shell, cloth["run_act"])
    render_fold_detail(cam, arm_obj, shell, cloth["run_act"])

    # ---- rest state for save / stats ----
    if sign:
        sign.hide_render = False
    arm_obj.animation_data.action = None
    B.apply_pose(arm_obj)
    set_morph_action(shell, cloth["idle_act"])
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 60
    bpy.context.scene.frame_set(1)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 800, 1000

    blend_path = BLENDS / "eliz_costume_v5.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"SAVED:{blend_path}")

    # ---- export: NLA tracks with matching names merge bones + morph weights ----
    mute_nla(arm_obj, shell, False)
    arm_obj.animation_data.action = None
    shell.data.shape_keys.animation_data.action = None
    for tr in arm_obj.animation_data.nla_tracks:
        tr.mute = False
    for tr in shell.data.shape_keys.animation_data.nla_tracks:
        tr.mute = False

    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objs + [arm_obj]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    glb_path = EXPORTS / "eliz_costume_v5.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_apply=False,
        export_animations=True,
        export_animation_mode="NLA_TRACKS",
        export_morph=True,
        export_morph_normal=True,
        export_yup=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print(f"EXPORTED:{glb_path}")
    print("V5_OK")


if __name__ == "__main__":
    main()

