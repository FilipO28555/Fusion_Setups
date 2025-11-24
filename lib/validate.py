#!/usr/bin/env python3
"""
Validation script for PIConGPU fusion CI tests.

This script validates He4 production from D-T fusion simulations by comparing
the simulated particle count against analytical predictions.

This file is part of PIConGPU.
Copyright 2024 PIConGPU contributors
Authors: GitHub Copilot, Filip Optolowicz
License: GPLv3+
"""

import sys
import os
import numpy as np
import scipy.constants as const

# =============================================================================
# Pade Approximation Parameters for D-T Fusion Cross Section S-Factor
# =============================================================================
class PadeParams:
    """
    Holds the coefficients for the Pade approximation of the D-T fusion
    astrophysical S-factor. These parameters are typically valid for
    center-of-mass energies in the ~1-1000 keV range.
    """
    BG = 34.3827      # Gamow factor coefficient
    A1 = 6.927e4
    A2 = 7.454e8
    A3 = 2.050e6
    A4 = 5.2002e4
    A5 = 0.0
    B1 = 6.38e1
    B2 = -9.95e-1
    B3 = 6.981e-5
    B4 = 1.728e-4

# =============================================================================
# Core Fusion Calculation Functions
# =============================================================================

def sigma(E_rel_keV):
    """
    Calculates the D-T fusion cross-section in square meters (m^2).

    Args:
        E_rel_keV (float): The relative kinetic energy in the center-of-mass
                           frame, in units of kilo-electron-volts (keV).

    Returns:
        float: The fusion cross-section in square meters (m^2).
    """
    p = PadeParams
    
    # The Pade approximation for the S-factor S(E)
    s_numerator = p.A1 + E_rel_keV * (p.A2 + E_rel_keV * (p.A3 + E_rel_keV * (p.A4 + E_rel_keV * p.A5)))
    s_denominator = 1.0 + E_rel_keV * (p.B1 + E_rel_keV * (p.B2 + E_rel_keV * (p.B3 + E_rel_keV * p.B4)))
    
    s_factor = s_numerator / s_denominator # Result in keV-barns

    # The Gamow factor for tunneling probability
    gamow_factor = np.exp(-p.BG / np.sqrt(E_rel_keV))

    # Cross-section formula: sigma(E) = S(E)/E * GamowFactor
    # The result is in milibarns. 1 milibarn = 1e-31 m^2
    sigma_barns = (s_factor / E_rel_keV) * gamow_factor

    return sigma_barns * 1e-31 # Convert barns to m^2

def totalRate(n1, n2, sigma_m2, v_rel, vol):
    """Calculates total reactions per second in a given volume."""
    return n1 * n2 * sigma_m2 * v_rel * vol

def calculate_expected_reactions(n_D, n_T, gamma, grid_size, cell_size, delta_t, n_steps):
    """
    Calculate expected He4 production based on analytical fusion rate.
    
    Args:
        n_D: Deuterium density (particles/m^3)
        n_T: Tritium density (particles/m^3)
        gamma: Lorentz factor
        grid_size: Tuple of (nx, ny, nz) grid dimensions
        cell_size: Tuple of (dx, dy, dz) cell dimensions in meters
        delta_t: Timestep in seconds
        n_steps: Number of simulation steps
        
    Returns:
        float: Expected number of He4 particles produced
    """
    # Particle masses
    m_D = const.value('deuteron mass in u')
    m_T = const.value('triton mass in u')
    
    # Calculate relativistic velocity
    beta = np.sqrt(1 - 1/gamma**2)
    v_rel = (2 * beta * const.c) / (1 + beta**2)
    
    # Calculate relative Lorentz factor
    gamma_rel = gamma**2 * (1 + beta**2)
    
    # Calculate reduced mass and relative energy
    mu_u = (m_D * m_T) / (m_D + m_T)
    mu_kg = mu_u * const.u
    E_rel_joules = (gamma_rel - 1) * mu_kg * const.c**2
    E_rel_keV = E_rel_joules / const.e / 1000.0
    
    # Calculate cross-section
    sigma_m2 = sigma(E_rel_keV)
    
    # Calculate total volume
    cell_volume = cell_size[0] * cell_size[1] * cell_size[2]
    total_volume = cell_volume * grid_size[0] * grid_size[1] * grid_size[2]
    
    # Calculate reaction rate
    reactions_per_sec = totalRate(n_D, n_T, sigma_m2, v_rel, total_volume)
    
    # Calculate total reactions over simulation time
    total_time = delta_t * n_steps
    expected_reactions = reactions_per_sec * total_time
    
    return expected_reactions

def read_particle_count(filepath):
    """
    Read the final particle count from a macroParticlesCount.dat file.
    
    Args:
        filepath: Path to the .dat file
        
    Returns:
        float: Final particle count (last timestep)
    """
    try:
        data = np.loadtxt(filepath, comments='#')
        if len(data.shape) == 1:
            # Single row
            return data[1]  # Column 1 is the count
        else:
            # Multiple rows - take the last one
            return data[-1, 1]  # Last row, column 1
    except Exception as e:
        raise RuntimeError(f"Failed to read particle count from {filepath}: {e}")

def validate_simulation(data_path, tolerance=0.20):
    """
    Validate fusion simulation results against analytical predictions.
    
    Args:
        data_path: Path to simulation output directory
        tolerance: Relative tolerance for validation (default 20%)
        
    Returns:
        int: 0 if validation passes, 1 if it fails
    """
    print("=" * 70)
    print("PIConGPU Fusion CI Test Validation")
    print("=" * 70)
    
    # Simulation parameters (matching ci.sh)
    n_D = 1e+31  # Deuterium density (particles/m^3)
    n_T = 1e+31  # Tritium density (particles/m^3)
    gamma = 1.021 # Lorentz factor
    
    grid_size = (24, 24, 24)  # Grid dimensions from ci.sh (-g 24 24 24)
    delta_t = 1e-5  # Timestep in seconds
    delta_x = delta_t * const.c * 2  # Spatial step corresponding to delta_t
    cell_size = (delta_x, delta_x, delta_x)  # Cell size in meters
    n_steps = 200  # Number of steps from ci.sh (-s 200)
    
    print(f"\nSimulation Parameters:")
    print(f"  Grid size: {grid_size[0]} x {grid_size[1]} x {grid_size[2]} cells")
    print(f"  Cell size: {cell_size[0]:.2e} m")
    print(f"  Timesteps: {n_steps}")
    print(f"  Timestep: {delta_t:.2e} s")
    print(f"  Deuterium density: {n_D:.2e} m^-3")
    print(f"  Tritium density: {n_T:.2e} m^-3")
    print(f"  Lorentz factor (gamma): {gamma}")
    print(f"  Tolerance: ±{tolerance*100:.1f}%")
    
    # Calculate expected He4 production
    print(f"\n{'─' * 70}")
    print("Calculating expected He4 production from analytical formula...")
    expected_he4 = calculate_expected_reactions(n_D, n_T, gamma, grid_size, cell_size, delta_t, n_steps)
    print(f"  Expected He4 particles: {expected_he4:.3e}")
    
    # Read actual He4 count from simulation
    he4_file = os.path.join(data_path, "He4_macroParticlesCount.dat")
    print(f"\n{'─' * 70}")
    print(f"Reading simulation results from:")
    print(f"  {he4_file}")
    
    if not os.path.exists(he4_file):
        print(f"\n❌ ERROR: He4 particle count file not found!")
        print(f"   Expected: {he4_file}")
        return 1
    
    try:
        actual_he4 = read_particle_count(he4_file)
        print(f"  Actual He4 particles: {actual_he4:.3e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1
    
    # Calculate relative difference
    if expected_he4 == 0:
        print(f"\n❌ ERROR: Expected He4 count is zero!")
        return 1
    
    rel_diff = abs(actual_he4 - expected_he4) / expected_he4
    percent_diff = rel_diff * 100
    
    print(f"\n{'─' * 70}")
    print("Validation Results:")
    print(f"  Expected: {expected_he4:.6e} He4 particles")
    print(f"  Actual:   {actual_he4:.6e} He4 particles")
    print(f"  Absolute difference: {abs(actual_he4 - expected_he4):.6e}")
    print(f"  Relative difference: {percent_diff:.2f}%")
    print(f"  Tolerance: ±{tolerance*100:.1f}%")
    
    # Check if within tolerance
    print(f"\n{'=' * 70}")
    if rel_diff <= tolerance:
        print(f"✅ VALIDATION PASSED")
        print(f"   He4 production is within {tolerance*100:.1f}% of analytical prediction")
        print(f"   ({percent_diff:.2f}% difference)")
        print("=" * 70)
        return 0
    else:
        print(f"❌ VALIDATION FAILED")
        print(f"   He4 production differs by {percent_diff:.2f}%")
        print(f"   Exceeds tolerance of ±{tolerance*100:.1f}%")
        print("=" * 70)
        return 1

def main():
    """Main entry point for validation script."""
    if len(sys.argv) < 2:
        print("Usage: validate.py <data_path>")
        print("  data_path: Path to directory containing simulation output files")
        sys.exit(1)
    
    data_path = sys.argv[1]
    
    if not os.path.isdir(data_path):
        print(f"Error: '{data_path}' is not a valid directory")
        sys.exit(1)
    
    result = validate_simulation(data_path, tolerance=0.20)
    sys.exit(result)

if __name__ == "__main__":
    main()
