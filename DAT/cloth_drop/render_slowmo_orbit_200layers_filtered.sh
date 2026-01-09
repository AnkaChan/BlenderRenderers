#!/bin/bash

BLENDER="/home/horde/Code/blender-5.0.1-linux-x64/blender"
SCENE="/home/horde/Code/BlenderRenderers/ScenesForCloth/Fall_cylinder_manyLayers.blend"
SCRIPT="/home/horde/Code/BlenderRenderers/DAT/cloth_drop/run_slowmo_orbit.py"
IN_FOLDER="/home/horde/Code/Outputs/ClothDrop/200_layers/filtered_butter_o2_c005_linear_s160_t300_m2"

CUDA_VISIBLE_DEVICES=0 $BLENDER "$SCENE" --background --python "$SCRIPT" -- \
    --inFolder "$IN_FOLDER" \
    --gpu 0 \
    --startFrame 40 \
    --endFrame 100 \
    --slowdown 5 \
    --stride 1 \
    --orbitDegrees 360 \
    --orbitCenter 0.0 0.0 0.0 \
    --lookAt 0.0 0.0 0.0 \
    --numLayers 200

