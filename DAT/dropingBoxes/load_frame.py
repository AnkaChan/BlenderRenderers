"""
Blender script to load a specific frame state from Falling Gift simulation.

Usage:
    1. Open Blender
    2. Modify EXPERIMENT_PATH and FRAME_NUMBER below
    3. Run this script from the Scripting workspace

The script loads initial mesh topology from PLY files, then updates
vertex positions from the corresponding frame's NPY files.
"""

import bpy
import numpy as np
import os
from pathlib import Path


# ============ CONFIGURE THESE ============
EXPERIMENT_PATH = r"D:\Data\DAT_sim\falling_gift_comparison\truncation_mode_1_100iter_20260121_XXXXXX"
FRAME_NUMBER = 100  # Which frame to load
# =========================================


def clear_simulation_objects():
    """Remove only simulation mesh objects (Box1-4, Cloth1-2), keep everything else."""
    # Only remove objects we created
    names_to_remove = ["Box1", "Box2", "Box3", "Box4", "Cloth1", "Cloth2"]
    
    for name in names_to_remove:
        if name in bpy.data.objects:
            obj = bpy.data.objects[name]
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # Clean up orphaned meshes
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    
    # Clean up orphaned materials with our naming pattern
    for mat in bpy.data.materials:
        if mat.users == 0 and "_Material" in mat.name:
            bpy.data.materials.remove(mat)
    
    print("Cleared simulation objects (Box1-4, Cloth1-2)")


def load_ply_topology(filepath):
    """
    Load PLY file and return vertices and faces.
    Returns (vertices, faces) as numpy arrays.
    """
    vertices = []
    faces = []
    
    with open(filepath, 'r') as f:
        # Parse header
        num_vertices = 0
        num_faces = 0
        in_header = True
        
        for line in f:
            line = line.strip()
            if in_header:
                if line.startswith("element vertex"):
                    num_vertices = int(line.split()[-1])
                elif line.startswith("element face"):
                    num_faces = int(line.split()[-1])
                elif line == "end_header":
                    in_header = False
            else:
                # Parse data
                parts = line.split()
                if len(vertices) < num_vertices:
                    vertices.append([float(x) for x in parts[:3]])
                elif len(faces) < num_faces:
                    # Skip the first number (vertex count per face)
                    faces.append([int(x) for x in parts[1:4]])
    
    return np.array(vertices), np.array(faces)


def create_mesh_from_data(name, vertices, faces):
    """Create a Blender mesh object from vertices and faces."""
    # Create mesh data
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices.tolist(), [], faces.tolist())
    mesh.update()
    
    # Create object
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    return obj


def create_material(name, color, metallic=0.0, roughness=0.5):
    """Create a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    
    return mat


def load_frame(experiment_path, frame_number, clear_existing=True):
    """
    Load a specific frame from the experiment.
    
    Args:
        experiment_path: Path to experiment folder
        frame_number: Frame number to load
        clear_existing: If True, remove existing mesh objects first
    """
    experiment_path = Path(experiment_path)
    
    if not experiment_path.exists():
        print(f"ERROR: Experiment path does not exist: {experiment_path}")
        return
    
    if clear_existing:
        clear_simulation_objects()
    
    # Define components with their colors
    components = {
        "box1": ("Box1", (0.0, 0.3, 0.15), "initial_box1.ply"),
        "box2": ("Box2", (0.0, 0.35, 0.17), "initial_box2.ply"),
        "box3": ("Box3", (0.0, 0.4, 0.2), "initial_box3.ply"),
        "box4": ("Box4", (0.0, 0.45, 0.22), "initial_box4.ply"),
        "cloth1": ("Cloth1", (0.8, 0.1, 0.1), "initial_cloth1.ply"),
        "cloth2": ("Cloth2", (0.9, 0.15, 0.1), "initial_cloth2.ply"),
    }
    
    # Create collections
    if "Boxes" not in bpy.data.collections:
        boxes_collection = bpy.data.collections.new("Boxes")
        bpy.context.scene.collection.children.link(boxes_collection)
    else:
        boxes_collection = bpy.data.collections["Boxes"]
        
    if "Cloth" not in bpy.data.collections:
        cloth_collection = bpy.data.collections.new("Cloth")
        bpy.context.scene.collection.children.link(cloth_collection)
    else:
        cloth_collection = bpy.data.collections["Cloth"]
    
    # Format frame number
    frame_str = f"{frame_number:06d}"
    
    # Load each component
    for comp_dir, (name, color, ply_file) in components.items():
        # Get topology from PLY
        ply_path = experiment_path / ply_file
        if not ply_path.exists():
            print(f"WARNING: PLY not found: {ply_path}")
            continue
            
        _, faces = load_ply_topology(str(ply_path))
        
        # Get positions from NPY
        npy_path = experiment_path / comp_dir / f"frame_{frame_str}.npy"
        if not npy_path.exists():
            print(f"WARNING: NPY not found: {npy_path}")
            # Fall back to initial positions
            vertices, _ = load_ply_topology(str(ply_path))
        else:
            vertices = np.load(str(npy_path))
        
        print(f"Loading: {name} (frame {frame_number})")
        
        # Create mesh object
        obj = create_mesh_from_data(name, vertices, faces)
        
        # Create and assign material
        mat = create_material(f"{name}_Material", color, roughness=0.4)
        obj.data.materials.append(mat)
        
        # Move to appropriate collection
        bpy.context.scene.collection.objects.unlink(obj)
        if "Box" in name:
            boxes_collection.objects.link(obj)
        else:
            cloth_collection.objects.link(obj)
        
        # Smooth shading for cloth
        if "Cloth" in name:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.shade_smooth()
    
    bpy.ops.object.select_all(action='DESELECT')
    print(f"\nLoaded frame {frame_number} from: {experiment_path}")


# Main execution
if __name__ == "__main__":
    load_frame(EXPERIMENT_PATH, FRAME_NUMBER)
