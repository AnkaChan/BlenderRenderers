@echo off
cd /d "%~dp0"

set BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set BLEND_FILE="Multi-physics.blend"
set IN_FOLDER="D:\Data\DAT_Sim\multiphysics_drop\4x5_20260119_005251"
set OUT_PATH="D:\Data\DAT_Sim\multiphysics_drop\4x5_20260119_005251\Rendering_test"

%BLENDER% %BLEND_FILE% --background --python run.py -- --inFolder %IN_FOLDER% --outPath %OUT_PATH% --stride 10 --numFrames 300

pause
