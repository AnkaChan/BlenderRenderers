# Blender Python script to render multiphysics simulation sequences
# Run from command line:
#   blender Multi-physics.blend --background --python run.py -- --inFolder "D:\Data\DAT_Sim\multiphysics_drop\4x5_YYYYMMDD_HHMMSS"
#
# Or for interactive preview (no rendering):
#   blender Multi-physics.blend --python run.py -- --inFolder "..." --preview

import os
import glob
import time
import sys
import argparse
import json
import bpy
import numpy as np
from pathlib import Path
from os.path import join
from mathutils import Matrix, Quaternion, Vector

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
    
    parser = argparse.ArgumentParser(description="Render multiphysics npy sequence with Blender")
    parser.add_argument("--inFolder", type=str, required=True, help="Input folder containing .npy files")
    parser.add_argument("--outPath", type=str, default=None, help="Output folder for rendered images")
    parser.add_argument("--gpu", type=int, default=0, help="GPU index to use (default: 0)")
    parser.add_argument("--numFrames", type=int, default=1000, help="Number of frames to render")
    parser.add_argument("--stride", type=int, default=1, help="Frame stride")
    parser.add_argument("--startFrame", type=int, default=0, help="Start frame index")
    parser.add_argument("--preview", action="store_true", help="Preview mode (no rendering)")
    parser.add_argument("--scale", type=float, default=0.01, help="Scale factor (cm to m)")
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

# Setup GPU (skip in preview mode for faster startup)
if not args.preview:
    setup_optix(gpu_index=args.gpu)

# -------------------------
# Paths
# -------------------------
inFolder = args.inFolder
outPath = args.outPath if args.outPath else join(inFolder, "Rendering")
os.makedirs(outPath, exist_ok=True)

# Load mesh info
mesh_info_path = join(inFolder, "initial_meshes", "mesh_info.json")
if not os.path.exists(mesh_info_path):
    raise FileNotFoundError(f"mesh_info.json not found at {mesh_info_path}")

with open(mesh_info_path, 'r') as f:
    mesh_info = json.load(f)

print(f"Input folder: {inFolder}")
print(f"Output path: {outPath}")

# -------------------------
# Settings
# -------------------------
cam_name = "Camera"
scale = args.scale  # cm to m conversion
stride = args.stride
numFrames = args.numFrames
startFrame = args.startFrame

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
        raise ValueError(f"Vertex count mismatch for {obj.name}: mesh has {n_mesh}, npy has {n_in}.")

    # Flatten to [x0,y0,z0,x1,y1,z1,...]
    co_flat = V_np.astype(np.float32).reshape(-1)

    # Fast bulk update
    mesh.vertices.foreach_set("co", co_flat)

    # Ensure Blender updates depsgraph
    mesh.update()
    obj.update_tag()

def update_rigid_body_transform(obj: bpy.types.Object, position: np.ndarray, quaternion: np.ndarray, scale_factor: float):
    """
    Update rigid body transform from position (3,) and quaternion (4,) [w,x,y,z].
    """
    # Scale position
    pos = Vector(position * scale_factor)
    
    # Quaternion from Newton is [w, x, y, z]
    quat = Quaternion((quaternion[0], quaternion[1], quaternion[2], quaternion[3]))
    
    # Set transform
    obj.location = pos
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = quat

# -------------------------
# Build mesh mapping
# -------------------------
print("\n--- Mesh Mapping ---")

# Soft bodies mapping
soft_body_meshes = []
for sb_info in mesh_info.get("soft_bodies", []):
    name = sb_info["name"]
    try:
        obj = get_mesh_obj(name)
        soft_body_meshes.append({
            "obj": obj,
            "name": name,
            "particle_start": sb_info["particle_start"],
            "num_vertices": sb_info["num_vertices"],
        })
        print(f"  Soft body: {name} (start: {sb_info['particle_start']}, verts: {sb_info['num_vertices']})")
    except RuntimeError as e:
        print(f"  Warning: {e}")

# Rigid bodies mapping
rigid_body_meshes = []
for rb_info in mesh_info.get("rigid_bodies", []):
    name = rb_info["name"]
    try:
        obj = get_mesh_obj(name)
        rigid_body_meshes.append({
            "obj": obj,
            "name": name,
            "body_idx": rb_info["body_idx"],
            "local_verts": np.load(join(inFolder, "initial_meshes", f"{name}_vertices_local.npy")),
        })
        print(f"  Rigid body: {name} (body_idx: {rb_info['body_idx']})")
    except RuntimeError as e:
        print(f"  Warning: {e}")

# Cloth mapping
cloth_mesh = None
cloth_info = mesh_info.get("cloth")
if cloth_info:
    name = cloth_info["name"]
    try:
        obj = get_mesh_obj(name)
        # particle_start may not exist in older mesh_info.json files
        # Calculate from soft bodies if not present
        if "particle_start" in cloth_info:
            particle_start = cloth_info["particle_start"]
        else:
            # Cloth starts after all soft bodies
            particle_start = 0
            for sb in soft_body_meshes:
                end = sb["particle_start"] + sb["num_vertices"]
                if end > particle_start:
                    particle_start = end
        cloth_mesh = {
            "obj": obj,
            "name": name,
            "particle_start": particle_start,
            "num_vertices": cloth_info["num_vertices"],
        }
        print(f"  Cloth: {name} (start: {particle_start}, verts: {cloth_info['num_vertices']})")
    except RuntimeError as e:
        print(f"  Warning: {e}")

# -------------------------
# Main Loop
# -------------------------
print("\n--- Starting Render Loop ---")

# Set camera
if cam_name in bpy.context.scene.objects:
    bpy.context.scene.camera = bpy.context.scene.objects[cam_name]
    print(f"Camera: {cam_name}")

# Collect npy files (particle positions)
npy_pattern = join(inFolder, "frame_*.npy")
npy_files = sorted(glob.glob(npy_pattern))
print(f"Found {len(npy_files)} npy frames")

# Also check for rigid body transforms
body_q_pattern = join(inFolder, "body_q_*.npy")
body_q_files = sorted(glob.glob(body_q_pattern))
print(f"Found {len(body_q_files)} body_q frames")
if len(body_q_files) == 0 and len(rigid_body_meshes) > 0:
    print("WARNING: No body_q files found! Rigid bodies will NOT be animated.")
    print("         Re-run the Newton simulation to generate body_q_*.npy files.")

fileId = startFrame
while fileId < startFrame + numFrames:
    if fileId >= len(npy_files):
        if args.preview:
            print("End of frames.")
            break
        print("No more npy frames yet. Waiting 60 seconds...")
        time.sleep(60)
        npy_files = sorted(glob.glob(npy_pattern))
        body_q_files = sorted(glob.glob(body_q_pattern))
        continue

    npy_path = npy_files[fileId]
    frame_name = Path(npy_path).stem
    print(f"Processing: {frame_name}")

    # Load particle positions
    particle_q = np.load(npy_path)
    
    # Scale to meters
    particle_q = particle_q * scale

    # Update soft bodies
    for sb in soft_body_meshes:
        start = sb["particle_start"]
        end = start + sb["num_vertices"]
        V = particle_q[start:end]
        update_mesh_vertices(sb["obj"], V)

    # Update cloth
    if cloth_mesh:
        start = cloth_mesh["particle_start"]
        end = start + cloth_mesh["num_vertices"]
        V = particle_q[start:end]
        update_mesh_vertices(cloth_mesh["obj"], V)

    # Update rigid bodies (from body_q if available)
    if fileId < len(body_q_files) and len(rigid_body_meshes) > 0:
        body_q_path = body_q_files[fileId]
        body_q = np.load(body_q_path)  # Shape: (num_bodies, 7) - [px, py, pz, qx, qy, qz, qw]
        
        for rb in rigid_body_meshes:
            body_idx = rb["body_idx"]
            if body_idx < len(body_q):
                transform = body_q[body_idx]
                position = transform[:3]  # in cm
                quat_xyzw = transform[3:7]  # [qx, qy, qz, qw] from Warp
                
                # Load local vertices (in cm)
                local_verts = rb["local_verts"]
                
                # Convert quaternion for Blender: [w, x, y, z]
                quat_blender = Quaternion((quat_xyzw[3], quat_xyzw[0], quat_xyzw[1], quat_xyzw[2]))
                rot_matrix = np.array(quat_blender.to_matrix().to_3x3())
                
                # Transform: rotate then translate (all in cm)
                world_verts = (local_verts @ rot_matrix.T) + position
                
                # Scale to meters and update mesh
                world_verts = (world_verts * scale).astype(np.float32)
                update_mesh_vertices(rb["obj"], world_verts)

    # Force scene update
    bpy.context.view_layer.update()

    # Render (unless preview mode)
    if not args.preview:
        bpy.context.scene.render.filepath = join(outPath, frame_name + ".png")
        bpy.ops.render.render(write_still=True)
    else:
        # In preview mode, just update viewport
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

    fileId += stride

print("\n--- Done! ---")
