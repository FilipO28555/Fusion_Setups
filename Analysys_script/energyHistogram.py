import os
import sys
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- Main Configuration ---

# 1. Define ALL possible particles and their colors.
#    This is used for the combined count plot to ensure visual consistency.
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

# 2. Global variable for maximum iteration limit for discrepancy calculation
maxIter = 3500

def parse_energy_bin_edges(header_line):
    """
    Parses the header line of the data file to extract the edges of the energy bins.
    """
    parts = header_line.split()
    
    bin_edges = [0.0]
    bin_boundary_strings = parts[2:-2]
    for s in bin_boundary_strings:
        bin_edges.append(float(s))
        
    last_boundary_str = parts[-2]
    last_boundary = float(re.findall(r"[-+]?\d*\.\d+|\d+", last_boundary_str)[0])
    bin_edges.append(last_boundary)
    
    sorted_edges = sorted(bin_edges)
    
    if len(sorted_edges) > 1:
        # Create a synthetic upper edge for the final open-ended bin for plotting
        final_upper_edge = sorted_edges[-1] * 1.5 
        sorted_edges.append(final_upper_edge)
    
    return sorted_edges

def create_energy_histogram(data_file, species_name, output_dir):
    """
    Reads particle energy data from a file and creates a 2D color plot.
    """
    try:
        with open(data_file, 'r') as f:
            header = f.readline().strip()
            
        data = pd.read_csv(data_file, sep=r'\s+', comment='#', header=None, engine='python')

        energy_bin_edges = parse_energy_bin_edges(header)
        
        num_bins = data.shape[1] - 2
        timesteps = data.iloc[:, 0].values
        counts = data.iloc[:, 1:1+num_bins].values

        if len(timesteps) == 0 or len(energy_bin_edges) < 2:
            print(f"Warning: Not enough data to plot in {os.path.basename(data_file)}. Skipping.")
            return

        if len(timesteps) > 1:
            timestep_edges = np.append(timesteps, timesteps[-1] + np.diff(timesteps)[-1])
        elif len(timesteps) == 1:
            timestep_edges = np.append(timesteps, timesteps[0] + 1)
        else:
            timestep_edges = np.array([])

        fig, ax = plt.subplots(figsize=(12, 8))
        
        c = ax.pcolormesh(timestep_edges, energy_bin_edges, counts.T, cmap='viridis', shading='auto')
        
        fig.colorbar(c, ax=ax, label='Particle Count')
        
        ax.set_title(f'Energy Distribution for {species_name} Over Time', fontsize=16)
        ax.set_xlabel('Time Step', fontsize=12)
        ax.set_ylabel('Energy (log scale)', fontsize=12)
        ax.set_yscale('log')
        
        plt.tight_layout()
        
        output_path = os.path.join(output_dir, f'{species_name}_energy_histogram.png')
        plt.savefig(output_path, dpi=300)
        plt.close(fig)

    except Exception as e:
        print(f"An error occurred while processing {os.path.basename(data_file)} for energy histogram: {e}")

def create_combined_count_plot(data_files, output_dir, color_map):
    """
    Creates a single plot showing the total real particle count for all species.
    """
    print("\nGenerating combined total particle count plot...")
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    all_species_counts = {}

    for data_file in data_files:
        try:
            base_name = os.path.basename(data_file)
            species_name = base_name.split('_')[0]

            data = pd.read_csv(data_file, sep=r'\s+', comment='#', header=None, engine='python')
            
            timesteps = data.iloc[:, 0]
            total_counts = data.iloc[:, -1]
            
            all_species_counts[species_name] = pd.Series(total_counts.values, index=timesteps.values)
            
            plot_color = color_map.get(species_name, None) # Get color from map
            ax.plot(timesteps, total_counts, marker='.', linestyle='-', label=species_name, color=plot_color)
            print(f"  - Added '{species_name}' to the combined plot.")

        except Exception as e:
            print(f"An error occurred while processing {os.path.basename(data_file)} for combined plot: {e}")

    if all_species_counts:
        df_counts = pd.DataFrame(all_species_counts)
        total_running_count = df_counts.fillna(0).sum(axis=1)

        ax.plot(total_running_count.index, total_running_count.values, 
                color='black', linestyle='--', linewidth=2, label='Total')
        
        filtered_total = total_running_count[total_running_count.index <= maxIter]

        if not filtered_total.empty:
            discrepancy = filtered_total.max() - filtered_total.min()
            discrepancy_text = f"Discrepancy (t <= {maxIter}): {discrepancy:.2e}"
        else:
            discrepancy_text = f"No data <= {maxIter} for discrepancy"
        
        ax.text(0.02, 0.85, discrepancy_text, transform=ax.transAxes, fontsize=12,
                verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='wheat', alpha=0.5))

    ax.set_title('Total Real Particle Count for All Species Over Time', fontsize=16)
    ax.set_xlabel('Time Step', fontsize=12)
    ax.set_ylabel('Total Real Particle Count', fontsize=12)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    # set y axes as log scale
    ax.set_yscale('log')
    ax.legend()
    # ax.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    
    plt.tight_layout()
    
    output_path = os.path.join(output_dir, 'all_species_total_counts.png')
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"Combined plot saved to {output_path}")

def create_particle_change_plot(data_files, output_dir):
    """
    Calculates and plots the normalized rate of change of the total particle count.
    """
    print("\nGenerating normalized particle change plot...")
    
    all_species_counts = {}
    for data_file in data_files:
        try:
            base_name = os.path.basename(data_file)
            species_name = base_name.split('_')[0]
            data = pd.read_csv(data_file, sep=r'\s+', comment='#', header=None, engine='python')
            timesteps = data.iloc[:, 0]
            total_counts = data.iloc[:, -1]
            all_species_counts[species_name] = pd.Series(total_counts.values, index=timesteps.values)
        except Exception as e:
            print(f"Could not process {os.path.basename(data_file)} for change plot: {e}")
            continue

    if not all_species_counts:
        print("No data available to generate particle change plot.")
        return

    df_counts = pd.DataFrame(all_species_counts)
    total_running_count = df_counts.fillna(0).sum(axis=1)

    if len(total_running_count) < 2:
        print("Not enough data points to calculate rate of change.")
        return

    initial_total_count = total_running_count.iloc[0]
    if initial_total_count == 0:
        print("Initial total particle count is zero. Cannot normalize.")
        return
    
    # Calculate percentage change from the initial value
    percent_change = ((total_running_count - initial_total_count) / initial_total_count) * 100
    
    filtered_data = percent_change[(percent_change.index >= 0) & (percent_change.index <= maxIter)]

    fig, ax = plt.subplots(figsize=(12, 8))
    
    ax.plot(filtered_data.index, filtered_data.values, marker='.', linestyle='-', 
            label='Normalized Change')
            
    ax.set_title(f'Normalized Change of Total Particle Count (up to t={maxIter})', fontsize=16)
    ax.set_xlabel('Time Step', fontsize=12)
    ax.set_ylabel('Normalized Change (%)', fontsize=12)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax.legend()
    
    ax.set_xlim(left=0, right=maxIter)
    
    plt.tight_layout()
    
    output_path = os.path.join(output_dir, 'normalized_particle_change_percent.png')
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"Normalized change plot saved to {output_path}")


def process_data_folder(folder_path, color_map):
    """
    Finds all energy histogram files and generates all relevant plots.
    """
    output_dir = os.path.join(folder_path, 'plots')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    file_pattern = os.path.join(folder_path, '*_energyHistogram_all.dat')
    data_files = sorted(glob.glob(file_pattern))

    if not data_files:
        print(f"No files found matching the pattern: {file_pattern}")
        return

    print(f"Found {len(data_files)} species files to process:")
    for f in data_files:
        print(f"  -> {os.path.basename(f)}")

    # Part 1: Generate individual energy histograms
    for data_file in data_files:
        base_name = os.path.basename(data_file)
        species_name = base_name.split('_')[0]
        print(f"\nGenerating energy histogram for '{species_name}'...")
        create_energy_histogram(data_file, species_name, output_dir)

    # Part 2: Generate the combined plots
    if data_files:
        create_combined_count_plot(data_files, output_dir, color_map)
        create_particle_change_plot(data_files, output_dir)
            
    print(f"\nProcessing complete. All plots saved in '{output_dir}'")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        base_directory = sys.argv[1]
    else:
        base_directory = '.'
        print(f"No base directory specified. Using current directory: '{base_directory}'")

    sim_output_path = os.path.join(base_directory, 'simOutput')
    
    if not os.path.isdir(sim_output_path):
        print(f"Error: 'simOutput' directory not found at '{sim_output_path}'")
    else:
        process_data_folder(sim_output_path, ALL_PARTICLE_COLORS)
