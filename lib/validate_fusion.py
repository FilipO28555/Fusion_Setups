#!/usr/bin/env python3
"""
Fusion CI Test Validation Script

This script validates the results of a D-T fusion simulation by:
1. Reading the simulation output data
2. Calculating the predicted He4 production using analytical formulas
3. Measuring the actual He4 production from simulation
4. Comparing predicted vs measured with 20% tolerance

Authors: GitHub Copilot, Filip Optolowicz
License: GPLv3+
"""

import sys
import os
import numpy as np

# Try to import h5py, make it optional
try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False
    print("Warning: h5py not available, will try alternative data reading methods")

# Add the lib directory to Python path
sys.path.append(os.path.dirname(__file__))

try:
    from fusion_lib import calculate_fusion_parameters, sigma, predict_he4_production
    # Physical constants (in case scipy is not available)
    c = 299792458.0  # Speed of light in m/s
    e = 1.602176634e-19  # Elementary charge in C
    u = 1.66053906660e-27  # Atomic mass unit in kg
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure scipy and numpy are installed, and ReactionRate.py is available")
    sys.exit(1)

def read_he4_count_from_h5(data_path):
    """
    Read the final He4 particle count from the simulation output
    
    Args:
        data_path: Path to simulation output directory
        
    Returns:
        int: Number of He4 particles at the end of simulation
    """
    # Look for bp (ADIOS2) or h5 files in the data path
    data_files = []
    for file in os.listdir(data_path):
        if file.endswith(('.h5', '.bp')) or 'simData_fusion' in file:
            data_files.append(file)
    
    if not data_files:
        print("No simulation data files found, trying alternative methods...")
        # Try alternative approach - count particles from macroParticlesCount plugin
        return read_he4_count_alternative(data_path)
    
    # Sort files to get the final timestep
    h5_files.sort()
    final_file = os.path.join(data_path, h5_files[-1])
    
    print(f"Reading He4 count from: {final_file}")
    
    if not HAS_H5PY:
        print("Warning: h5py not available, cannot read HDF5 files directly")
        # Try alternative approach - count particles from macroParticlesCount plugin
        return read_he4_count_alternative(data_path)
    
    try:
        with h5py.File(final_file, 'r') as f:
            # Check available iterations
            iterations = list(f['data'].keys())
            final_iteration = max([int(it) for it in iterations])
            iteration_key = str(final_iteration)
            
            print(f"Final iteration: {final_iteration}")
            
            # Read He4 particle data
            if 'particles' in f[f'data/{iteration_key}']:
                particles = f[f'data/{iteration_key}/particles']
                
                if 'He4' in particles:
                    he4_group = particles['He4']
                    
                    # Count total He4 particles
                    if 'weighting' in he4_group:
                        weighting_group = he4_group['weighting']
                        if hasattr(weighting_group, 'keys'):
                            # For openPMD format with species data
                            weights = weighting_group[list(weighting_group.keys())[0]][:]
                            total_he4 = np.sum(weights)
                        else:
                            # Direct array access
                            weights = weighting_group[:]
                            total_he4 = np.sum(weights)
                    else:
                        # Count particles directly if no weighting
                        if 'position' in he4_group:
                            pos_data = he4_group['position']
                            if 'x' in pos_data:
                                total_he4 = len(pos_data['x'][:])
                            else:
                                total_he4 = len(list(pos_data.keys()))
                        else:
                            total_he4 = 0
                else:
                    print("Warning: He4 species not found in particles data")
                    total_he4 = 0
            else:
                print("Warning: No particles data found in file")
                total_he4 = 0
                
    except Exception as e:
        print(f"Error reading h5 file: {e}")
        # Try alternative approach - count particles from macroParticlesCount plugin
        return read_he4_count_alternative(data_path)
    
    print(f"Total He4 particles found: {total_he4}")
    return int(total_he4)

def read_he4_count_alternative(data_path):
    """
    Alternative method to read He4 count from macroParticlesCount output
    """
    print("Looking for He4 macroParticlesCount files...")
    
    # List all files in data path
    all_files = os.listdir(data_path)
    print(f"Available files: {all_files}")
    
    try:
        # Look for He4 particle count files
        he4_files = [f for f in all_files if 'He4' in f and 'macroParticlesCount' in f and f.endswith('.dat')]
        
        if he4_files:
            file_path = os.path.join(data_path, he4_files[0])
            print(f"Reading He4 count from: {file_path}")
            
            # Read the data file
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
            # Parse the last line for final count
            if lines:
                last_line = lines[-1].strip()
                # Typically format: timestep count
                parts = last_line.split()
                if len(parts) >= 2:
                    final_count = float(parts[-1])
                    print(f"He4 count from macroParticlesCount: {final_count}")
                    return int(final_count)
        
        # If no He4 files found, look for any particle count files as backup
        count_files = [f for f in all_files if 'macroParticlesCount' in f and f.endswith('.dat')]
        if count_files:
            print(f"Found particle count files: {count_files}")
            print("Note: No He4 particles detected in simulation output")
            return 0
        else:
            print("No macroParticlesCount files found")
            return 0
            
    except Exception as e:
        print(f"Error reading particle count files: {e}")
        return 0

def calculate_predicted_he4():
    """
    Calculate predicted He4 production using the analytical formulas
    
    Returns:
        float: Predicted number of He4 particles
    """
    # Simulation parameters (hardcoded for CI test)
    gamma = 1.5  # Lorentz factor
    ppc = 20     # particles per cell
    grid_size = (128, 128, 128)  # From 1.cfg
    steps = 200  # From 1.cfg
    
    # Use fusion_lib to calculate prediction
    predicted_he4, params = predict_he4_production(gamma, ppc, grid_size, steps)
    
    print(f"Simulation parameters:")
    print(f"  Gamma: {gamma}")
    print(f"  PPC: {ppc}")
    print(f"  Grid: {grid_size[0]}x{grid_size[1]}x{grid_size[2]}")
    print(f"  Steps: {steps}")
    print(f"  Relative energy (CM): {params['E_rel_keV']:.3e} keV")
    print(f"  Cross-section: {sigma(params['E_rel_keV']):.3e} m^2")
    print(f"  Particle densities: {params['n_D']:.3e} particles/m^3")
    print(f"  Total simulation time: {params['total_time']:.3e} s")
    print(f"  Predicted He4 production: {predicted_he4:.3e}")
    
    return predicted_he4

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_fusion.py <data_path>")
        sys.exit(1)
    
    data_path = sys.argv[1]
    
    if not os.path.exists(data_path):
        print(f"Error: Data path '{data_path}' does not exist")
        sys.exit(1)
    
    print("=" * 50)
    print("Fusion CI Test Validation")
    print("=" * 50)
    
    try:
        # Calculate predicted He4 production
        predicted_he4 = calculate_predicted_he4()
        
        print("\n" + "-" * 50)
        print("Reading simulation results...")
        
        # Read actual He4 production from simulation
        measured_he4 = read_he4_count_from_h5(data_path)
        
        print(f"\nResults comparison:")
        print(f"  Predicted He4: {predicted_he4:.3e}")
        print(f"  Measured He4:  {measured_he4}")
        
        # Calculate relative error
        if predicted_he4 > 0:
            relative_error = abs(measured_he4 - predicted_he4) / predicted_he4
            error_percent = relative_error * 100
        else:
            print("Warning: Predicted He4 is zero, cannot calculate relative error")
            relative_error = float('inf')
            error_percent = float('inf')
        
        print(f"  Relative error: {error_percent:.2f}%")
        
        # Check if within 20% tolerance
        tolerance = 0.20  # 20%
        
        if relative_error <= tolerance:
            print(f"\n✅ PASS: Error {error_percent:.2f}% is within {tolerance*100}% tolerance")
            sys.exit(0)
        else:
            print(f"\n❌ FAIL: Error {error_percent:.2f}% exceeds {tolerance*100}% tolerance")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nError during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
