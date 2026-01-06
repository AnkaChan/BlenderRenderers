#!/bin/bash

BLENDER="/home/horde/Code/blender-5.0.1-linux-x64/blender"
SCENE="/home/horde/Code/BlenderRenderers/DAT/oscillating_cloth/oscillating_cloth.blend"
SCRIPT="/home/horde/Code/BlenderRenderers/DAT/oscillating_cloth/run.py"
IN_FOLDER="/home/horde/Code/Outputs/oscilating/truncation_0_iter_10_20260105_235326"

CUDA_VISIBLE_DEVICES=0 $BLENDER "$SCENE" --background --python "$SCRIPT" -- \
    --inFolder "$IN_FOLDER" \
    --gpu 0 \
    --numFrames 1000

