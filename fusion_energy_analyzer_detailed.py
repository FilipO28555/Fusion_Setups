#!/usr/bin/env python3
"""
Enhanced Fusion Energy Analyzer Script

This script provides a comprehensive analysis of fusion reaction energetics:
1) Analyzes initial reactant energies (d and t) in the first steps
2) Analyzes product energies (n and He4) in later steps  
3) Compares theoretical vs observed energy distributions
4) Calculates energy conservation and reaction Q-value

Author: Created for fusion simulation analysis
"""

import os
import sys
import glob
import re
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Fusion reaction constants
# CORRECTED: Q-value is now in keV to match the input data files.
D_T_FUSION_Q_VALUE_KEV = 17590.0  # keV (17.59 MeV)
NEUTRON_MASS = 1.67493e-27    # kg
HE4_MASS = 6.64466e-27        # kg
DEUTERIUM_MASS = 3.34358e-27   # kg
TRITIUM_MASS = 5.00827e-27    # kg

def parse_energy_bin_edges(header_line: str, num_data_columns: int) -> List[float]:
    """
    Robustly parse energy bin edges from the PIConGPU histogram header.
    Includes a workaround for malformed headers where one bin is missing.
    """
    # Find all floating point numbers in the header, including scientific notation
    # This regex properly captures numbers like 1.23e+06 or 1.23e-06
    all_numbers = [float(f) for f in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", header_line)]
    
    # The numbers from the header are the upper edges of the bins.
    # The full set of edges starts at 0.
    bin_edges = [0.0] + all_numbers
    
    # The number of bins is num_data_columns. We need num_data_columns + 1 edges for calculation.
    if len(bin_edges) == num_data_columns + 1:
        # Header is consistent with data. Perfect match.
        pass
    elif len(bin_edges) == num_data_columns:
        # This is the error case. The header is missing the final overflow boundary.
        # We trust the number of data columns and extrapolate the last edge.
        print(f"Warning: Header has one fewer bin boundary than expected for the data. Extrapolating last edge.")
        if len(bin_edges) > 1:
            # Assume the last bin has the same width as the second-to-last.
            last_bin_width = bin_edges[-1] - bin_edges[-2]
            bin_edges.append(bin_edges[-1] + last_bin_width)
        else: # Fallback for a single bin
            bin_edges.append(bin_edges[0] * 1.5 if bin_edges else 1.0)
    else:
        raise ValueError(
            f"Unrecoverable mismatch between number of data columns ({num_data_columns}) "
            f"and parsed boundaries from header ({len(all_numbers)})."
        )
        
    return bin_edges

def read_energy_data(data_file: str) -> Tuple[Optional[pd.DataFrame], Optional[List[float]]]:
    """Read particle energy data from file."""
    try:
        with open(data_file, 'r') as f:
            header = f.readline().strip()
            
        data = pd.read_csv(data_file, sep=r'\s+', comment='#', header=None, engine='python')
        
        # Determine the number of bins from the actual data columns
        num_bins = data.shape[1] - 2 # Subtract timestep and total_count columns
        
        energy_bin_edges = parse_energy_bin_edges(header, num_bins)
        
        column_names = ['timestep'] + [f'bin_{i}' for i in range(num_bins)] + ['total_count']
        data.columns = column_names
        
        return data, energy_bin_edges
        
    except Exception as e:
        print(f"Error reading {data_file}: {e}")
        return None, None

def calculate_mean_energy(
    data_row: pd.Series, 
    energy_bin_edges: List[float], 
    treat_first_bin_as_zero: bool = False
) -> float:
    """
    Calculate the mean energy from a single row of histogram data.
    
    Args:
        data_row: A pandas Series representing one timestep.
        energy_bin_edges: A list of the boundaries for the energy bins.
        treat_first_bin_as_zero: If True and the particle is in the first bin,
                                 return exactly 0.0 keV.
    """
    # Extract the bin counts from the row
    bin_counts = data_row.iloc[1:-1].to_numpy()
    total_count = data_row.iloc[-1]

    if total_count == 0:
        return 0.0

    # The number of bins is determined by the number of bin_count columns.
    num_bins = len(bin_counts)
    
    # For N bins, we need N+1 edges to calculate N bin centers.
    if len(energy_bin_edges) != num_bins + 1:
         raise ValueError(
            f"Logic error: Number of bins ({num_bins}) does not align with "
            f"number of bin edges ({len(energy_bin_edges)}) for center calculation."
        )

    # For single-particle simulations, find the populated bin
    if total_count == 1:
        populated_bin_index = np.argmax(bin_counts > 0)
        
        # Handle the gamma=1 case
        if treat_first_bin_as_zero and populated_bin_index == 0:
            return 0.0
            
        # Calculate the center of that bin
        bin_lower_edge = energy_bin_edges[populated_bin_index]
        bin_upper_edge = energy_bin_edges[populated_bin_index + 1]
        bin_center = (bin_lower_edge + bin_upper_edge) / 2.0
        return bin_center
    else:
        # For statistical distributions, calculate the weighted average
        bin_centers = (np.array(energy_bin_edges[:-1]) + np.array(energy_bin_edges[1:])) / 2.0
        
        # Handle the gamma=1 case for the first bin
        if treat_first_bin_as_zero:
            bin_centers[0] = 0.0
            
        mean_energy = np.sum(bin_counts * bin_centers) / total_count
        return mean_energy

def calculate_theoretical_product_energies(d_energy_kev: float, t_energy_kev: float) -> Tuple[float, float]:
    """
    Calculate theoretical neutron and He4 energies from D-T fusion.
    All energy values are in keV.
    """
    # Total initial energy (kinetic + rest mass) in keV
    total_initial_energy_kev = d_energy_kev + t_energy_kev + D_T_FUSION_Q_VALUE_KEV
    
    # In the center-of-mass frame, products share energy inversely proportional to mass
    total_mass = NEUTRON_MASS + HE4_MASS
    
    # Neutron gets more energy due to lower mass
    neutron_fraction = HE4_MASS / total_mass
    he4_fraction = NEUTRON_MASS / total_mass
    
    theoretical_n_energy_kev = total_initial_energy_kev * neutron_fraction
    theoretical_he4_energy_kev = total_initial_energy_kev * he4_fraction
    
    return theoretical_n_energy_kev, theoretical_he4_energy_kev

def analyze_fusion_energetics_eV(data_files: Dict[str, str]) -> None:
    """
    Comprehensive analysis of fusion reaction energetics.
    """
    print("="*80)
    print("COMPREHENSIVE FUSION ENERGY ANALYSIS")
    print("="*80)
    print()
    
    # Step 1: Analyze initial reactant energies
    print("🔥 STEP 1: INITIAL REACTANT ANALYSIS")
    print("-" * 50)
    
    d_initial_energy = None
    t_initial_energy = None
    
    for species in ['d', 't']:
        if species in data_files:
            data, energy_edges = read_energy_data(data_files[species])
            if data is not None and energy_edges is not None:
                # Look at first few steps
                first_steps = data[data['total_count'] > 0].head(3)

                if not first_steps.empty:
                    for _, row in first_steps.iterrows():
                        timestep = int(row['timestep'])
                        total_count = row['total_count']
                        # For initial reactants, treat the first bin as zero energy (gamma=1 case)
                        mean_energy = calculate_mean_energy(row, energy_edges, treat_first_bin_as_zero=True)

                        print(f"{species.upper()} at step {timestep}: {total_count:.1e} particles, "
                              f"Energy: {mean_energy:,.1f} keV ({mean_energy/1000:.2f} MeV)")
                        
                        # Store initial energies for theoretical calculation
                        if timestep == 0:
                            if species == 'd':
                                d_initial_energy = mean_energy
                            elif species == 't':
                                t_initial_energy = mean_energy
                else:
                    print(f"No {species.upper()} data found in early steps")
    
    print()
    
    # Step 2: Analyze product energies
    print("⚛️  STEP 2: FUSION PRODUCT ANALYSIS")
    print("-" * 50)
    
    product_energies = {}
    
    for species in ['n', 'He4']:
        if species in data_files:
            data, energy_edges = read_energy_data(data_files[species])
            if data is not None and energy_edges is not None:
                # Look at later steps with data
                later_data = data[data['total_count'] > 0]
                
                if not later_data.empty:
                    # Take first few timesteps with product data
                    sample_data = later_data.head(5)

                    energies = []
                    for _, row in sample_data.iterrows():
                        timestep = int(row['timestep'])
                        total_count = row['total_count']
                        # For products, we expect high energy, so do not force the first bin to zero.
                        mean_energy = calculate_mean_energy(row, energy_edges)
                        energies.append(mean_energy)

                        if len(energies) <= 3:  # Show first 3 timesteps
                            print(f"{species.upper()} at step {timestep}: {total_count:.1e} particles, "
                                  f"Energy: {mean_energy:,.1f} keV ({mean_energy/1000:.2f} MeV)")
                    
                    # Store average energy for comparison
                    product_energies[species] = np.mean(energies)
                    
                    total_timesteps = len(later_data)
                    print(f"  → Average {species.upper()} energy over {total_timesteps} timesteps: "
                          f"{product_energies[species]:,.0f} eV ({product_energies[species]/1e6:.2f} MeV)")
                else:
                    print(f"No {species.upper()} data found")
        print()
    
    # Step 3: Theoretical vs Observed Comparison
    print("📊 STEP 3: THEORETICAL VS OBSERVED COMPARISON")
    print("-" * 50)
    
    if d_initial_energy is not None and t_initial_energy is not None:
        print(f"Initial reactant energies:")
        print(f"  Deuterium:  {d_initial_energy:,.0f} eV ({d_initial_energy/1e6:.2f} MeV)")
        print(f"  Tritium:    {t_initial_energy:,.0f} eV ({t_initial_energy/1e6:.2f} MeV)")
        print(f"  Total:      {(d_initial_energy + t_initial_energy):,.0f} eV "
              f"({(d_initial_energy + t_initial_energy)/1e6:.2f} MeV)")
        print()
        
        # Calculate theoretical product energies
        theoretical_n, theoretical_he4 = calculate_theoretical_product_energies(
            d_initial_energy, t_initial_energy)
        
        print(f"Theoretical product energies (with Q = {D_T_FUSION_Q_VALUE/1e6:.2f} MeV):")
        print(f"  Neutron:    {theoretical_n:,.0f} eV ({theoretical_n/1e6:.2f} MeV)")
        print(f"  Helium-4:   {theoretical_he4:,.0f} eV ({theoretical_he4/1e6:.2f} MeV)")
        print(f"  Total:      {(theoretical_n + theoretical_he4):,.0f} eV "
              f"({(theoretical_n + theoretical_he4)/1e6:.2f} MeV)")
        print()
        
        # Compare with observed
        if 'n' in product_energies and 'He4' in product_energies:
            observed_n = product_energies['n']
            observed_he4 = product_energies['He4']
            
            print(f"Observed product energies:")
            print(f"  Neutron:    {observed_n:,.0f} eV ({observed_n/1e6:.2f} MeV)")
            print(f"  Helium-4:   {observed_he4:,.0f} eV ({observed_he4/1e6:.2f} MeV)")
            print(f"  Total:      {(observed_n + observed_he4):,.0f} eV "
                  f"({(observed_n + observed_he4)/1e6:.2f} MeV)")
            print()
            
            # Calculate differences
            n_diff = abs(observed_n - theoretical_n) / theoretical_n * 100
            he4_diff = abs(observed_he4 - theoretical_he4) / theoretical_he4 * 100
            
            print(f"Energy differences (Theory vs Simulation):")
            print(f"  Neutron:    {n_diff:.1f}% difference")
            print(f"  Helium-4:   {he4_diff:.1f}% difference")
            
            # Energy conservation check
            total_initial = d_initial_energy + t_initial_energy + D_T_FUSION_Q_VALUE
            total_final = observed_n + observed_he4
            conservation_error = abs(total_final - total_initial) / total_initial * 100
            
            print(f"  Energy conservation: {conservation_error:.1f}% error")
            
            if conservation_error < 5:
                print("  ✅ Energy is well conserved!")
            elif conservation_error < 15:
                print("  ⚠️  Some energy conservation issues")
            else:
                print("  ❌ Significant energy conservation problems")
    else:
        print("❌ Could not find initial reactant energies for comparison")
    
    print()
    print("="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

def analyze_fusion_energetics(data_files: Dict[str, str]) -> None:
    """
    Comprehensive analysis of fusion reaction energetics.
    Assumes all energy data from files is in keV.
    """
    print("="*80)
    print("COMPREHENSIVE FUSION ENERGY ANALYSIS (Units: keV)")
    print("="*80)
    print()

    # Step 1: Analyze initial reactant energies
    print("🔥 STEP 1: INITIAL REACTANT ANALYSIS")
    print("-" * 50)

    d_initial_energy_kev = None
    t_initial_energy_kev = None

    for species in ['d', 't']:
        if species in data_files:
            data, energy_edges = read_energy_data(data_files[species])
            if data is not None and energy_edges is not None:
                first_steps = data[data['total_count'] > 0].head(3)
                if not first_steps.empty:
                    # Use the first row with particles for initial energy
                    initial_row = first_steps.iloc[0]
                    timestep = int(initial_row['timestep'])
                    total_count = initial_row['total_count']
                    mean_energy_kev = calculate_mean_energy(initial_row, energy_edges)

                    print(f"{species.upper()} at step {timestep}: {total_count:.1e} particles, "
                          f"Energy: {mean_energy_kev:,.1f} keV ({mean_energy_kev/1000:.2f} MeV)")

                    if species == 'd':
                        d_initial_energy_kev = mean_energy_kev
                    elif species == 't':
                        t_initial_energy_kev = mean_energy_kev
                else:
                    print(f"No {species.upper()} data found in early steps")

    print()

    # Step 2: Analyze product energies
    print("⚛️  STEP 2: FUSION PRODUCT ANALYSIS")
    print("-" * 50)

    product_energies_kev = {}

    for species in ['n', 'He4']:
        if species in data_files:
            data, energy_edges = read_energy_data(data_files[species])
            if data is not None and energy_edges is not None:
                later_data = data[data['total_count'] > 0]
                if not later_data.empty:
                    # For single particle simulation, take the first product instance
                    product_row = later_data.iloc[0]
                    timestep = int(product_row['timestep'])
                    total_count = product_row['total_count']
                    mean_energy_kev = calculate_mean_energy(product_row, energy_edges)
                    product_energies_kev[species] = mean_energy_kev

                    print(f"{species.upper()} at step {timestep}: {total_count:.1e} particles, "
                          f"Energy: {mean_energy_kev:,.1f} keV ({mean_energy_kev/1000:.2f} MeV)")
                else:
                    print(f"No {species.upper()} data found")
        print()

    # Step 3: Theoretical vs Observed Comparison
    print("📊 STEP 3: THEORETICAL VS OBSERVED COMPARISON")
    print("-" * 50)

    if d_initial_energy_kev is not None and t_initial_energy_kev is not None:
        print(f"Initial reactant energies:")
        print(f"  Deuterium:  {d_initial_energy_kev:,.1f} keV ({d_initial_energy_kev/1000:.2f} MeV)")
        print(f"  Tritium:    {t_initial_energy_kev:,.1f} keV ({t_initial_energy_kev/1000:.2f} MeV)")
        print(f"  Total:      {(d_initial_energy_kev + t_initial_energy_kev):,.1f} keV "
              f"({(d_initial_energy_kev + t_initial_energy_kev)/1000:.2f} MeV)")
        print()

        theoretical_n, theoretical_he4 = calculate_theoretical_product_energies(
            d_initial_energy_kev, t_initial_energy_kev)

        print(f"Theoretical product energies (with Q = {D_T_FUSION_Q_VALUE_KEV/1000:.2f} MeV):")
        print(f"  Neutron:    {theoretical_n:,.1f} keV ({theoretical_n/1000:.2f} MeV)")
        print(f"  Helium-4:   {theoretical_he4:,.1f} keV ({theoretical_he4/1000:.2f} MeV)")
        print(f"  Total:      {(theoretical_n + theoretical_he4):,.1f} keV "
              f"({(theoretical_n + theoretical_he4)/1000:.2f} MeV)")
        print()

        if 'n' in product_energies_kev and 'He4' in product_energies_kev:
            observed_n = product_energies_kev['n']
            observed_he4 = product_energies_kev['He4']

            print(f"Observed product energies:")
            print(f"  Neutron:    {observed_n:,.1f} keV ({observed_n/1000:.2f} MeV)")
            print(f"  Helium-4:   {observed_he4:,.1f} keV ({observed_he4/1000:.2f} MeV)")
            print(f"  Total:      {(observed_n + observed_he4):,.1f} keV "
                  f"({(observed_n + observed_he4)/1000:.2f} MeV)")
            print()

            n_diff = abs(observed_n - theoretical_n) / theoretical_n * 100
            he4_diff = abs(observed_he4 - theoretical_he4) / theoretical_he4 * 100
            print(f"Energy differences (Theory vs Simulation):")
            print(f"  Neutron:    {n_diff:.1f}% difference")
            print(f"  Helium-4:   {he4_diff:.1f}% difference")

            total_initial = d_initial_energy_kev + t_initial_energy_kev + D_T_FUSION_Q_VALUE_KEV
            total_final = observed_n + observed_he4
            conservation_error = abs(total_final - total_initial) / total_initial * 100
            print(f"  Energy conservation: {conservation_error:.1f}% error")

            if conservation_error < 5:
                print("  ✅ Energy is well conserved!")
            else:
                print("  ❌ Significant energy conservation problems")
    else:
        print("❌ Could not find initial reactant energies for comparison")

    print()
    print("="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

def find_data_files(folder_path: str) -> Dict[str, str]:
    """Find all energy histogram files in the specified folder."""
    file_pattern = os.path.join(folder_path, '*_energyHistogram_all.dat')
    data_files = glob.glob(file_pattern)
    
    species_files = {}
    for file_path in data_files:
        base_name = os.path.basename(file_path)
        species_name = base_name.split('_')[0]
        species_files[species_name] = file_path
    
    return species_files

def main():
    """Main function to run the comprehensive energy analysis."""
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        folder_path = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Analyzing fusion data in: {folder_path}")
    print()
    
    # Find all energy histogram data files
    data_files = find_data_files(folder_path)
    
    if not data_files:
        print(f"❌ No energy histogram files found in {folder_path}")
        print("Looking for files matching pattern: *_energyHistogram_all.dat")
        return
    
    print(f"Found {len(data_files)} species data files:")
    for species, file_path in data_files.items():
        print(f"  📄 {species}: {os.path.basename(file_path)}")
    print()
    
    # Run the comprehensive analysis
    analyze_fusion_energetics(data_files)

if __name__ == '__main__':
    main()
