import os, glob, time, math
import bpy
import numpy as np
from pathlib import Path
from os.path import join

# -------------------------
# Paths
# -------------------------
outPath = None
inFolder = r'D:\Data\DAT_Sim\cloth_twist_release\truncation_1_iter_100_20260105_123906'

if outPath is None:
    outPath = inFolder + "\\Rendering_subdiv"
os.makedirs(outPath, exist_ok=True)

# your npy folder / pattern
npy_pattern = join(inFolder, "*.npy")   # adjust if needed

# -------------------------
# Settings
# -------------------------
cam_name = "Camera"
target_obj_name = "initial_mesh"   # <-- existing mesh object name in the Blender scene

stride = 1
numFrames = 1000
doSubDiv = False
thickness = 0.003

# (optional) apply scale/loc/rot once
apply_transform_once = False
obj_scale = (0.01, 0.01, 0.01)
obj_location = (0.0, 0.0, 10.0)
obj_rotation_euler = (0.0, 0.0, 0.0)  # radians

# -------------------------
# Helpers
# -------------------------
def get_mesh_obj(name: str) -> bpy.types.Object:
    obj = bpy.context.scene.objects.get(name)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Cannot find mesh object '{name}' in the scene.")
    return obj

def update_mesh_vertices(obj: bpy.types.Object, V_np: np.ndarray):
    """
    V_np: (N,3) float32/float64 in object local space.
    """
    if V_np.ndim != 2 or V_np.shape[1] != 3:
        raise ValueError(f"Expected (N,3) array, got {V_np.shape}.")

    mesh = obj.data
    n_mesh = len(mesh.vertices)
    n_in = V_np.shape[0]
    if n_in != n_mesh:
        raise ValueError(f"Vertex count mismatch: mesh has {n_mesh}, npy has {n_in}.")

    # Flatten to [x0,y0,z0,x1,y1,z1,...]
    co_flat = V_np.astype(np.float32).reshape(-1)

    # Fast bulk update
    mesh.vertices.foreach_set("co", co_flat)

    # Ensure Blender updates depsgraph
    mesh.update()
    obj.update_tag()

# -------------------------
# Main
# -------------------------
bpy.context.scene.camera = bpy.context.scene.objects[cam_name]
print("Camera:", cam_name)

obj = get_mesh_obj(target_obj_name)
print("Target mesh:", obj.name)


bpy.ops.object.select_all(action='DESELECT')
obj.select_set(state=True)


# Optional: material once
mat = bpy.data.materials.get("Cloth")
if mat is not None:
    if len(obj.material_slots) < 1:
        obj.data.materials.append(mat)
    else:
        obj.material_slots[obj.active_material_index].material = mat
    obj.data.materials[0] = mat

# Collect frames
npy_files = sorted(glob.glob(npy_pattern))
print("Number of npy frames:", len(npy_files))

fileId = 0
while fileId < numFrames:
    if fileId >= len(npy_files):
        print("No more npy frames yet. Wait 6 mins.")
        time.sleep(360)
        npy_files = sorted(glob.glob(npy_pattern))
        continue

    npy_path = npy_files[fileId]
    print("Rendering:", npy_path)

    # Load vertices
    V = np.load(npy_path)

    # Update the existing mesh vertices
    update_mesh_vertices(obj, V)

    # Render
    bpy.context.scene.render.filepath = os.path.join(outPath, Path(npy_path).stem + ".png")
    bpy.ops.render.render(write_still=True)

    fileId += stride
