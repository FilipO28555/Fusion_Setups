#!/usr/bin/env python3
"""
Combine PIConGPU PNG outputs from multiple species into animated GIFs.
Each species is colored differently and overlaid into a single animation.

Usage:
    python combine_pngs_to_gif.py --input /path/to/simOutput --output combined.gif
    python combine_pngs_to_gif.py --input /path/to/simOutput --output combined.gif --fps 10
    python combine_pngs_to_gif.py --input /path/to/simOutput --output combined.gif --species d t He4
"""

import argparse
import os
import glob
import re
from pathlib import Path

import numpy as np
from PIL import Image

# =============================================================================
# SPECIES COLOR CONFIGURATION
# =============================================================================
# Edit this dictionary to change colors for each species
# Colors are in RGB format (0-255)
# You can use any species name that matches your PIConGPU output folders

SPECIES_COLORS = {
    'd': (0, 100, 255),      # Deuterons - Blue
    't': (255, 50, 50),      # Tritons - Red
    'He4': (50, 255, 50),    # Helium-4 - Green
    'n': (255, 255, 0),      # Neutrons - Yellow
    'e': (255, 0, 255),      # Electrons - Magenta
    'p': (255, 165, 0),      # Protons - Orange
    'C': (0, 255, 255),      # Carbon - Cyan
    'N': (128, 0, 128),      # Nitrogen - Purple
}

# Background color (RGB)
BACKGROUND_COLOR = (0, 0, 0)  # Black


def find_png_folders(sim_output_path: str) -> dict:
    """
    Find all PNG output folders in the simulation output directory.
    
    Returns:
        dict: {species_name: folder_path}
    """
    folders = {}
    for item in os.listdir(sim_output_path):
        item_path = os.path.join(sim_output_path, item)
        if os.path.isdir(item_path) and item.startswith('png'):
            # Extract species name from folder name (e.g., 'pngDeuterons' -> 'd')
            # or use the folder name directly
            species = item.replace('png', '')
            
            # Map common folder names to species codes
            name_mapping = {
                'Deuterons': 'd',
                'Tritons': 't',
                'Neutrons': 'n',
                'Electrons': 'e',
                'He4': 'He4',
                'Protons': 'p',
            }
            
            species_code = name_mapping.get(species, species)
            folders[species_code] = item_path
    
    return folders


def get_sorted_pngs(folder: str) -> list:
    """
    Get list of PNG files sorted by timestep number.
    """
    png_files = glob.glob(os.path.join(folder, '*.png'))
    
    def extract_number(filename):
        # Extract number from filename like 'yx_0.5_0000100.png'
        match = re.search(r'(\d+)\.png$', filename)
        return int(match.group(1)) if match else 0
    
    return sorted(png_files, key=extract_number)


def load_and_colorize(png_path: str, color: tuple) -> np.ndarray:
    """
    Load a grayscale PNG and colorize it with the given RGB color.
    
    Args:
        png_path: Path to PNG file
        color: RGB tuple (r, g, b) with values 0-255
    
    Returns:
        numpy array of shape (H, W, 4) with RGBA values
    """
    img = Image.open(png_path)
    
    # Convert to grayscale if needed
    if img.mode != 'L':
        img = img.convert('L')
    
    # Convert to numpy array and normalize to 0-1
    gray = np.array(img).astype(np.float32) / 255.0
    
    # Create RGBA image
    h, w = gray.shape
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    
    # Apply color based on intensity
    rgba[:, :, 0] = gray * color[0] / 255.0  # R
    rgba[:, :, 1] = gray * color[1] / 255.0  # G
    rgba[:, :, 2] = gray * color[2] / 255.0  # B
    rgba[:, :, 3] = gray  # Alpha = intensity
    
    return rgba


def combine_frames(frame_paths: dict, colors: dict, background: tuple,
                   dx: float = None, scale_length: float = None) -> Image.Image:
    """
    Combine multiple species frames into a single image.
    
    Args:
        frame_paths: {species: png_path}
        colors: {species: (r, g, b)}
        background: Background RGB color
        dx: Cell size in meters (for scale bar)
        scale_length: Desired scale bar length in meters (auto if None)
    
    Returns:
        Combined PIL Image
    """
    from PIL import ImageDraw, ImageFont
    
    # Load first image to get dimensions
    first_species = list(frame_paths.keys())[0]
    first_img = Image.open(frame_paths[first_species])
    w, h = first_img.size
    
    # Initialize with background color
    combined = np.zeros((h, w, 3), dtype=np.float32)
    combined[:, :, 0] = background[0] / 255.0
    combined[:, :, 1] = background[1] / 255.0
    combined[:, :, 2] = background[2] / 255.0
    
    # Overlay each species
    for species, png_path in frame_paths.items():
        if species not in colors:
            print(f"Warning: No color defined for species '{species}', using white")
            color = (255, 255, 255)
        else:
            color = colors[species]
        
        rgba = load_and_colorize(png_path, color)
        alpha = rgba[:, :, 3:4]  # Keep as 3D for broadcasting
        
        # Alpha blending: combined = combined * (1 - alpha) + new * alpha
        combined = combined * (1 - alpha) + rgba[:, :, :3] * alpha
    
    # Convert to uint8
    combined = (np.clip(combined, 0, 1) * 255).astype(np.uint8)
    
    img = Image.fromarray(combined, mode='RGB')
    
    # Add scale bar if dx is provided
    if dx is not None:
        img = add_scale_bar(img, dx, scale_length)
    
    return img


def add_scale_bar(img: Image.Image, dx: float, scale_length: float = None) -> Image.Image:
    """
    Add a scale bar to the image.
    
    Args:
        img: PIL Image
        dx: Cell size in meters
        scale_length: Desired scale bar length in meters (auto if None)
    
    Returns:
        Image with scale bar
    """
    from PIL import ImageDraw, ImageFont
    
    w, h = img.size
    draw = ImageDraw.Draw(img)
    
    # Calculate domain size
    domain_size = w * dx  # Total width in meters
    
    # Auto-select a nice scale bar length if not provided
    if scale_length is None:
        # Choose a scale that's roughly 1/5 of the image width
        target_pixels = w / 5
        target_length = target_pixels * dx
        
        # Round to a nice number
        nice_values = [1e-9, 2e-9, 5e-9, 1e-8, 2e-8, 5e-8, 
                       1e-7, 2e-7, 5e-7, 1e-6, 2e-6, 5e-6,
                       1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4,
                       1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2]
        
        scale_length = min(nice_values, key=lambda x: abs(x - target_length))
    
    # Calculate scale bar width in pixels
    scale_pixels = int(scale_length / dx)
    
    # Format the scale label
    if scale_length >= 1e-3:
        label = f"{scale_length * 1e3:.1f} mm"
    elif scale_length >= 1e-6:
        label = f"{scale_length * 1e6:.1f} µm"
    elif scale_length >= 1e-9:
        label = f"{scale_length * 1e9:.1f} nm"
    else:
        label = f"{scale_length:.2e} m"
    
    # Position: bottom-right corner with margin
    margin = 20
    bar_height = 8
    x1 = w - margin - scale_pixels
    y1 = h - margin - bar_height
    x2 = w - margin
    y2 = h - margin
    
    # Draw scale bar (white with black outline)
    draw.rectangle([x1-1, y1-1, x2+1, y2+1], fill=(0, 0, 0))  # Black outline
    draw.rectangle([x1, y1, x2, y2], fill=(255, 255, 255))     # White bar
    
    # Draw label
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = ImageFont.load_default()
    
    # Get text size for centering
    bbox = draw.textbbox((0, 0), label, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = x1 + (scale_pixels - text_width) // 2
    text_y = y1 - 20
    
    # Draw text with outline for visibility
    for offset_x, offset_y in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        draw.text((text_x + offset_x, text_y + offset_y), label, fill=(0, 0, 0), font=font)
    draw.text((text_x, text_y), label, fill=(255, 255, 255), font=font)
    
    return img


def create_gif(sim_output_path: str, output_path: str, 
               species_list: list = None, fps: int = 10,
               colors: dict = None, dx: float = None, scale_length: float = None):
    """
    Create animated GIF from PIConGPU PNG outputs.
    
    Args:
        sim_output_path: Path to simulation output directory
        output_path: Path for output GIF
        species_list: List of species to include (None = all found)
        fps: Frames per second
        colors: Color dictionary (None = use default SPECIES_COLORS)
        dx: Cell size in meters (for scale bar)
        scale_length: Desired scale bar length in meters (auto if None)
    """
    if colors is None:
        colors = SPECIES_COLORS
    
    # Find PNG folders
    png_folders = find_png_folders(sim_output_path)
    
    if not png_folders:
        print(f"Error: No PNG folders found in {sim_output_path}")
        print("Expected folders like 'pngDeuterons', 'pngTritons', etc.")
        return
    
    print(f"Found species: {list(png_folders.keys())}")
    
    # Filter to requested species
    if species_list:
        png_folders = {s: p for s, p in png_folders.items() if s in species_list}
        if not png_folders:
            print(f"Error: None of the requested species {species_list} found")
            return
    
    print(f"Processing species: {list(png_folders.keys())}")
    for species, color in colors.items():
        if species in png_folders:
            print(f"  {species}: RGB{color}")
    
    # Get sorted PNG lists for each species
    png_lists = {species: get_sorted_pngs(folder) 
                 for species, folder in png_folders.items()}
    
    # Check that all species have the same number of frames
    frame_counts = {s: len(pngs) for s, pngs in png_lists.items()}
    print(f"Frame counts: {frame_counts}")
    
    min_frames = min(frame_counts.values())
    if min_frames == 0:
        print("Error: No PNG files found")
        return
    
    # Create combined frames
    print(f"Creating {min_frames} combined frames...")
    frames = []
    
    for i in range(min_frames):
        if i % 10 == 0:
            print(f"  Processing frame {i}/{min_frames}")
        
        frame_paths = {species: png_lists[species][i] 
                       for species in png_folders.keys()}
        
        combined = combine_frames(frame_paths, colors, BACKGROUND_COLOR, dx, scale_length)
        frames.append(combined)
    
    # Save as GIF
    print(f"Saving GIF to {output_path}...")
    duration = int(1000 / fps)  # milliseconds per frame
    
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0  # Loop forever
    )
    
    print(f"Done! Created {output_path}")
    print(f"  Frames: {len(frames)}")
    print(f"  FPS: {fps}")
    print(f"  Duration: {len(frames) / fps:.1f} seconds")


def create_legend(colors: dict, species_list: list, output_path: str):
    """
    Create a legend image showing species colors.
    """
    from PIL import ImageDraw, ImageFont
    
    height = 30 * len(species_list) + 20
    width = 200
    
    img = Image.new('RGB', (width, height), color=BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    y = 10
    for species in species_list:
        color = colors.get(species, (255, 255, 255))
        
        # Draw color box
        draw.rectangle([10, y, 30, y + 20], fill=color)
        
        # Draw species name
        draw.text((40, y), species, fill=(255, 255, 255), font=font)
        
        y += 30
    
    img.save(output_path)
    print(f"Legend saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Combine PIConGPU PNG outputs into animated GIF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --input ./simOutput --output animation.gif
    %(prog)s --input ./simOutput --output animation.gif --fps 15
    %(prog)s --input ./simOutput --output animation.gif --species d t He4
    %(prog)s --input ./simOutput --output animation.gif --dx 6e-7
    %(prog)s --input ./simOutput --output animation.gif --dx 6e-7 --scale 5e-6
    
Default colors:
    d (Deuterons): Blue
    t (Tritons): Red
    He4 (Helium-4): Green
    n (Neutrons): Yellow
    e (Electrons): Magenta
        """
    )
    
    parser.add_argument('--input', '-i', required=True,
                        help='Path to simulation output directory')
    parser.add_argument('--output', '-o', default='combined_animation.gif',
                        help='Output GIF filename (default: combined_animation.gif)')
    parser.add_argument('--species', '-s', nargs='+', default=None,
                        help='Species to include (default: all found)')
    parser.add_argument('--fps', type=int, default=10,
                        help='Frames per second (default: 10)')
    parser.add_argument('--legend', action='store_true',
                        help='Also create a legend image')
    parser.add_argument('--dx', type=float, default=None,
                        help='Cell size in meters for scale bar (e.g., 6e-7 for 0.6 µm)')
    parser.add_argument('--scale', type=float, default=None,
                        help='Scale bar length in meters (auto if not specified)')
    
    args = parser.parse_args()
    
    # Validate input path
    if not os.path.isdir(args.input):
        print(f"Error: Input directory not found: {args.input}")
        return 1
    
    # Print scale info if provided
    if args.dx:
        print(f"Cell size (dx): {args.dx:.2e} m = {args.dx * 1e6:.2f} µm")
        if args.scale:
            print(f"Scale bar length: {args.scale:.2e} m = {args.scale * 1e6:.2f} µm")
    
    # Create GIF
    create_gif(
        sim_output_path=args.input,
        output_path=args.output,
        species_list=args.species,
        fps=args.fps,
        dx=args.dx,
        scale_length=args.scale
    )
    
    # Create legend if requested
    if args.legend:
        legend_path = args.output.replace('.gif', '_legend.png')
        species = args.species or list(find_png_folders(args.input).keys())
        create_legend(SPECIES_COLORS, species, legend_path)
    
    return 0


if __name__ == '__main__':
    exit(main())
