#!/bin/bash

BLENDER="/home/horde/Code/blender-5.0.1-linux-x64/blender"
SCENE="/home/horde/Code/BlenderRenderers/DAT/unroll/unroll.blend"
SCRIPT="/home/horde/Code/BlenderRenderers/DAT/unroll/run.py"
IN_FOLDER="/home/horde/Code/Outputs/unroll/truncation_0_iter_5_20260105_175909"

CUDA_VISIBLE_DEVICES=1 $BLENDER "$SCENE" --background --python "$SCRIPT" -- \
    --inFolder "$IN_FOLDER" \
    --gpu 0 \
    --numFrames 1000

