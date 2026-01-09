@echo off
echo ============================================================
echo 🔫 Bullet Simulation Renderer
echo ============================================================

set BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set BLEND_FILE="D:\Code\Graphics\BlenderRenderers\DAT\bullet\bullet_side_cross_section.blend"
set SCRIPT="D:\Code\Graphics\BlenderRenderers\DAT\bullet\run_bullet_sim.py"

set IN_FOLDER="D:\Data\DAT_Sim\bullet_out_of_barrel\fps_600000"
set OUT_PATH="D:\Data\DAT_Sim\bullet_out_of_barrel\fps_600000\Rendering_side_cross_section"
set GPU=0
set NUM_FRAMES=10000
set STRIDE=50

%BLENDER% %BLEND_FILE% --background --python %SCRIPT% -- --inFolder %IN_FOLDER% --outPath %OUT_PATH% --gpu %GPU% --numFrames %NUM_FRAMES% --stride %STRIDE%

echo ============================================================
echo ✅ Rendering complete!
echo ============================================================
pause
