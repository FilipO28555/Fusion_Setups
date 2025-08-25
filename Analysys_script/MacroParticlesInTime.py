import os
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt

# --- Main Configuration ---

# 1. Define ALL possible particles and their colors in this master dictionary.
#    This should be kept consistent with your GIF generator script.
ALL_PARTICLE_COLORS = {
    'eL': 'cyan',
    'eP1': 'magenta',
    'eP2': 'yellow',
    'eR': 'lime',

    'd': 'red',
    't': 'orange',
    'n': 'blue',
    'He4': 'violet',
}

# 2. Plot Settings
OUTPUT_PLOT_FILENAME = 'macro_particles_count_plot.png'


def plot_particle_counts(data_folder, output_folder, color_map):
    """
    Finds all '*_macroParticlesCount.dat' files in a directory, reads the
    time step and particle count, and plots them on a single graph.

    Args:
        data_folder (str): The path to the directory containing the .dat files.
        output_folder (str): The path to the directory where the plot will be saved.
        color_map (dict): A dictionary mapping particle names to colors.
    """
    # --- 1. Find all the relevant data files ---
    file_pattern = os.path.join(data_folder, '*_macroParticlesCount.dat')
    file_list = glob.glob(file_pattern)

    if not file_list:
        print(f"Error: No files found matching the pattern in '{data_folder}'")
        return

    print(f"Found files: {', '.join(os.path.basename(f) for f in file_list)}")

    # --- 2. Create a plot ---
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 8))

    # --- 3. Loop through each file, read data, and plot ---
    # This variable changes marker size for each plotted line, for better visibility
    marker_size = 7
    for filename in sorted(file_list):
        try:
            # Read the data using pandas
            data = pd.read_csv(
                filename,
                sep=r'\s+',
                comment='#',
                header=None,
                names=['step', 'count', 'energy'],
                engine='python'
            )

            # Extract a clean name for the legend from the filename.
            # e.g., 'eL_macroParticlesCount.dat' -> 'eL'
            species_name = os.path.basename(filename).split('_')[0]

            # Get the color for the species, defaulting to gray if not found
            plot_color = color_map.get(species_name, 'gray')

            # Plot the 'step' column vs the 'count' column
            ax.plot(
                data['step'],
                data['count'],
                label=species_name,
                color=plot_color,
                marker='o',
                linestyle='-',
                markersize=marker_size
            )
            marker_size -= 1 # Decrement marker size for the next line

        except Exception as e:
            print(f"Could not process file {os.path.basename(filename)}: {e}")

    # --- 4. Customize and save the plot ---
    ax.set_title('Particle Count vs. Time Step for Different Species', fontsize=16)
    ax.set_xlabel('Time Step', fontsize=12)
    ax.set_ylabel('Particle Count', fontsize=12)
    ax.legend(title='Species')
    ax.ticklabel_format(style='sci', axis='y', scilimits=(0, 0)) # Use scientific notation
    ax.grid(True)

    plt.tight_layout() # Adjust layout to prevent labels from overlapping
    
    output_path = os.path.join(output_folder, OUTPUT_PLOT_FILENAME)
    plt.savefig(output_path, dpi=300)
    print(f"\nSuccessfully created plot: {output_path}")
    plt.close(fig) # Close the figure to free up memory


if __name__ == '__main__':
    # Get the base simulation directory from the first command-line argument
    if len(sys.argv) > 1:
        base_directory = sys.argv[1]
    else:
        # Use the current directory as a fallback
        base_directory = '.'
        print(f"No base directory specified. Using current directory: '{base_directory}'")

    # Define the path where the data files are located
    sim_output_path = os.path.join(base_directory, 'simOutput')
    
    if not os.path.isdir(sim_output_path):
        print(f"Error: 'simOutput' directory not found at '{sim_output_path}'")
    else:
        print(f"Processing data in: {sim_output_path}")
        # The plot will be saved in the 'simOutput' directory
        plot_particle_counts(
            data_folder=sim_output_path,
            output_folder=sim_output_path,
            color_map=ALL_PARTICLE_COLORS
        )
