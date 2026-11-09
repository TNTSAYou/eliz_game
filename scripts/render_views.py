"""Re-render the v1 preview views from the saved .blend, without rebuilding.

Run:
    & "D:\\tools\\blender-4.5.15-windows-x64\\blender.exe" --background `
        --python-exit-code 1 --python "D:\\work\\eliz_game\\scripts\\render_views.py"

Outputs art/renders/v1_*.png. Requires art/blender/eliz_costume_v1.blend,
which is produced by scripts/build_eliz_v1.py.
"""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_eliz_v1 as B  # noqa: E402  (needs bpy, only importable inside Blender)


def main():
    blend = B.BLENDS / "eliz_costume_v1.blend"
    if not blend.exists():
        raise SystemExit(f"missing blend: {blend}")

    bpy.ops.wm.open_mainfile(filepath=str(blend))
    cam = bpy.data.objects.get("CAM_View")
    arm = bpy.data.objects.get("RIG_Eliz")
    sign = bpy.data.objects.get("PROP_Sign")
    if cam is None or arm is None:
        raise SystemExit("blend is missing CAM_View / RIG_Eliz")

    B.apply_pose(arm)
    B.render_all_views(cam, sign)

    B.apply_pose(arm, **B.RUN_POSE)
    B.place_camera(cam, (-3.2, -4.2, 1.55), (0, 0, 0.95), 2.35)
    if sign:
        sign.hide_render = True
    B.render_to(B.RENDERS / "v1_run_reveal.png")

    B.apply_pose(arm)
    if sign:
        sign.hide_render = False
    B.place_camera(cam, (-3.6, -4.5, 1.60), (0, 0, 0.95), 3.00)
    B.render_to(B.RENDERS / "v1_sign_pose.png")

    print("RENDERED_OK")


if __name__ == "__main__":
    main()
