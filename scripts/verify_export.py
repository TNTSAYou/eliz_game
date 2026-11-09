"""Re-import art/exports/eliz_costume_v1.glb into a clean scene and check it.

Run:
    & "D:\\tools\\blender-4.5.15-windows-x64\\blender.exe" --background --factory-startup `
        --python-exit-code 1 --python "D:\\work\\eliz_game\\scripts\\verify_export.py"

Prints a VERIFY:<json> line and exits non-zero if a hard check fails.
"""

import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / "art" / "exports" / "eliz_costume_v1.glb"


def main():
    if not GLB.exists():
        raise SystemExit(f"missing export: {GLB}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLB))

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    # the importer adds a bone-shape helper in "glTF_not_exported"; ignore it
    meshes = [o for o in meshes
              if not any(c.name == "glTF_not_exported" for c in o.users_collection)]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    depsgraph = bpy.context.evaluated_depsgraph_get()

    tris = 0
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]
    for obj in meshes:
        ev = obj.evaluated_get(depsgraph)
        mesh = ev.to_mesh()
        tris += sum(max(0, len(p.vertices) - 2) for p in mesh.polygons)
        for v in mesh.vertices:
            co = ev.matrix_world @ v.co
            for i in range(3):
                lo[i] = min(lo[i], co[i])
                hi[i] = max(hi[i], co[i])
        ev.to_mesh_clear()

    bones = sum(len(a.data.bones) for a in arms)
    actions = sorted(a.name for a in bpy.data.actions)
    mats = sorted(m.name for m in bpy.data.materials)
    height = hi[2] - lo[2]

    report = {
        "file": str(GLB),
        "bytes": GLB.stat().st_size,
        "meshes": len(meshes),
        "armatures": len(arms),
        "bones": bones,
        "tris": tris,
        "height": round(height, 4),
        "width": round(hi[0] - lo[0], 4),
        "depth": round(hi[1] - lo[1], 4),
        "min_z": round(lo[2], 4),
        "max_z": round(hi[2], 4),
        "actions": actions,
        "materials": mats,
    }
    print("VERIFY:" + json.dumps(report, ensure_ascii=False))

    problems = []
    if not (1.79 <= height <= 1.81):
        problems.append(f"height {height:.3f} != 1.80")
    if bones != 13:
        problems.append(f"bones {bones} != 13")
    if len(actions) < 2:
        problems.append(f"actions {actions} < 2")
    if not (4000 <= tris <= 12000):
        problems.append(f"tris {tris} outside 4k-12k")
    if lo[2] < -0.002:
        problems.append(f"min_z {lo[2]:.3f} below ground")
    if problems:
        raise SystemExit("VERIFY FAILED: " + "; ".join(problems))
    print("VERIFY_OK")


if __name__ == "__main__":
    main()
