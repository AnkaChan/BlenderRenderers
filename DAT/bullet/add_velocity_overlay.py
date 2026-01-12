"""
Add velocity overlay to rendered frames using PIL (for custom fonts).

Reads PNG frames + NPY data, overlays velocity text, saves new frames.
No manual work needed - just run and get video-ready frames!
"""

import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

# =============================================================================
# Configuration - EDIT THESE
# =============================================================================

# Paths
DATA_PATH = Path(r"D:\Data\DAT_Sim\bullet_out_of_barrel\fps_600000")
RENDER_FOLDER = DATA_PATH / "Render_cross_section"  # Input rendered PNGs
OUTPUT_FOLDER = DATA_PATH / "Render_cross_section_with_velocity"  # Output with overlay

# Simulation parameters
SIM_FPS = 600000  # Simulation FPS
# Note: RENDER_STRIDE is no longer needed - we extract frame numbers from filenames

# Text overlay settings
FONT_NAME = "tahoma.ttf"  # Tahoma font
FONT_SIZE = 72  # Main text size
TEXT_COLOR = (30, 30, 30)  # Dark gray fill

# Margins from edges
MARGIN = 60


# =============================================================================
# Functions
# =============================================================================

def load_font(font_name, size):
    """Load font, fallback to default if not found."""
    try:
        return ImageFont.truetype(font_name, size)
    except OSError:
        # Try with full Windows font path
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{font_name}", size)
        except OSError:
            print(f"Warning: Font '{font_name}' not found, using default")
            return ImageFont.load_default()


def get_centroid(npy_files_dict, sim_frame):
    """Load NPY and return centroid."""
    if sim_frame not in npy_files_dict:
        return None
    verts = np.load(npy_files_dict[sim_frame])
    return verts.mean(axis=0)


def extract_frame_number(filepath):
    """Extract frame number from filename like 'frame_000050.png' -> 50"""
    stem = Path(filepath).stem  # 'frame_000050'
    parts = stem.split('_')
    return int(parts[-1])  # 50


def get_text_size(draw, text, font):
    """Get text bounding box size."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("🔫 Adding Velocity Overlay to Frames (Tahoma font)")
    print("=" * 60)
    
    # Create output folder
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Load font
    font = load_font(FONT_NAME, FONT_SIZE)
    print(f"Font: {FONT_NAME}, Size: {FONT_SIZE}")
    
    # Get all NPY files and build dict by frame number
    npy_files_list = sorted(DATA_PATH.glob("frame_*.npy"))
    npy_files_dict = {extract_frame_number(f): f for f in npy_files_list}
    print(f"Found {len(npy_files_dict)} NPY files")
    
    # Get rendered PNG files
    png_files = sorted(RENDER_FOLDER.glob("frame_*.png"))
    print(f"Found {len(png_files)} rendered PNG files")
    print(f"Output: {OUTPUT_FOLDER}")
    
    if not png_files:
        print("ERROR: No PNG files found!")
        return
    
    # Track previous frame for velocity calculation (cache centroid!)
    prev_sim_frame = None
    prev_centroid = None
    velocity = 0.0
    freeze_frame = 1010  # Freeze velocity after this frame
    frames_processed = 0
    
    # Process each frame
    for png_file in tqdm(png_files, desc="Processing"):
        # Extract sim frame number from PNG filename
        current_sim_frame = extract_frame_number(png_file)
        
        # Only update velocity until freeze_frame
        if frames_processed < freeze_frame:
            # Load current centroid (only 1 NPY load per frame!)
            current_centroid = get_centroid(npy_files_dict, current_sim_frame)
            
            # Calculate velocity from cached previous centroid
            if prev_centroid is not None and current_centroid is not None:
                displacement_cm = current_centroid - prev_centroid
                frame_delta = current_sim_frame - prev_sim_frame
                time_s = frame_delta / SIM_FPS
                velocity = np.linalg.norm(displacement_cm / time_s) / 100.0  # cm/s to m/s
            
            # Cache for next iteration
            prev_sim_frame = current_sim_frame
            prev_centroid = current_centroid
        # After freeze_frame, velocity stays frozen
        
        # Read image with PIL
        img = Image.open(png_file)
        draw = ImageDraw.Draw(img)
        img_width, img_height = img.size
        
        # === Bottom RIGHT: Velocity ===
        velocity_text = f"{velocity:.0f} m/s"
        vel_w, vel_h = get_text_size(draw, velocity_text, font)
        vel_x = img_width - MARGIN - vel_w
        vel_y = img_height - MARGIN - vel_h
        draw.text((vel_x, vel_y), velocity_text, font=font, fill=TEXT_COLOR)
        
        # Save
        output_path = OUTPUT_FOLDER / png_file.name
        img.save(output_path)
        frames_processed += 1
    
    print(f"\n✅ Done! {frames_processed} frames saved to:")
    print(f"   {OUTPUT_FOLDER}")
    print(f"\n🔫 frozen speed (at frame {freeze_frame}): {velocity:.0f} m/s")


if __name__ == "__main__":
    main()
