#!/usr/bin/env python3
"""
Particle Energy Calculator for Fusion Simulations

This tool calculates the relativistic energies of deuterium and tritium particles
at different Lorentz factors (gamma values) for PIConGPU fusion simulations.

Usage:
    python particle_energy_calculator.py [gamma_value]
    
If no gamma value is provided, it will use gamma = 10 as default.
"""

import sys
import argparse

# Physical constants
C_LIGHT = 2.99792458e8  # speed of light in m/s (exact)
J_TO_EV = 6.24150907446e18  # conversion factor from Joules to eV

# Particle masses in kg (CODATA 2018 values)
DEUTERIUM_MASS = 3.3435837724e-27  # kg
TRITIUM_MASS = 5.0082635e-27       # kg (approximate, tritium is unstable)

# Rest energies in MeV (commonly used values)
DEUTERIUM_REST_ENERGY_MEV = 1875.612762  # MeV
TRITIUM_REST_ENERGY_MEV = 2808.391482    # MeV

def calculate_particle_energy(rest_mass_kg, gamma):
    """
    Calculate relativistic energies for a particle.
    
    Args:
        rest_mass_kg: Rest mass of the particle in kg
        gamma: Lorentz factor
        
    Returns:
        dict: Dictionary containing rest, kinetic, and total energies in various units
    """
    # Rest energy
    rest_energy_J = rest_mass_kg * C_LIGHT**2
    rest_energy_eV = rest_energy_J * J_TO_EV
    rest_energy_keV = rest_energy_eV / 1e3
    rest_energy_MeV = rest_energy_eV / 1e6
    
    # Total energy
    total_energy_J = gamma * rest_energy_J
    total_energy_eV = total_energy_J * J_TO_EV
    total_energy_keV = total_energy_eV / 1e3
    total_energy_MeV = total_energy_eV / 1e6
    
    # Kinetic energy
    kinetic_energy_J = (gamma - 1) * rest_energy_J
    kinetic_energy_eV = kinetic_energy_J * J_TO_EV
    kinetic_energy_keV = kinetic_energy_eV / 1e3
    kinetic_energy_MeV = kinetic_energy_eV / 1e6
    
    return {
        'rest': {'J': rest_energy_J, 'eV': rest_energy_eV, 'keV': rest_energy_keV, 'MeV': rest_energy_MeV},
        'kinetic': {'J': kinetic_energy_J, 'eV': kinetic_energy_eV, 'keV': kinetic_energy_keV, 'MeV': kinetic_energy_MeV},
        'total': {'J': total_energy_J, 'eV': total_energy_eV, 'keV': total_energy_keV, 'MeV': total_energy_MeV}
    }

def calculate_velocity(gamma):
    """Calculate particle velocity from Lorentz factor."""
    beta = (1 - 1/gamma**2)**0.5
    velocity = beta * C_LIGHT
    return velocity, beta

def print_particle_info(particle_name, mass_kg, gamma):
    """Print detailed energy information for a particle."""
    energies = calculate_particle_energy(mass_kg, gamma)
    velocity, beta = calculate_velocity(gamma)
    
    print(f"\n=== {particle_name.upper()} AT GAMMA = {gamma} ===")
    print(f"Velocity:       {velocity/C_LIGHT:.6f}c ({beta:.6f})")
    print(f"Rest energy:    {energies['rest']['MeV']:>10.3f} MeV ({energies['rest']['keV']:>12,.0f} keV)")
    print(f"Kinetic energy: {energies['kinetic']['MeV']:>10.3f} MeV ({energies['kinetic']['keV']:>12,.0f} keV)")
    print(f"Total energy:   {energies['total']['MeV']:>10.3f} MeV ({energies['total']['keV']:>12,.0f} keV)")

def main():
    parser = argparse.ArgumentParser(description='Calculate particle energies at relativistic speeds')
    parser.add_argument('gamma', type=float, nargs='?', default=10.0,
                        help='Lorentz factor (default: 10.0)')
    parser.add_argument('--range', nargs=3, type=float, metavar=('start', 'stop', 'step'),
                        help='Calculate for a range of gamma values: start stop step')
    
    args = parser.parse_args()
    
    if args.range:
        gamma_start, gamma_stop, gamma_step = args.range
        gamma_values = []
        gamma = gamma_start
        while gamma <= gamma_stop:
            gamma_values.append(gamma)
            gamma += gamma_step
    else:
        gamma_values = [args.gamma]
    
    print("="*70)
    print("PARTICLE ENERGY CALCULATOR FOR FUSION SIMULATIONS")
    print("="*70)
    
    for gamma in gamma_values:
        if gamma < 1.0:
            print(f"\nError: Gamma must be >= 1.0 (given: {gamma})")
            continue
            
        print_particle_info("Deuterium", DEUTERIUM_MASS, gamma)
        print_particle_info("Tritium", TRITIUM_MASS, gamma)
        
        # Combined system
        d_energies = calculate_particle_energy(DEUTERIUM_MASS, gamma)
        t_energies = calculate_particle_energy(TRITIUM_MASS, gamma)
        
        total_kinetic = d_energies['kinetic']['MeV'] + t_energies['kinetic']['MeV']
        total_rest = d_energies['rest']['MeV'] + t_energies['rest']['MeV']
        total_system = d_energies['total']['MeV'] + t_energies['total']['MeV']
        
        print(f"\n=== COMBINED D+T SYSTEM ===")
        print(f"Total rest energy:    {total_rest:>10.3f} MeV")
        print(f"Total kinetic energy: {total_kinetic:>10.3f} MeV")
        print(f"Total system energy:  {total_system:>10.3f} MeV")
        
        # Fusion Q-value context
        Q_VALUE_MEV = 17.59  # D-T fusion Q-value
        print(f"\nD-T Fusion Q-value:   {Q_VALUE_MEV:>10.3f} MeV")
        print(f"Kinetic/Q ratio:      {total_kinetic/Q_VALUE_MEV:>10.1f}x")
        
        if len(gamma_values) > 1:
            print("\n" + "-"*70)

if __name__ == "__main__":
    main()
