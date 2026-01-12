"""
Generate velocity data for Premiere Pro overlay.

This script reads all NPY frames and outputs a CSV with:
- Frame number (video frame, accounting for stride)
- Time (real-world time in milliseconds)
- Velocity (m/s)
- Position Z (cm)

You can import this CSV into Premiere or use it for manual keyframing.
"""

import numpy as np
from pathlib import Path
import csv

# =============================================================================
# Configuration - EDIT THESE
# =============================================================================

# Path to simulation NPY files
DATA_PATH = Path(r"D:\Data\DAT_Sim\bullet_out_of_barrel\fps_600000")

# Simulation parameters
SIM_FPS = 600000  # Simulation FPS
RENDER_STRIDE = 50  # Frame stride used in rendering

# Output
OUTPUT_CSV = DATA_PATH / "velocity_data.csv"


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("🔫 Generating Velocity Data for Premiere")
    print("=" * 60)
    
    # Get all NPY files
    npy_files = sorted(DATA_PATH.glob("frame_*.npy"))
    print(f"Found {len(npy_files)} total frames")
    
    # Filter by stride (only rendered frames)
    rendered_files = npy_files[::RENDER_STRIDE]
    print(f"Rendered frames (stride {RENDER_STRIDE}): {len(rendered_files)}")
    
    # Calculate velocities
    data = []
    prev_centroid = None
    
    for video_frame, npy_file in enumerate(rendered_files):
        # Load vertices
        vertices = np.load(npy_file)
        centroid = vertices.mean(axis=0)
        
        # Extract sim frame number from filename
        sim_frame = int(npy_file.stem.split("_")[-1])
        
        # Real time in milliseconds
        real_time_ms = (sim_frame / SIM_FPS) * 1000
        
        # Calculate velocity
        if prev_centroid is not None:
            # Displacement in cm over RENDER_STRIDE frames
            displacement_cm = centroid - prev_centroid
            time_s = RENDER_STRIDE / SIM_FPS
            velocity_cm_s = displacement_cm / time_s
            velocity_m_s = velocity_cm_s / 100.0  # cm to m
            speed_m_s = np.linalg.norm(velocity_m_s)
        else:
            speed_m_s = 0.0
        
        data.append({
            'video_frame': video_frame,
            'sim_frame': sim_frame,
            'time_ms': round(real_time_ms, 3),
            'velocity_m_s': round(speed_m_s, 1),
            'z_position_cm': round(centroid[2], 2),
        })
        
        prev_centroid = centroid
        
        if video_frame % 10 == 0:
            print(f"  Frame {video_frame}: {speed_m_s:.1f} m/s, z={centroid[2]:.1f} cm")
    
    # Write CSV
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['video_frame', 'sim_frame', 'time_ms', 'velocity_m_s', 'z_position_cm'])
        writer.writeheader()
        writer.writerows(data)
    
    print(f"\n✅ Saved: {OUTPUT_CSV}")
    print(f"   {len(data)} frames")
    print(f"   Max velocity: {max(d['velocity_m_s'] for d in data)} m/s")
    
    # Also create a simple text version for quick reference
    txt_file = DATA_PATH / "velocity_data.txt"
    with open(txt_file, 'w') as f:
        f.write("Video Frame | Time (ms) | Velocity (m/s)\n")
        f.write("-" * 45 + "\n")
        for d in data:
            f.write(f"{d['video_frame']:11d} | {d['time_ms']:9.3f} | {d['velocity_m_s']:14.1f}\n")
    
    print(f"✅ Saved: {txt_file}")
    
    print("\n" + "=" * 60)
    print("For Premiere Pro:")
    print("  1. Import CSV as spreadsheet reference")
    print("  2. Create text layer with velocity")
    print("  3. Keyframe text at each frame change")
    print("  OR use Essential Graphics template with CSV data")
    print("=" * 60)


if __name__ == "__main__":
    main()
