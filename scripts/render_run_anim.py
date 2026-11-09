"""Render the run cycle from the saved v2 blend to PNG frames + MP4 + GIF.

Run:
    & "D:\\tools\\blender-4.5.15-windows-x64\\blender.exe" --background `
        --python-exit-code 1 --python "D:\\work\\eliz_game\\scripts\\render_run_anim.py"

Outputs:
    tools/run_frames/frame_001.png ...
    art/renders/v3_run.mp4
    art/renders/v3_run.gif   (made by the caller with ffmpeg)
"""

import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_eliz_v2 as B  # noqa: E402

FRAMES = (1, 25)          # last frame is the loop point, not rendered twice
OUT = ROOT / "tools" / "run_frames"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(B.BLENDS / "eliz_costume_v2.blend"))
    scene = bpy.context.scene
    arm = bpy.data.objects["RIG_Eliz"]
    cam = bpy.data.objects["CAM_View"]
    sign = bpy.data.objects.get("PROP_Sign")

    act = bpy.data.actions.get("run")
    if act is None:
        raise SystemExit("missing run action")
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    slots = list(getattr(act, "slots", []))
    if slots and hasattr(ad, "action_slot"):
        ad.action_slot = slots[0]

    if sign:
        sign.hide_render = True
    scene.render.fps = 30
    scene.frame_start, scene.frame_end = FRAMES
    scene.render.resolution_x, scene.render.resolution_y = 640, 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_freestyle = True

    views = [
        ("three_quarter", (-3.6, -4.0, 1.65), (0.0, 0.0, 0.92), 2.60),
        ("side", (-6.0, 0.0, 0.95), (0.0, 0.0, 0.95), 2.30),
    ]
    for name, loc, target, scale in views:
        out_dir = OUT / name
        out_dir.mkdir(parents=True, exist_ok=True)
        B.place_camera(cam, loc, target, scale)
        for f in range(FRAMES[0], FRAMES[1]):
            scene.frame_set(f)
            scene.render.filepath = str(out_dir / f"frame_{f:03d}.png")
            bpy.ops.render.render(write_still=True)
        print(f"VIEW {name} done")
    print("ANIM_OK")


if __name__ == "__main__":
    main()
