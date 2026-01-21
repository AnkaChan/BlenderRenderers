@echo off
cd /d "%~dp0"

set BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set BLEND_FILE="FallingGift.blend"
set IN_FOLDER="D:\Data\DAT_Sim\falling_gift_comparison\comparison_20260120_215433\truncation_mode_1"
set OUT_PATH="D:\Data\DAT_Sim\falling_gift_comparison\comparison_20260120_215433\truncation_mode_1\renders"

%BLENDER% %BLEND_FILE% --background --python render_sequence.py -- --inFolder %IN_FOLDER% --outPath %OUT_PATH% --stride 10 --numFrames 800

pause
