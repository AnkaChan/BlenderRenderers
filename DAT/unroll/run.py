import os, glob, time, math, sys, argparse
import bpy
import numpy as np
from pathlib import Path
from os.path import join

# -------------------------
# Argument Parsing
# -------------------------
def parse_args():
    # Blender eats args before "--", so we grab everything after
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    parser = argparse.ArgumentParser(description="Render npy sequence with Blender")
    parser.add_argument("--inFolder", type=str, required=True, help="Input folder containing .npy files")
    parser.add_argument("--outPath", type=str, default=None, help="Output folder for rendered images")
    parser.add_argument("--gpu", type=int, default=0, help="GPU index to use (default: 0)")
    parser.add_argument("--numFrames", type=int, default=1000, help="Number of frames to render")
    parser.add_argument("--stride", type=int, default=1, help="Frame stride")
    return parser.parse_args(argv)

args = parse_args()

# -------------------------
# GPU / OptiX Setup
# -------------------------
def setup_optix(gpu_index=0):
    """Enable OptiX rendering on a specific GPU."""
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()  # Refresh device list
    
    # Disable all devices first
    for device in prefs.devices:
        device.use = False
    
    # Enable only the specified GPU
    gpu_devices = [d for d in prefs.devices if d.type == 'OPTIX']
    if gpu_index < len(gpu_devices):
        gpu_devices[gpu_index].use = True
        print(f"Using OptiX device: {gpu_devices[gpu_index].name}")
    else:
        print(f"Warning: GPU index {gpu_index} not found. Available: {len(gpu_devices)}")
        if gpu_devices:
            gpu_devices[0].use = True
    
    # Set scene to use GPU
    bpy.context.scene.cycles.device = 'GPU'

# Call setup using GPU from args
setup_optix(gpu_index=args.gpu)

# -------------------------
# Paths (from command line args)
# -------------------------
inFolder = args.inFolder
outPath = args.outPath if args.outPath else inFolder + "/Rendering_subdiv"
os.makedirs(outPath, exist_ok=True)

# your npy folder / pattern
npy_pattern = join(inFolder, "*.npy")   # adjust if needed

# -------------------------
# Settings
# -------------------------
cam_name = "Camera"
target_obj_name = "initial_cloth"   # <-- mesh object name for unroll scene

stride = args.stride
numFrames = args.numFrames
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

    # Load vertices (skip first 66 vertices which are the collider)
    V = np.load(npy_path)[66:]

    # Update the existing mesh vertices
    update_mesh_vertices(obj, V)

    # Render
    bpy.context.scene.render.filepath = os.path.join(outPath, Path(npy_path).stem + ".png")
    bpy.ops.render.render(write_still=True)

    fileId += stride

