"""
Slow Motion Orbit Render

Renders a selected range of frames with:
- Slow motion via frame interpolation
- Camera orbiting around Z axis
"""

import os, glob, math, sys, argparse
import bpy
import numpy as np
from pathlib import Path
from os.path import join
from mathutils import Vector, Euler

# -------------------------
# Argument Parsing
# -------------------------
def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    parser = argparse.ArgumentParser(description="Slow-mo orbit render for npy sequences")
    parser.add_argument("--inFolder", type=str, required=True, help="Input folder containing .npy files")
    parser.add_argument("--outPath", type=str, default=None, help="Output folder for rendered images")
    parser.add_argument("--gpu", type=int, default=0, help="GPU index to use (default: 0)")
    
    # Frame range
    parser.add_argument("--startFrame", type=int, default=0, help="Start frame index")
    parser.add_argument("--endFrame", type=int, default=100, help="End frame index")
    parser.add_argument("--stride", type=int, default=1, help="Source frame stride (skip frames)")
    
    # Slow motion
    parser.add_argument("--slowdown", type=int, default=4, help="Slowdown factor (interpolated frames per source frame)")
    
    # Camera orbit
    parser.add_argument("--orbitDegrees", type=float, default=360.0, help="Total camera rotation in degrees")
    parser.add_argument("--orbitCenter", type=float, nargs=3, default=[0.0, 0.0, 0.0], help="Orbit center point (x y z)")
    parser.add_argument("--lookAt", type=float, nargs=3, default=[0.0, 0.0, 0.0], help="Point camera looks at (x y z)")
    
    # Mesh config
    parser.add_argument("--numLayers", type=int, default=200, help="Number of cloth layers")
    parser.add_argument("--meshPrefix", type=str, default="initial_mesh", help="Mesh name prefix")
    
    return parser.parse_args(argv)

args = parse_args()

# -------------------------
# GPU / OptiX Setup
# -------------------------
def setup_optix(gpu_index=0):
    """Enable OptiX rendering on a specific GPU."""
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    
    for device in prefs.devices:
        device.use = False
    
    gpu_devices = [d for d in prefs.devices if d.type == 'OPTIX']
    if gpu_index < len(gpu_devices):
        gpu_devices[gpu_index].use = True
        print(f"Using OptiX device: {gpu_devices[gpu_index].name}")
    else:
        print(f"Warning: GPU index {gpu_index} not found. Available: {len(gpu_devices)}")
        if gpu_devices:
            gpu_devices[0].use = True
    
    bpy.context.scene.cycles.device = 'GPU'

setup_optix(gpu_index=args.gpu)

# -------------------------
# Paths
# -------------------------
inFolder = args.inFolder

# Generate descriptive output folder name
if args.outPath:
    outPath = args.outPath
else:
    stride_str = f"_stride{args.stride}" if args.stride > 1 else ""
    folder_name = f"Render_f{args.startFrame}-{args.endFrame}{stride_str}_slow{args.slowdown}x_orbit{int(args.orbitDegrees)}deg"
    outPath = join(inFolder, folder_name)

os.makedirs(outPath, exist_ok=True)

npy_pattern = join(inFolder, "*.npy")

# -------------------------
# Settings
# -------------------------
cam_name = "Camera"
start_frame = args.startFrame
end_frame = args.endFrame
src_stride = args.stride  # renamed to avoid confusion
slowdown = args.slowdown
orbit_degrees = args.orbitDegrees
orbit_center = Vector(args.orbitCenter)
look_at = Vector(args.lookAt)

# Mesh names
num_layers = args.numLayers
mesh_prefix = args.meshPrefix
mesh_names = [f"{mesh_prefix}_{i:03d}_cloth_main_cloth_layer{i}" for i in range(num_layers)]

print(f"=" * 60)
print(f"Slow Motion Orbit Render")
print(f"  Frame range:    {start_frame} -> {end_frame} (stride {src_stride})")
print(f"  Slowdown:       {slowdown}x")
print(f"  Orbit:          {orbit_degrees}° around Z")
print(f"  Orbit center:   {list(orbit_center)}")
print(f"  Look at:        {list(look_at)}")
print(f"  Num layers:     {num_layers}")
print(f"  Output:         {outPath}")
print(f"=" * 60)

# -------------------------
# Helpers
# -------------------------
def get_mesh_obj(name: str) -> bpy.types.Object:
    obj = bpy.context.scene.objects.get(name)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Cannot find mesh object '{name}' in the scene.")
    return obj

def update_mesh_vertices(obj: bpy.types.Object, V_np: np.ndarray):
    """Update mesh vertices from numpy array."""
    if V_np.ndim != 2 or V_np.shape[1] != 3:
        raise ValueError(f"Expected (N,3) array, got {V_np.shape}.")

    mesh = obj.data
    n_mesh = len(mesh.vertices)
    n_in = V_np.shape[0]
    if n_in != n_mesh:
        raise ValueError(f"Vertex count mismatch: mesh has {n_mesh}, npy has {n_in}.")

    co_flat = V_np.astype(np.float32).reshape(-1)
    mesh.vertices.foreach_set("co", co_flat)
    mesh.update()
    obj.update_tag()

def lerp_vertices(v0: np.ndarray, v1: np.ndarray, t: float) -> np.ndarray:
    """Linear interpolation between two vertex arrays."""
    return v0 * (1.0 - t) + v1 * t

def orbit_camera(camera, orbit_center: Vector, look_at: Vector, initial_location: Vector, angle_rad: float):
    """
    Rotate camera around Z axis passing through orbit_center, looking at look_at point.
    
    Args:
        camera: Blender camera object
        orbit_center: Point to orbit around (rotation axis passes through here)
        look_at: Point camera should look at
        initial_location: Camera's starting position
        angle_rad: Rotation angle in radians
    """
    # Vector from orbit center to initial camera position
    offset = initial_location - orbit_center
    
    # Rotate offset around Z axis
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    new_offset = Vector((
        offset.x * cos_a - offset.y * sin_a,
        offset.x * sin_a + offset.y * cos_a,
        offset.z  # Keep Z offset unchanged
    ))
    
    # New camera position
    camera.location = orbit_center + new_offset
    
    # Point camera at look_at target using Blender's track_to method
    direction = look_at - camera.location
    
    # Use quaternion to rotation - camera looks down -Z, up is +Y
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()

# -------------------------
# Main
# -------------------------

# Get camera
camera = bpy.context.scene.objects[cam_name]
bpy.context.scene.camera = camera
print(f"Camera: {cam_name}")

# Store initial camera state
initial_cam_location = camera.location.copy()
initial_cam_rotation = camera.rotation_euler.copy()
print(f"Initial camera location: {list(initial_cam_location)}")

# Get all mesh objects
mesh_objs = []
for name in mesh_names:
    obj = get_mesh_obj(name)
    mesh_objs.append(obj)
print(f"Loaded {len(mesh_objs)} mesh objects")

bpy.ops.object.select_all(action='DESELECT')
for obj in mesh_objs:
    obj.select_set(state=True)

# Get vertex counts
mesh_vertex_counts = [len(obj.data.vertices) for obj in mesh_objs]

# Collect npy files
npy_files = sorted(glob.glob(npy_pattern))
print(f"Total npy files: {len(npy_files)}")

if end_frame >= len(npy_files):
    print(f"Warning: end_frame ({end_frame}) >= available frames ({len(npy_files)})")
    end_frame = len(npy_files) - 1

# Build list of source frame indices (respecting stride)
source_indices = list(range(start_frame, end_frame + 1, src_stride))
num_source_pairs = len(source_indices) - 1
total_output_frames = num_source_pairs * slowdown
print(f"Source frames: {len(source_indices)} (stride {src_stride}), Output frames: {total_output_frames}")

# Pre-load frames for interpolation
print("Loading frames...")
loaded_frames = {}
for i in source_indices:
    loaded_frames[i] = np.load(npy_files[i])

# Render loop
output_idx = 0
for pair_idx in range(num_source_pairs):
    src_idx_a = source_indices[pair_idx]
    src_idx_b = source_indices[pair_idx + 1]
    frame_a = loaded_frames[src_idx_a]
    frame_b = loaded_frames[src_idx_b]
    
    for sub_idx in range(slowdown):
        # Interpolation factor (0 to 1 within this source frame pair)
        t = sub_idx / slowdown
        
        # Interpolate vertices
        V_interp = lerp_vertices(frame_a, frame_b, t)
        
        # Update all meshes
        start_v = 0
        for i, obj in enumerate(mesh_objs):
            end_v = start_v + mesh_vertex_counts[i]
            update_mesh_vertices(obj, V_interp[start_v:end_v])
            start_v = end_v
        
        # Calculate camera orbit angle
        progress = output_idx / total_output_frames
        angle_rad = math.radians(orbit_degrees * progress)
        orbit_camera(camera, orbit_center, look_at, initial_cam_location, angle_rad)
        
        # Render
        out_file = join(outPath, f"frame_{output_idx:06d}.png")
        bpy.context.scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)
        
        print(f"Rendered {output_idx + 1}/{total_output_frames}: src={src_idx_a}->{src_idx_b}, t={t:.2f}, orbit={math.degrees(angle_rad):.1f}°")
        output_idx += 1

print(f"\nDone! Rendered {output_idx} frames to: {outPath}")

