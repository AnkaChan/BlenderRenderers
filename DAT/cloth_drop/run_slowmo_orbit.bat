@echo off

set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set "SCENE=Fall_cylinder_manyLayers.blend"
set "SCRIPT=run_slowmo_orbit.py"
set "IN_FOLDER=D:\Data\DAT_Sim\ClothDrop\200_layers\20260108_020623\filtered_butter_o2_c025_linear_s160_t250_m2"

set CUDA_VISIBLE_DEVICES=0

"%BLENDER%" "%SCENE%" --background --python "%SCRIPT%" -- ^
    --inFolder "%IN_FOLDER%" ^
    --gpu 0 ^
    --startFrame 40 ^
    --endFrame 100 ^
    --slowdown 5 ^
    --stride 10 ^
    --orbitDegrees 360 ^
    --orbitCenter 0.0 0.0 0.0 ^
    --lookAt 0.0 0.0 0.0 ^
    --numLayers 200

pause

