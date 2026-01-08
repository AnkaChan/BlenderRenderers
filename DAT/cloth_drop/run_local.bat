@echo off

set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set "SCENE=Fall_cylinder_manyLayers.blend"
set "SCRIPT=run.py"
set "IN_FOLDER=D:\Data\DAT_Sim\ClothDrop\200_layers\20260108_020623\filtered_butter_o2_c005_linear_s160_t300_m2"

set CUDA_VISIBLE_DEVICES=0

"%BLENDER%" "%SCENE%" --background --python "%SCRIPT%" -- --inFolder "%IN_FOLDER%" --gpu 0 --numFrames 600 --stride 1 --numLayers 200

pause
