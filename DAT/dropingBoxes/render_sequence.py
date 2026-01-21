"""
Blender script to render Falling Gift simulation sequence.

Usage:
    blender FallingGift.blend --background --python render_sequence.py -- --inFolder "D:\Data\DAT_sim\falling_gift_comparison\experiment_folder" --outPath "D:\renders\falling_gift" --gpu 0 --numFrames 800

The script expects the following folder structure:
    inFolder/
    ├── initial_box1.ply    (topology, already loaded in scene)
    ├── initial_box2.ply
    ├── initial_box3.ply
    ├── initial_box4.ply
    ├── initial_cloth1.ply
    ├── initial_cloth2.ply
    ├── box1/
    │   ├── frame_000000.npy
    │   ├── frame_000001.npy
    │   └── ...
    ├── box2/
    ├── box3/
    ├── box4/
    ├── cloth1/
    └── cloth2/
"""

import os
import glob
import time
import sys
import argparse
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
    
    parser = argparse.ArgumentParser(description="Render Falling Gift npy sequence with Blender")
    parser.add_argument("--inFolder", type=str, required=True, help="Input folder containing component subfolders with .npy files")
    parser.add_argument("--outPath", type=str, default=None, help="Output folder for rendered images")
    parser.add_argument("--gpu", type=int, default=0, help="GPU index to use (default: 0)")
    parser.add_argument("--numFrames", type=int, default=800, help="Number of frames to render")
    parser.add_argument("--stride", type=int, default=1, help="Frame stride (render every Nth frame)")
    parser.add_argument("--startFrame", type=int, default=0, help="Starting frame number")
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
outPath = args.outPath if args.outPath else join(inFolder, "renders")
os.makedirs(outPath, exist_ok=True)


# -------------------------
# Settings
# -------------------------
cam_name = "Camera"

# Mesh names in the Blender scene (must match objects loaded by load_initial_meshes.py)
# Maps: scene object name -> subfolder with npy files
mesh_components = {
    "Box1": "box1",
    "Box2": "box2",
    "Box3": "box3",
    "Box4": "box4",
    "Cloth1": "cloth1",
    "Cloth2": "cloth2",
}

stride = args.stride
numFrames = args.numFrames
startFrame = args.startFrame


# -------------------------
# Helpers
# -------------------------
def get_mesh_obj(name: str) -> bpy.types.Object:
    """Get a mesh object by name from the scene."""
    obj = bpy.context.scene.objects.get(name)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Cannot find mesh object '{name}' in the scene.")
    return obj


def update_mesh_vertices(obj: bpy.types.Object, V_np: np.ndarray):
    """
    Update mesh vertices from numpy array.
    V_np: (N,3) float32/float64 in object local space.
    """
    if V_np.ndim != 2 or V_np.shape[1] != 3:
        raise ValueError(f"Expected (N,3) array, got {V_np.shape}.")

    mesh = obj.data
    n_mesh = len(mesh.vertices)
    n_in = V_np.shape[0]
    if n_in != n_mesh:
        raise ValueError(f"Vertex count mismatch for {obj.name}: mesh has {n_mesh}, npy has {n_in}.")

    # Flatten to [x0,y0,z0,x1,y1,z1,...]
    co_flat = V_np.astype(np.float32).reshape(-1)

    # Fast bulk update
    mesh.vertices.foreach_set("co", co_flat)

    # Ensure Blender updates depsgraph
    mesh.update()
    obj.update_tag()


def get_frame_path(component_folder: str, frame_num: int) -> str:
    """Get the npy file path for a given component and frame number."""
    return join(inFolder, component_folder, f"frame_{frame_num:06d}.npy")


def frame_exists(frame_num: int) -> bool:
    """Check if all component npy files exist for a given frame."""
    for obj_name, folder in mesh_components.items():
        if not os.path.exists(get_frame_path(folder, frame_num)):
            return False
    return True


def load_frame(frame_num: int, mesh_objs: dict):
    """Load all component npy files for a given frame and update meshes."""
    for obj_name, folder in mesh_components.items():
        npy_path = get_frame_path(folder, frame_num)
        V = np.load(npy_path)
        update_mesh_vertices(mesh_objs[obj_name], V)


# -------------------------
# Main
# -------------------------
print("=" * 60)
print("Falling Gift Renderer")
print("=" * 60)
print(f"Input folder: {inFolder}")
print(f"Output folder: {outPath}")
print(f"Frames: {startFrame} to {startFrame + numFrames}, stride {stride}")
print("=" * 60)

# Set camera
bpy.context.scene.camera = bpy.context.scene.objects[cam_name]
print(f"Camera: {cam_name}")

# Get all mesh objects
mesh_objs = {}
for obj_name in mesh_components.keys():
    obj = get_mesh_obj(obj_name)
    print(f"Found mesh: {obj.name} ({len(obj.data.vertices)} vertices)")
    mesh_objs[obj_name] = obj

# Deselect all
bpy.ops.object.select_all(action='DESELECT')

# Count available frames
first_component = list(mesh_components.values())[0]
npy_pattern = join(inFolder, first_component, "frame_*.npy")
available_frames = len(glob.glob(npy_pattern))
print(f"Available frames in {first_component}/: {available_frames}")

# Render loop
frame_num = startFrame
rendered_count = 0

while rendered_count < numFrames:
    # Check if frame exists
    if not frame_exists(frame_num):
        print(f"Frame {frame_num} not found. Waiting 60 seconds...")
        time.sleep(60)
        continue
    
    # Load frame data
    print(f"Rendering frame {frame_num}...")
    load_frame(frame_num, mesh_objs)
    
    # Force depsgraph update
    bpy.context.view_layer.update()
    
    # Render
    output_file = join(outPath, f"frame_{frame_num:06d}.png")
    bpy.context.scene.render.filepath = output_file
    bpy.ops.render.render(write_still=True)
    
    print(f"  Saved: {output_file}")
    
    frame_num += stride
    rendered_count += 1

print("=" * 60)
print(f"Rendering complete! {rendered_count} frames rendered.")
print("=" * 60)
