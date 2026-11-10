"""Re-render v5 views and run frames from the saved blend (no rebuild/sim)."""
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_eliz_v2 as B  # noqa: E402
import build_eliz_v5 as V5  # noqa: E402

bpy.ops.wm.open_mainfile(filepath=str(ROOT / "art" / "blender" / "eliz_costume_v5.blend"))
scene = bpy.context.scene
cam = bpy.data.objects["CAM_View"]
arm = bpy.data.objects["RIG_Eliz"]
shell = bpy.data.objects["SUIT_Shell"]
sign = bpy.data.objects.get("PROP_Sign")

coat, detail = V5.regroup_for_outline(shell)
V5.fix_freestyle(scene, coat, detail)
V5.mute_nla(arm, shell, True)
V5.render_views(cam, shell, bpy.data.actions["idle_morph"], sign)
if sign:
    sign.hide_render = True
V5.render_run(cam, arm, shell, bpy.data.actions["run_morph"])
V5.render_fold_detail(cam, arm, shell, bpy.data.actions["run_morph"])

# restore the saved state
if sign:
    sign.hide_render = False
arm.animation_data.action = None
B.apply_pose(arm)
V5.set_morph_action(shell, bpy.data.actions["idle_morph"])
V5.mute_nla(arm, shell, True)
scene.frame_start, scene.frame_end = 1, 60
scene.frame_set(1)
scene.render.resolution_x, scene.render.resolution_y = 800, 1000
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "art" / "blender" / "eliz_costume_v5.blend"))
print("RERENDER_OK")
