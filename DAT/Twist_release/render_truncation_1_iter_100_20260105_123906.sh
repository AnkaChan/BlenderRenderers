#!/bin/bash

BLENDER="/home/horde/Code/blender-5.0.1-linux-x64/blender"
SCENE="/home/horde/Code/BlenderRenderers/DAT/Twist_release/Twisting.blend"
SCRIPT="/home/horde/Code/BlenderRenderers/DAT/Twist_release/run.py"
IN_FOLDER="/home/horde/Code/Outputs/cloth_twist_release/truncation_1_iter_100_20260105_123906"

CUDA_VISIBLE_DEVICES=0 $BLENDER "$SCENE" --background --python "$SCRIPT" -- \
    --inFolder "$IN_FOLDER" \
    --gpu 0 \
    --numFrames 1000

