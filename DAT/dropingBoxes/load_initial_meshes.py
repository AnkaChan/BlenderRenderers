"""
Blender script to load initial mesh files from Falling Gift simulation.

Usage:
    1. Open Blender
    2. Run this script from the Scripting workspace, OR
    3. Run from command line:
       blender --python load_initial_meshes.py -- --input "D:\Data\DAT_sim\falling_gift_comparison\experiment_folder"

The script loads:
    - initial_box1.ply through initial_box4.ply (soft body blocks)
    - initial_cloth1.ply and initial_cloth2.ply (cloth straps)
"""

import bpy
import os
import sys
from pathlib import Path


# Default input path (modify this or pass via command line)
DEFAULT_INPUT_PATH = r"D:\Data\DAT_sim\falling_gift_comparison"


def clear_scene():
    """Remove all mesh objects from the scene."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.select_set(True)
    bpy.ops.object.delete()


def import_ply(filepath, name):
    """Import a PLY file and rename the object."""
    bpy.ops.wm.ply_import(filepath=filepath)
    # The imported object is automatically selected
    obj = bpy.context.selected_objects[0]
    obj.name = name
    return obj


def create_material(name, color, metallic=0.0, roughness=0.5):
    """Create a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    # Materials use nodes by default in Blender 4.0+
    
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    
    return mat


def load_falling_gift_meshes(input_path):
    """
    Load all initial meshes from a Falling Gift experiment folder.
    
    Args:
        input_path: Path to experiment folder containing initial_*.ply files
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"ERROR: Input path does not exist: {input_path}")
        return
    
    # Define meshes to load with their colors
    meshes = {
        # Boxes (dark green)
        "initial_box1.ply": ("Box1", (0.0, 0.3, 0.15)),
        "initial_box2.ply": ("Box2", (0.0, 0.35, 0.17)),
        "initial_box3.ply": ("Box3", (0.0, 0.4, 0.2)),
        "initial_box4.ply": ("Box4", (0.0, 0.45, 0.22)),
        # Cloth straps (red/orange ribbon colors)
        "initial_cloth1.ply": ("Cloth1", (0.8, 0.1, 0.1)),
        "initial_cloth2.ply": ("Cloth2", (0.9, 0.15, 0.1)),
    }
    
    # Create collections for organization
    boxes_collection = bpy.data.collections.new("Boxes")
    cloth_collection = bpy.data.collections.new("Cloth")
    bpy.context.scene.collection.children.link(boxes_collection)
    bpy.context.scene.collection.children.link(cloth_collection)
    
    # Load each mesh
    for filename, (name, color) in meshes.items():
        filepath = input_path / filename
        
        if not filepath.exists():
            print(f"WARNING: File not found: {filepath}")
            continue
        
        print(f"Loading: {filename} -> {name}")
        
        # Import the PLY
        obj = import_ply(str(filepath), name)
        
        # Create and assign material
        mat = create_material(f"{name}_Material", color, roughness=0.4)
        obj.data.materials.append(mat)
        
        # Move to appropriate collection (unlink from all current collections first)
        for coll in obj.users_collection:
            coll.objects.unlink(obj)
        if "Box" in name:
            boxes_collection.objects.link(obj)
        else:
            cloth_collection.objects.link(obj)
        
        # Set smooth shading for cloth
        if "Cloth" in name:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.shade_smooth()
    
    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')
    
    print(f"\nLoaded meshes from: {input_path}")
    print("Tip: Press Numpad '.' to frame selected, or 'Home' to frame all in 3D view")


def main():
    """Main entry point."""
    # Parse command line arguments (after --)
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    # Simple argument parsing
    input_path = DEFAULT_INPUT_PATH
    for i, arg in enumerate(argv):
        if arg in ("--input", "-i") and i + 1 < len(argv):
            input_path = argv[i + 1]
    
    # Clear existing meshes (optional - comment out to keep existing objects)
    # clear_scene()
    
    # Load the meshes
    load_falling_gift_meshes(input_path)


if __name__ == "__main__":
    main()
