"""
Load a single frame from bullet simulation into Blender.

Usage in Blender:
    1. Open bullet.blend
    2. Open this script in Text Editor
    3. Adjust FRAME_NUMBER and DATA_PATH below
    4. Run script (Alt+P)
"""

import bpy
import numpy as np
from pathlib import Path

# =============================================================================
# Configuration - EDIT THESE
# =============================================================================

# Which frame to load
FRAME_NUMBER = 0

# Path to simulation data
DATA_PATH = Path(r"D:\Data\DAT_Sim\bullet_out_of_barrel\fps_600000")

# Mesh object name in Blender
MESH_NAME = "initial_mesh"

# Barrel mode: "transparent" or "crosssection"
BARREL_MODE = "transparent"


# =============================================================================
# Functions
# =============================================================================

def update_mesh_vertices(obj, V_np):
    """Fast bulk update of mesh vertices."""
    mesh = obj.data
    if len(mesh.vertices) != V_np.shape[0]:
        print(f"ERROR: Vertex count mismatch! Mesh: {len(mesh.vertices)}, Data: {V_np.shape[0]}")
        return False
    
    co_flat = V_np.astype(np.float32).reshape(-1)
    mesh.vertices.foreach_set("co", co_flat)
    mesh.update()
    obj.update_tag()
    return True


def setup_barrel_mode(mode):
    """Set barrel display mode."""
    rifled_barrel = bpy.data.objects.get("rifled_barrel")
    barrel_section = bpy.data.collections.get("barrel side section")
    
    if mode == "transparent":
        if rifled_barrel:
            rifled_barrel.hide_render = False
            rifled_barrel.hide_viewport = False
        if barrel_section:
            for obj in barrel_section.objects:
                obj.hide_render = True
                obj.hide_viewport = True
        print("Barrel: TRANSPARENT")
        
    elif mode == "crosssection":
        if rifled_barrel:
            rifled_barrel.hide_render = True
            rifled_barrel.hide_viewport = True
        if barrel_section:
            for obj in barrel_section.objects:
                obj.hide_render = False
                obj.hide_viewport = False
        print("Barrel: CROSSSECTION")


def load_frame(frame_num, data_path, mesh_name):
    """Load a specific frame."""
    # Find the npy file
    npy_file = data_path / f"frame_{frame_num:06d}.npy"
    
    if not npy_file.exists():
        print(f"ERROR: File not found: {npy_file}")
        return False
    
    # Get mesh object
    mesh_obj = bpy.data.objects.get(mesh_name)
    if mesh_obj is None:
        print(f"ERROR: Mesh '{mesh_name}' not found!")
        return False
    
    # Load and apply vertices
    V = np.load(npy_file)
    print(f"Loaded: {npy_file.name} ({V.shape[0]} vertices)")
    
    if update_mesh_vertices(mesh_obj, V):
        print(f"✅ Frame {frame_num} loaded successfully!")
        return True
    return False


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("🔫 Load Bullet Simulation Frame")
    print("=" * 50)
    
    setup_barrel_mode(BARREL_MODE)
    load_frame(FRAME_NUMBER, DATA_PATH, MESH_NAME)
    
    # Force viewport update
    bpy.context.view_layer.update()
    
    print("=" * 50)
