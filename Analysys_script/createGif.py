import os
import sys
import re
from PIL import Image, ImageOps, ImageChops
from collections import defaultdict

# --- Main Configuration ---

# 1. Define ALL possible particles and their colors in this master dictionary.
#    The script will use this to colorize the particles it finds in each directory.
ALL_PARTICLE_COLORS = {
    'eL': 'cyan',
    'eP1': 'magenta',
    'eP2': 'yellow',
    'eR': 'lime',
    
    'd': 'cyan',
    't': 'magenta',
    'n': 'yellow',
    'He4': 'lime',
}

# 2. GIF Settings
#    Duration for each frame in milliseconds. (1000 // 12 calculates duration for 12 fps).
FRAME_DURATION_MS = 1000 // 12


def tint_image(src_image, color):
    """
    Applies a color tint to an image, treating black as transparent.
    This function preserves the intensity gradient of the original image.

    Args:
        src_image (PIL.Image.Image): The source image.
        color (str): The color to tint the image with.

    Returns:
        PIL.Image.Image: A new RGBA image tinted with the specified color.
    """
    # Convert the source image to grayscale to get its luminance profile.
    grayscale_img = src_image.convert('L')
    # Scale the grayscale values to the range [0, 255]
    max_value = max(grayscale_img.getextrema())
    if max_value > 0:
        grayscale_img = grayscale_img.point(lambda p: int((p / max_value) * 5 * 255))
    
    # Create the tinted version. This maps black to black, and white to the new color.
    # The result is an RGB image.
    tinted_rgb = ImageOps.colorize(grayscale_img, black=(0, 0, 0), white=color)
    
    return tinted_rgb

def create_combined_gif(folder_path, output_filename, tint_map, duration=200):
    """
    Finds, tints, and combines PNG images from a directory into a single animated GIF.

    Args:
        folder_path (str): The path to the directory containing the PNG files.
        output_filename (str): The name of the output GIF file.
        tint_map (dict): A dictionary mapping particle prefixes to color strings.
        duration (int): The duration of each frame in the GIF in milliseconds.
    """
    # 1. Identify files and group by timestep
    files_by_timestep = defaultdict(list)
    try:
        all_files = [f for f in os.listdir(folder_path) if f.endswith('.png')]
    except FileNotFoundError:
        print(f"Error: Directory not found: {folder_path}")
        return

    if not all_files:
        print(f"No PNG files found in: {folder_path}")
        return

    for filename in all_files:
        try:
            # Assumes filename format: 'particle_..._timestep.png'
            parts = filename.split('_')
            timestep = parts[-1].split('.')[0]
            files_by_timestep[timestep].append(filename)
        except IndexError:
            print(f"Warning: Skipping file with unexpected format: {filename}")
            continue

    # 2. Sort timesteps chronologically
    # Sorting numerically, not alphabetically (e.g., '10' comes after '2')
    sorted_timesteps = sorted(files_by_timestep.keys(), key=int)
    
    if not sorted_timesteps:
        print("Could not extract timesteps from filenames.")
        return

    print(f"Found {len(sorted_timesteps)} timesteps.")

    # 3. Process each timestep to create composite frames
    final_frames = []
    first_image_path = os.path.join(folder_path, files_by_timestep[sorted_timesteps[0]][0])
    with Image.open(first_image_path) as img:
        image_size = img.size

    for timestep in sorted_timesteps:
        # Create a blank black canvas for this timestep's frame
        base_canvas = Image.new('RGB', image_size, (0, 0, 0))

        # Layer all images for this timestep
        for filename in sorted(files_by_timestep[timestep]):
            prefix = filename.split('_')[0]
            color = tint_map.get(prefix, 'white')  # Default to white if prefix not in map

            overlay_path = os.path.join(folder_path, filename)
            with Image.open(overlay_path) as original_overlay:
                tinted_layer = tint_image(original_overlay, color)
                # Add the tinted layer to the base canvas
                base_canvas = ImageChops.add(base_canvas, tinted_layer)
        
        # Convert to 'P' mode for GIF optimization and add to our list of frames
        final_frames.append(base_canvas.convert('P', palette=Image.ADAPTIVE))

    # 4. Save the frames as an animated GIF
    # The GIF will be saved in the base directory (e.g., where 'simOutput' is)
    output_path = os.path.join(folder_path, '..', output_filename)

    if final_frames:
        final_frames[0].save(
            output_path,
            save_all=True,
            append_images=final_frames[1:],
            duration=duration,
            loop=0,  # 0 means loop forever
            optimize=True
        )
        print(f"\nSuccessfully created GIF: {output_path}")
    else:
        print("No frames were created. GIF not generated.")

def camel_to_snake(name):
    """Converts a CamelCase string to snake_case."""
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def discover_and_run_jobs(base_directory):
    """
    Scans the 'simOutput' directory to find subdirectories and automatically
    creates and runs a GIF generation job for each one.
    """
    sim_output_path = os.path.join(base_directory, 'simOutput')

    if not os.path.isdir(sim_output_path):
        print(f"Error: 'simOutput' directory not found at '{sim_output_path}'")
        return

    # Find all subdirectories starting with 'png'
    subdirs = [d for d in os.listdir(sim_output_path) if os.path.isdir(os.path.join(sim_output_path, d)) and d.startswith('png')]

    if not subdirs:
        print(f"No 'png*' subdirectories found in '{sim_output_path}'. Nothing to do.")
        return
        
    print(f"Discovered {len(subdirs)} potential job(s): {', '.join(subdirs)}")

    for dir_name in subdirs:
        print("-" * 50)
        
        # --- Infer configuration from directory name ---
        directory_suffix = dir_name[3:] # Remove 'png' prefix
        output_filename = f"{camel_to_snake(directory_suffix)}_colored.gif"
        image_folder = os.path.join(sim_output_path, dir_name)
        
        print(f"Processing job for '{directory_suffix}'...")
        print(f"  -> Input: {image_folder}")
        print(f"  -> Output: {output_filename}")

        # --- Discover particles present in this directory ---
        try:
            all_files = [f for f in os.listdir(image_folder) if f.endswith('.png')]
            # Get unique prefixes from filenames (e.g., 'eL', 'eR')
            found_prefixes = set(f.split('_')[0] for f in all_files)
        except Exception as e:
            print(f"Could not read directory {image_folder}. Skipping. Error: {e}")
            continue

        # Build the color map for this specific job
        particle_map = {prefix: ALL_PARTICLE_COLORS[prefix] for prefix in found_prefixes if prefix in ALL_PARTICLE_COLORS}

        if not particle_map:
            print(f"Warning: No known particles found in {dir_name}. Skipping job.")
            continue
            
        print(f"  -> Found particles: {', '.join(particle_map.keys())}")

        # --- Run the GIF creation process for the current job ---
        create_combined_gif(
            folder_path=image_folder,
            output_filename=output_filename,
            tint_map=particle_map,
            duration=FRAME_DURATION_MS
        )
    
    print("-" * 50)
    print("All jobs completed.")


if __name__ == '__main__':
    # Get the base simulation directory from the first command-line argument
    if len(sys.argv) > 1:
        base_directory = sys.argv[1]
    else:
        # Use the current directory as a fallback
        base_directory = '.'
        print(f"No base directory specified. Using current directory: '{base_directory}'")

    # Discover and run all jobs
    discover_and_run_jobs(base_directory)
