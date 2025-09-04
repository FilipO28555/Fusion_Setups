#!/usr/bin/env python3
"""
Fusion Rate Analyzer for PIConGPU Deuteron-Triton Simulations

This script analyzes fusion rates in PIConGPU simulations by:
1. Calculating theoretical fusion rates using cross-sections
2. Running simulations with specified parameters
3. Analyzing simulation results to extract actual fusion rates
4. Comparing theoretical and simulation results

Usage:
    python fusion_rate_analyzer.py [--gamma-d GAMMA_D] [--gamma-t GAMMA_T] 
                                   [--density DENSITY] [--timesteps STEPS] 
                                   [--auto-test] [--output-folder FOLDER]
"""

import os
import sys
import re
import subprocess
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import glob
import shutil
from typing import Tuple, Dict, Optional, List
import configparser

# Physical constants
C_LIGHT = 2.99792458e8  # m/s
AMU = 1.66053906660e-27  # kg
ELECTRON_CHARGE = 1.602176634e-19  # C
KEV_TO_JOULE = 1.602176634e-16  # J/keV
MILLI_BARN_TO_M2 = 1e-31  # m^2/millibarn

# Particle masses (in AMU)
DEUTERON_MASS = 2.01410177812
TRITON_MASS = 3.0160492779

class FusionRateAnalyzer:
    def __init__(self, config_file="/home/optolo43/Fusion_Setups/etc/picongpu/1.cfg"):
        self.config_file = config_file
        self.base_dir = "/home/optolo43/Fusion_Setups"
        
        # Physical constants as instance variables
        self.C_LIGHT = C_LIGHT
        self.DEUTERON_MASS = DEUTERON_MASS
        self.TRITON_MASS = TRITON_MASS
        
        # Default simulation parameters
        self.params = {
            'gamma_d': 1.01,
            'gamma_t': 1.01,
            'density': 1e25,  # m^-3
            'timesteps': 2,
            'dt': 0.64e-16,  # s
            'cell_width': 0.16e-6,  # m
            'cell_height': 0.40e-7,  # m
            'cell_depth': 0.16e-6,  # m
            'grid_size': [128, 256, 128]
        }
        
        # Cross-section parameters for D-T fusion (Padé approximation)
        self.cross_section_params = {
            'BG': 34.3827,
            'A1': 6.927e4,
            'A2': 7.454e8,
            'A3': 2.050e6,
            'A4': 5.2002e4,
            'A5': 0.0,
            'B1': 6.38e1,
            'B2': -9.95e-1,
            'B3': 6.981e-5,
            'B4': 1.728e-4
        }
        
        self._load_simulation_parameters()
        self._print_simulation_parameters()
    
    def _load_simulation_parameters(self):
        """Load parameters from simulation configuration files."""
        # Load from simulation.param
        sim_param_file = os.path.join(self.base_dir, "include/picongpu/param/simulation.param")
        if os.path.exists(sim_param_file):
            self._parse_simulation_param(sim_param_file)
            print(f"Loaded density from simulation.param: {self.params['density']:.2e} m⁻³")
        
        # Load gamma values from particle.param
        particle_param_file = os.path.join(self.base_dir, "include/picongpu/param/particle.param")
        if os.path.exists(particle_param_file):
            self._parse_particle_param(particle_param_file)
        
        # Load from config file
        if os.path.exists(self.config_file):
            self._parse_config_file(self.config_file)
    
    def _parse_simulation_param(self, param_file):
        """Parse simulation.param for physical constants."""
        with open(param_file, 'r') as f:
            content = f.read()
        
        # Extract DELTA_T_SI
        dt_match = re.search(r'constexpr float_64 DELTA_T_SI = ([0-9.e+-]+)', content)
        if dt_match:
            self.params['dt'] = float(dt_match.group(1))
        
        # Extract cell dimensions
        cell_width_match = re.search(r'constexpr float_64 CELL_WIDTH_SI = ([0-9.e+-]+)', content)
        if cell_width_match:
            self.params['cell_width'] = float(cell_width_match.group(1))
            
        cell_height_match = re.search(r'constexpr float_64 CELL_HEIGHT_SI = ([0-9.e+-]+)', content)
        if cell_height_match:
            self.params['cell_height'] = float(cell_height_match.group(1))
            
        cell_depth_match = re.search(r'constexpr float_64 CELL_DEPTH_SI = ([0-9.e+-]+)', content)
        if cell_depth_match:
            self.params['cell_depth'] = float(cell_depth_match.group(1))
        
        # Extract base density
        density_match = re.search(r'constexpr float_64 BASE_DENSITY_SI = ([0-9.e+-]+)', content)
        if density_match:
            density_str = density_match.group(1)
            # Handle scientific notation like 1e25
            self.params['density'] = float(density_str)
    
    def _parse_particle_param(self, param_file):
        """Parse particle.param for gamma values and drift directions."""
        with open(param_file, 'r') as f:
            content = f.read()
        
        # Extract gamma values and directions for positive and negative drift
        gamma_pos_match = re.search(r'struct DriftParamPositive\s*{[^}]*static constexpr float_64 gamma = ([0-9.]+)', content, re.DOTALL)
        if gamma_pos_match:
            self.params['gamma_d'] = float(gamma_pos_match.group(1))
        
        gamma_neg_match = re.search(r'struct DriftParamNegative\s*{[^}]*static constexpr float_64 gamma = ([0-9.]+)', content, re.DOTALL)
        if gamma_neg_match:
            self.params['gamma_t'] = float(gamma_neg_match.group(1))
        
        # Extract drift directions
        dir_pos_match = re.search(r'struct DriftParamPositive\s*{[^}]*driftDirection = float3_X\(([^)]+)\)', content, re.DOTALL)
        if dir_pos_match:
            dir_components = [float(x.strip()) for x in dir_pos_match.group(1).split(',')]
            self.params['direction_d'] = dir_components
        
        dir_neg_match = re.search(r'struct DriftParamNegative\s*{[^}]*driftDirection = float3_X\(([^)]+)\)', content, re.DOTALL)
        if dir_neg_match:
            dir_components = [float(x.strip()) for x in dir_neg_match.group(1).split(',')]
            self.params['direction_t'] = dir_components
    
    def _parse_config_file(self, config_file):
        """Parse TBG config file for simulation parameters."""
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Extract timesteps
        steps_match = re.search(r'TBG_steps="([^"]+)"', content)
        if steps_match:
            self.params['timesteps'] = int(steps_match.group(1))
        
        # Extract grid size
        grid_match = re.search(r'TBG_gridSize="([^"]+)"', content)
        if grid_match:
            grid_str = grid_match.group(1).strip()
            self.params['grid_size'] = [int(x) for x in grid_str.split()]
    
    def calculate_relativistic_velocity(self, gamma: float) -> float:
        """Calculate relativistic velocity from Lorentz factor."""
        beta = np.sqrt(1 - 1/gamma**2)
        return beta * self.C_LIGHT
    
    def calculate_direction_dot_product(self, dir1: List[float], dir2: List[float]) -> float:
        """Calculate normalized dot product between two direction vectors."""
        # Normalize vectors
        norm1 = np.sqrt(sum(x**2 for x in dir1))
        norm2 = np.sqrt(sum(x**2 for x in dir2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0  # No direction defined
        
        dir1_norm = [x/norm1 for x in dir1]
        dir2_norm = [x/norm2 for x in dir2]
        
        # Dot product
        dot_product = sum(a*b for a, b in zip(dir1_norm, dir2_norm))
        return dot_product
       
    def calculate_cm_energy(self, gamma_d: float, gamma_t: float, direction_cosine: float = -1.0) -> float:
        """
        Calculate center of mass relative kinetic energy in keV.
        This follows the same method as the PIConGPU C++ implementation.
        
        Args:
            gamma_d: Lorentz factor of deuteron
            gamma_t: Lorentz factor of triton
            direction_cosine: cosine of angle between velocity vectors
                             -1.0 = opposite directions (head-on, maximum energy)
                             +1.0 = same direction (minimum energy)
                              0.0 = perpendicular
        """
        # Convert masses to kg
        mass0 = self.DEUTERON_MASS * AMU  # deuteron
        mass1 = self.TRITON_MASS * AMU    # triton
        
        # Calculate lab energies
        E0_lab = gamma_d * mass0 * self.C_LIGHT**2
        E1_lab = gamma_t * mass1 * self.C_LIGHT**2
        
        # Calculate lab momenta magnitudes
        p0_mag = np.sqrt(E0_lab**2 - (mass0 * self.C_LIGHT**2)**2) / self.C_LIGHT
        p1_mag = np.sqrt(E1_lab**2 - (mass1 * self.C_LIGHT**2)**2) / self.C_LIGHT
        
        # Calculate net momentum based on direction
        # For opposite directions (head-on): p_net = |p0 - p1|
        # For same direction: p_net = |p0 + p1|
        # For general angle: p_net = sqrt(p0² + p1² + 2*p0*p1*cos(θ))
        p_net_sq = p0_mag**2 + p1_mag**2 + 2*p0_mag*p1_mag*direction_cosine
        p_tot_lab = np.sqrt(max(0, p_net_sq))
        
        E_tot_lab = E0_lab + E1_lab
        
        # Invariant mass squared (Mandelstam variable s)
        s = E_tot_lab**2 - (p_tot_lab * self.C_LIGHT)**2
        s = max(s, 0.0)  # guard against numerical errors
        
        # Rest mass energies
        m0c2 = mass0 * self.C_LIGHT**2
        m1c2 = mass1 * self.C_LIGHT**2
        
        # Relative Lorentz factor (Cannoni eq. 42)
        # γ_r = (s - m₀²c⁴ - m₁²c⁴) / (2m₀m₁c⁴)
        gamma_r = (s - m0c2**2 - m1c2**2) / (2.0 * m0c2 * m1c2)
        gamma_r = max(gamma_r, 1.0)  # guard

        # Reduced mass
        mu = (mass0 * mass1) / (mass0 + mass1)
        
        # Relative kinetic energy in CM frame: E_r = μc²(γ_r - 1)
        E_r = mu * self.C_LIGHT**2 * (gamma_r - 1.0)
        
        # Convert to keV
        E_cm_keV = E_r / KEV_TO_JOULE
        
        # 
        
        return E_cm_keV, gamma_r
    
    def calculate_cross_section(self, E_cm_keV: float) -> float:
        """Calculate D-T fusion cross section using Padé approximation."""
        p = self.cross_section_params
        
        # S-factor calculation
        S_numerator = (p['A1'] + E_cm_keV * (p['A2'] + E_cm_keV * (p['A3'] + E_cm_keV * (p['A4'] + E_cm_keV * p['A5']))))
        S_denominator = (1 + E_cm_keV * (p['B1'] + E_cm_keV * (p['B2'] + E_cm_keV * (p['B3'] + E_cm_keV * p['B4']))))
        
        S_E = S_numerator / S_denominator
        
        # Cross section formula: σ = S(E) / (E * exp(BG/√E))
        sigma = S_E / (E_cm_keV * np.exp(p['BG'] / np.sqrt(E_cm_keV)))
        
        return sigma  # in millibarns
    
    def calculate_fusion_rate(self, gamma_d: float, gamma_t: float, density: float, 
                             direction_d: List[float] = None, direction_t: List[float] = None) -> Tuple[float, float, float]:
        """Calculate theoretical fusion rate with direction consideration."""
        
        # Calculate direction cosine if directions are provided
        direction_cosine = -1.0  # Default to head-on collision
        collision_type = "head-on (opposite directions)"
        
        if direction_d is not None and direction_t is not None:
            direction_cosine = self.calculate_direction_dot_product(direction_d, direction_t)
            
            if direction_cosine > 0.9:
                collision_type = "same direction"
            elif direction_cosine < -0.9:
                collision_type = "head-on (opposite directions)"
            else:
                collision_type = f"angled (cos θ = {direction_cosine:.3f})"
        
        # Calculate CM energy with direction
        E_cm, gamma_r = self.calculate_cm_energy(gamma_d, gamma_t, direction_cosine)
        
        # Calculate cross section
        sigma_mb = self.calculate_cross_section(E_cm)
        sigma_m2 = sigma_mb * MILLI_BARN_TO_M2
        
        # Calculate particle velocities
        # For non-relativistic testing use classical velocities derived from gamma ~ 1
        v_d = self.calculate_relativistic_velocity(gamma_d)
        v_t = self.calculate_relativistic_velocity(gamma_t)
        v_rel_gamma_r = self.calculate_relativistic_velocity(gamma_r)
        
        # Non-relativistic relative speed (classical formula):
        # v_rel = sqrt(v_d^2 + v_t^2 - 2*v_d*v_t*cos(theta))
        # This reduces to v_d + v_t for head-on (cosθ = -1) and |v_d - v_t| for same direction (cosθ = +1).
        v_rel_sq = v_d**2 + v_t**2 - 2.0 * v_d * v_t * direction_cosine
        v_rel = np.sqrt(max(0.0, v_rel_sq))
        # print the comparison
        print(f"v_rel (classical) = {v_rel:.3e} m/s, v_rel (from gamma_r) = {v_rel_gamma_r:.3e} m/s")
        v_rel = v_rel_gamma_r  # Use relativistic relative velocity
        
        
        # Fusion reaction rate per unit volume: R = n_D * n_T * <σv>
        # Base density is the density of each species (D and T separately)
        n_d = n_t = density  # Each species has the base density
        sigma_v = sigma_m2 * v_rel
        reaction_rate = n_d * n_t * sigma_v  # reactions per m³ per second
        
        print(f"Direction analysis: {collision_type}")
        print(f"Direction cosine: {direction_cosine:.6f}")
        
        return reaction_rate, E_cm, sigma_mb, v_rel
    
    def calculate_expected_fusions(self, gamma_d: float, gamma_t: float, density: float, 
                                 timesteps: int, dt: float, 
                                 direction_d: List[float] = None, direction_t: List[float] = None) -> Dict:
        """Calculate expected number of fusions in simulation volume.
        Uses kernel-matched invariant flux: sigma * v_rel * gamma_cm.
        """
        # Simulation volume
        volume = (self.params['grid_size'][0] * self.params['cell_width'] *
                 self.params['grid_size'][1] * self.params['cell_height'] *
                 self.params['grid_size'][2] * self.params['cell_depth'])

        # Direction cosine (default head-on)
        dir_cos = -1.0
        if direction_d is not None and direction_t is not None:
            dir_cos = self.calculate_direction_dot_product(direction_d, direction_t)

        # Get E_cm_keV, sigma(E), v_rel from existing helpers
        reaction_rate_tmp, E_cm_keV, sigma_mb, v_rel = self.calculate_fusion_rate(
            gamma_d, gamma_t, density, direction_d, direction_t)
        # Recompute gamma_cm from invariants
        mass0 = DEUTERON_MASS * AMU
        mass1 = TRITON_MASS * AMU
        m0c2 = mass0 * self.C_LIGHT * self.C_LIGHT
        m1c2 = mass1 * self.C_LIGHT * self.C_LIGHT
        E0 = gamma_d * m0c2
        E1 = gamma_t * m1c2
        p0 = max(0.0, (E0*E0 - m0c2*m0c2))**0.5 / self.C_LIGHT
        p1 = max(0.0, (E1*E1 - m1c2*m1c2))**0.5 / self.C_LIGHT
        p_tot_sq = p0*p0 + p1*p1 + 2.0*p0*p1*dir_cos
        p_tot = p_tot_sq**0.5 if p_tot_sq > 0.0 else 0.0
        E_tot = E0 + E1
        s = E_tot*E_tot - (p_tot * self.C_LIGHT) * (p_tot * self.C_LIGHT)
        sqrt_s = s**0.5 if s > 0.0 else 0.0
        gamma_cm = (E_tot / sqrt_s) if sqrt_s > 0.0 else 1.0
        print(f"Recomputed gamma_cm = {gamma_cm:.6f}")

        # Kernel-matched reaction rate per volume: n_d n_t sigma v_rel gamma_cm
        n_d = n_t = density
        sigma_m2 = sigma_mb * MILLI_BARN_TO_M2
        sigma_v = sigma_m2 * v_rel * gamma_cm
        reaction_rate = n_d * n_t * sigma_v

        # Time
        total_time = timesteps * dt
        N_expected = reaction_rate * volume * total_time

        return {
            'reaction_rate': reaction_rate,
            'volume': volume,
            'total_time': total_time,
            'N_expected': N_expected,
            'E_cm_keV': E_cm_keV,
            'sigma_mb': sigma_mb,
            'v_rel': v_rel,
            'gamma_cm': gamma_cm,
            'rate_per_timestep': reaction_rate * volume * dt
        }
    
    def update_simulation_parameters(self, gamma_d: float = None, gamma_t: float = None, 
                                   density: float = None, timesteps: int = None):
        """Update simulation parameters and modify config files."""
        if gamma_d is not None:
            self.params['gamma_d'] = gamma_d
            self._update_particle_param('DriftParamPositive', gamma_d)
        
        if gamma_t is not None:
            self.params['gamma_t'] = gamma_t
            self._update_particle_param('DriftParamNegative', gamma_t)
        
        if density is not None:
            self.params['density'] = density
            self._update_simulation_param('BASE_DENSITY_SI', density)
        
        if timesteps is not None:
            self.params['timesteps'] = timesteps
            self._update_config_param('TBG_steps', timesteps)
    
    def _update_particle_param(self, param_name: str, gamma: float):
        """Update gamma values in particle.param."""
        param_file = os.path.join(self.base_dir, "include/picongpu/param/particle.param")
        
        with open(param_file, 'r') as f:
            content = f.read()
        
        # Update gamma value
        pattern = f'(struct {param_name}\\s*{{[^}}]*static constexpr float_64 gamma = )([0-9.]+)'
        replacement = f'\\g<1>{gamma}'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        with open(param_file, 'w') as f:
            f.write(content)
    
    def _update_simulation_param(self, param_name: str, value: float):
        """Update values in simulation.param."""
        param_file = os.path.join(self.base_dir, "include/picongpu/param/simulation.param")
        
        with open(param_file, 'r') as f:
            content = f.read()
        
        # Update parameter value
        pattern = f'(constexpr float_64 {param_name} = )([0-9.e+-]+)'
        replacement = f'\\g<1>{value:.2e}'
        content = re.sub(pattern, replacement, content)
        
        with open(param_file, 'w') as f:
            f.write(content)
    
    def _update_config_param(self, param_name: str, value):
        """Update values in config file."""
        with open(self.config_file, 'r') as f:
            content = f.read()
        
        # Update parameter value
        pattern = f'({param_name}=")([^"]+)(")'
        replacement = f'\\g<1>{value}\\g<3>'
        content = re.sub(pattern, replacement, content)
        
        with open(self.config_file, 'w') as f:
            f.write(content)
    
    def run_simulation(self, output_folder: str) -> bool:
        """Run the PIConGPU simulation."""
        print(f"Running simulation with output folder: {output_folder}")
        
        # Change to base directory
        original_dir = os.getcwd()
        os.chdir(self.base_dir)
        
        try:
            # Run the simulation
            result = subprocess.run(['/bin/bash', 'run.sh', output_folder], 
                                  capture_output=True, text=True, timeout=7200)  # 2 hour timeout
            
            if result.returncode == 0:
                print("Simulation completed successfully")
                return True
            else:
                print(f"Simulation failed with return code {result.returncode}")
                print(f"Error output: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("Simulation timed out")
            return False
        except Exception as e:
            print(f"Error running simulation: {e}")
            return False
        finally:
            os.chdir(original_dir)
    
    def analyze_simulation_results(self, output_folder: str) -> Dict:
        """Analyze simulation results to extract fusion rates."""
        # Construct path to simulation output - check multiple possible locations
        sim_output_paths = [
            # First try: User home directory (most common for PIConGPU)
            os.path.join(os.path.expanduser('~'), output_folder, 'simOutput'),
            # Second try: Current working directory
            os.path.join(output_folder, 'simOutput'),
            # Third try: Relative to current directory
            os.path.join('.', output_folder, 'simOutput'),
            # Fourth try: Absolute path if already given
            os.path.join(output_folder, 'simOutput') if os.path.isabs(output_folder) else None,
            # Fifth try: Direct path to simOutput if output_folder already contains it
            output_folder if output_folder.endswith('simOutput') else None,
        ]
        
        # Filter out None values
        sim_output_paths = [p for p in sim_output_paths if p is not None]
        
        sim_output_path = None
        for path in sim_output_paths:
            if os.path.exists(path):
                sim_output_path = path
                print(f"Found simulation output at: {path}")
                break
        
        if sim_output_path is None:
            print(f"⚠️  Simulation output not found. Checked paths:")
            for path in sim_output_paths:
                print(f"  ❌ {path}")
            
            # Try to give helpful hints about where output might be
            home_dir = os.path.expanduser('~')
            potential_locations = [
                os.path.join(home_dir, output_folder),
                os.path.join('.', output_folder),
                output_folder
            ]
            
            print(f"\nLooking for directories matching '{output_folder}':")
            for location in potential_locations:
                if os.path.exists(location):
                    print(f"  ✅ Found: {location}")
                    if os.path.isdir(location):
                        try:
                            contents = os.listdir(location)
                            if 'simOutput' in contents:
                                print(f"     📁 Contains simOutput directory!")
                            else:
                                print(f"     📁 Contents: {', '.join(contents[:5])}{'...' if len(contents) > 5 else ''}")
                        except:
                            print(f"     📁 (unable to list contents)")
                else:
                    print(f"  ❌ Not found: {location}")
            
            return {}
        
        results = {}
        
        # Analyze particle counts for each species using energy histograms
        species = ['d', 't', 'n', 'He4']  # deuteron, triton, neutron, helium-4
        
        for species_name in species:
            # Try energy histogram first (gives real particle counts)
            energy_hist_file = os.path.join(sim_output_path, f'{species_name}_energyHistogram_all.dat')
            count_file = os.path.join(sim_output_path, f'{species_name}_macroParticlesCount.dat')
            
            data_source = None
            if os.path.exists(energy_hist_file):
                data_source = energy_hist_file
                data_type = "energy_histogram"
            elif os.path.exists(count_file):
                data_source = count_file
                data_type = "macro_particles"
            
            if data_source:
                try:
                    if data_type == "energy_histogram":
                        # Read energy histogram data
                        data = pd.read_csv(energy_hist_file, sep=r'\s+', comment='#', 
                                         header=None, engine='python')
                        
                        if len(data.columns) >= 2:
                            timesteps = data.iloc[:, 0].values
                            # Last column contains total real particle count
                            real_particle_counts = data.iloc[:, -1].values
                            
                            results[f'{species_name}_timesteps'] = timesteps
                            results[f'{species_name}_counts'] = real_particle_counts
                            results[f'{species_name}_data_type'] = 'real_particles'
                            
                            # Calculate production rate for fusion products
                            if species_name in ['n', 'He4'] and len(real_particle_counts) > 1:
                                # Rate of particle production (particles per timestep)
                                production_rate = np.diff(real_particle_counts)
                                results[f'{species_name}_production_rate'] = production_rate
                                results[f'{species_name}_total_produced'] = real_particle_counts[-1] - real_particle_counts[0]
                                
                                print(f"  Found {species_name} real particles: {real_particle_counts[-1]:.0f} total")
                    
                    else:  # macro_particles
                        # Read macro particle count data (fallback)
                        data = pd.read_csv(count_file, sep=r'\s+', comment='#', 
                                         header=None, engine='python')
                        
                        if len(data.columns) >= 2:
                            timesteps = data.iloc[:, 0].values
                            counts = data.iloc[:, 1].values
                            
                            results[f'{species_name}_timesteps'] = timesteps
                            results[f'{species_name}_counts'] = counts
                            results[f'{species_name}_data_type'] = 'macro_particles'
                            
                            # Calculate production rate for fusion products
                            if species_name in ['n', 'He4'] and len(counts) > 1:
                                # Rate of particle production (particles per timestep)
                                production_rate = np.diff(counts)
                                results[f'{species_name}_production_rate'] = production_rate
                                results[f'{species_name}_total_produced'] = counts[-1] - counts[0]
                                
                                print(f"  Found {species_name} macro particles: {counts[-1]:.0f} total")
                
                except Exception as e:
                    print(f"Error reading {data_source}: {e}")
        
        return results
    
    def compare_rates(self, theoretical: Dict, simulation: Dict) -> Dict:
        """Compare theoretical and simulation fusion rates."""
        comparison = {
            'theoretical_rate_per_timestep': theoretical['rate_per_timestep'],
            'theoretical_total': theoretical['N_expected'],
            'simulation_neutron_produced': simulation.get('n_total_produced', 0),
            'simulation_helium_produced': simulation.get('He4_total_produced', 0),
        }
        
        # Calculate ratios
        if comparison['theoretical_total'] > 0:
            comparison['neutron_ratio'] = comparison['simulation_neutron_produced'] / comparison['theoretical_total']
            comparison['helium_ratio'] = comparison['simulation_helium_produced'] / comparison['theoretical_total']
        else:
            comparison['neutron_ratio'] = 0
            comparison['helium_ratio'] = 0
        
        return comparison
    
    def plot_results(self, theoretical: Dict, simulation: Dict, comparison: Dict, 
                    output_folder: str):
        """Create plots comparing theoretical and simulation results."""
        
        # Ensure output directory exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created output directory: {output_folder}")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Plot 1: Particle counts over time
        ax1 = axes[0, 0]
        species_to_plot = ['d', 't', 'n', 'He4']
        colors = ['cyan', 'magenta', 'yellow', 'lime']
        
        for i, species in enumerate(species_to_plot):
            timesteps_key = f'{species}_timesteps'
            counts_key = f'{species}_counts'
            
            if timesteps_key in simulation and counts_key in simulation:
                ax1.plot(simulation[timesteps_key], simulation[counts_key], 
                        color=colors[i], marker='.', label=species, linewidth=2)
        
        ax1.set_xlabel('Timestep')
        ax1.set_ylabel('Particle Count')
        ax1.set_title('Particle Counts Over Time')
        if any(f'{species}_timesteps' in simulation for species in species_to_plot):
            ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Fusion product production rates
        ax2 = axes[0, 1]
        fusion_products = ['n', 'He4']
        
        for i, species in enumerate(fusion_products):
            rate_key = f'{species}_production_rate'
            if rate_key in simulation:
                timesteps = simulation[f'{species}_timesteps'][1:]  # Skip first timestep
                ax2.plot(timesteps, simulation[rate_key], 
                        color=colors[2+i], marker='o', label=f'{species} production rate')
        
        # Add theoretical prediction
        theoretical_rate = theoretical['rate_per_timestep']
        if len(simulation.get('n_timesteps', [])) > 1:
            ax2.axhline(y=theoretical_rate, color='red', linestyle='--', 
                       label=f'Theoretical rate: {theoretical_rate:.2e}')
        
        ax2.set_xlabel('Timestep')
        ax2.set_ylabel('Particles Produced per Timestep')
        ax2.set_title('Fusion Product Production Rate')
        if any(f'{species}_production_rate' in simulation for species in fusion_products) or 'n_timesteps' in simulation:
            ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Rate comparison
        ax3 = axes[1, 0]
        categories = ['Neutrons', 'Helium-4']
        theoretical_vals = [theoretical['N_expected'], theoretical['N_expected']]
        simulation_vals = [comparison['simulation_neutron_produced'], 
                          comparison['simulation_helium_produced']]
        
        x = np.arange(len(categories))
        width = 0.35
        
        ax3.bar(x - width/2, theoretical_vals, width, label='Theoretical', alpha=0.7)
        ax3.bar(x + width/2, simulation_vals, width, label='Simulation', alpha=0.7)
        
        ax3.set_xlabel('Fusion Products')
        ax3.set_ylabel('Total Count')
        ax3.set_title('Theoretical vs Simulation Fusion Products')
        ax3.set_xticks(x)
        ax3.set_xticklabels(categories)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Summary text
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        summary_text = f"""
        Simulation Parameters:
        γ_deuteron = {self.params['gamma_d']:.3f}
        γ_triton = {self.params['gamma_t']:.3f}
        Density = {self.params['density']:.2e} m⁻³
        Timesteps = {self.params['timesteps']}
        
        Physics:
        CM Energy = {theoretical['E_cm_keV']:.2f} keV
        Cross Section = {theoretical['sigma_mb']:.2e} mb
        
        Results:
        Theoretical Rate = {theoretical['reaction_rate']:.2e} m⁻³s⁻¹
        Expected Fusions = {theoretical['N_expected']:.2e}
        Neutron Ratio = {comparison['neutron_ratio']:.3f}
        Helium Ratio = {comparison['helium_ratio']:.3f}
        """
        
        ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, 
                fontsize=10, verticalalignment='top', fontfamily='monospace')
        
        plt.tight_layout()
        
        # Save plot in current working directory location
        plot_path = os.path.join(output_folder, 'fusion_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"Analysis plot saved to: {plot_path}")
        
        # Also save plot in home directory location if different
        home_plot_path = os.path.join(os.path.expanduser('~'), output_folder, 'fusion_analysis.png')
        if os.path.abspath(plot_path) != os.path.abspath(home_plot_path):
            # Create directory if it doesn't exist
            home_plot_dir = os.path.dirname(home_plot_path)
            if not os.path.exists(home_plot_dir):
                os.makedirs(home_plot_dir)
            plt.savefig(home_plot_path, dpi=300, bbox_inches='tight')
            print(f"Analysis plot also saved to: {home_plot_path}")
        
        plt.close()
    
    def run_full_analysis(self, gamma_d: float = None, gamma_t: float = None, 
                         density: float = None, timesteps: int = None, 
                         output_folder: str = "fusion_test", analyze_only: bool = False) -> Dict:
        """Run complete analysis: update parameters, run simulation, analyze results."""
        
        # Update parameters if provided (unless analyze-only mode)
        if not analyze_only and any(x is not None for x in [gamma_d, gamma_t, density, timesteps]):
            print("Updating simulation parameters...")
            self.update_simulation_parameters(gamma_d, gamma_t, density, timesteps)
        
        # Calculate theoretical predictions
        print("Calculating theoretical fusion rates...")
        
        # Get direction vectors from params if available
        direction_d = self.params.get('direction_d', None)
        direction_t = self.params.get('direction_t', None)
        
        theoretical = self.calculate_expected_fusions(
            self.params['gamma_d'], self.params['gamma_t'], 
            self.params['density'], self.params['timesteps'], self.params['dt'],
            direction_d, direction_t
        )
        
        print(f"Theoretical predictions:")
        print(f"  CM Energy: {theoretical['E_cm_keV']:.2f} keV")
        print(f"  Cross Section: {theoretical['sigma_mb']:.2e} mb")
        print(f"  V_rel: {theoretical['v_rel']:.2e} m/s")
        print(f"  Expected Fusions: {theoretical['N_expected']:.2e}")
        print(f"  Rate per timestep: {theoretical['rate_per_timestep']:.2e}")
        
        # Check if rate is sufficient for observation
        if not analyze_only and theoretical['N_expected'] < 0.1:
            print(f"WARNING: Expected fusion count ({theoretical['N_expected']:.2e}) is very low.")
            print("Consider increasing density, gamma values, or timesteps.")
        
        # Run simulation (skip if analyze-only mode)
        if not analyze_only:
            print("\nRunning PIConGPU simulation...")
            success = self.run_simulation(output_folder)
            
            if not success:
                print("Simulation failed!")
                return {'theoretical': theoretical, 'simulation': {}, 'comparison': {}}
        else:
            print("\nSkipping simulation (analyze-only mode)...")
        
        # Analyze results
        print("\nAnalyzing simulation results...")
        simulation = self.analyze_simulation_results(output_folder)
        
        # Compare results
        comparison = self.compare_rates(theoretical, simulation)
        
        # Create plots
        print("\nGenerating analysis plots...")
        self.plot_results(theoretical, simulation, comparison, output_folder)
        
        # Prepare summary text
        summary_text = f"""{"="*60}
        FUSION ANALYSIS SUMMARY
        {"="*60}
        Theoretical expected fusions: {theoretical['N_expected']:.2e}
        Neutrons produced: {comparison['simulation_neutron_produced']}
        Helium-4 produced: {comparison['simulation_helium_produced']}
        Neutron ratio (sim/theory): {comparison['neutron_ratio']:.3f}
        Helium ratio (sim/theory): {comparison['helium_ratio']:.3f}
        {"="*60}"""
        
        # Print summary
        print("\n" + summary_text)
        
        # Save summary to text file in both locations
        summary_filename = 'fusion_analysis_summary.txt'
        summary_path = os.path.join(output_folder, summary_filename)
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            
        with open(summary_path, 'w') as f:
            f.write(summary_text)
        print(f"Summary saved to: {summary_path}")
        
        # Also save in home directory if different
        home_summary_path = os.path.join(os.path.expanduser('~'), output_folder, summary_filename)
        if os.path.abspath(summary_path) != os.path.abspath(home_summary_path):
            home_summary_dir = os.path.dirname(home_summary_path)
            if not os.path.exists(home_summary_dir):
                os.makedirs(home_summary_dir)
            with open(home_summary_path, 'w') as f:
                f.write(summary_text)
            print(f"Summary also saved to: {home_summary_path}")
        
        return {
            'theoretical': theoretical,
            'simulation': simulation,
            'comparison': comparison
        }
    
    def automated_testing(self, test_cases: list = None):
        """Run automated testing with different parameter combinations."""
        if test_cases is None:
            # Default test cases
            test_cases = [
                {'gamma_d': 1.01, 'gamma_t': 1.01, 'density': 1e25, 'timesteps': 10},
                {'gamma_d': 1.1, 'gamma_t': 1.1, 'density': 1e25, 'timesteps': 10},
                {'gamma_d': 1.5, 'gamma_t': 1.5, 'density': 1e25, 'timesteps': 10},
                {'gamma_d': 1.01, 'gamma_t': 1.01, 'density': 5e25, 'timesteps': 10},
                {'gamma_d': 1.01, 'gamma_t': 1.01, 'density': 1e26, 'timesteps': 10},
            ]
        
        results = []
        
        for i, case in enumerate(test_cases):
            print(f"\n{'='*60}")
            print(f"RUNNING TEST CASE {i+1}/{len(test_cases)}")
            print(f"{'='*60}")
            print(f"Parameters: {case}")
            
            folder_name = f"auto_test_{i+1}"
            result = self.run_full_analysis(
                gamma_d=case['gamma_d'],
                gamma_t=case['gamma_t'], 
                density=case['density'],
                timesteps=case['timesteps'],
                output_folder=folder_name
            )
            
            results.append({
                'case': case,
                'folder': folder_name,
                'result': result
            })
        
        # Generate summary report
        self._generate_test_report(results)
        
        return results
    
    def _generate_test_report(self, results: list):
        """Generate a summary report of all test cases."""
        report_file = "fusion_test_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("FUSION RATE ANALYSIS TEST REPORT\\n")
            f.write("="*60 + "\\n\\n")
            
            for i, test in enumerate(results):
                case = test['case']
                comp = test['result']['comparison']
                theo = test['result']['theoretical']
                
                f.write(f"Test Case {i+1}: {test['folder']}\\n")
                f.write(f"Parameters: γ_d={case['gamma_d']}, γ_t={case['gamma_t']}, "
                       f"ρ={case['density']:.1e}, steps={case['timesteps']}\\n")
                f.write(f"CM Energy: {theo['E_cm_keV']:.2f} keV\\n")
                f.write(f"Cross Section: {theo['sigma_mb']:.2e} mb\\n")
                f.write(f"Expected Fusions: {theo['N_expected']:.2e}\\n")
                f.write(f"Neutron Ratio: {comp['neutron_ratio']:.3f}\\n")
                f.write(f"Helium Ratio: {comp['helium_ratio']:.3f}\\n")
                f.write("-" * 40 + "\\n\\n")
        
        print(f"\nTest report saved to: {report_file}")
    
    def _print_simulation_parameters(self):
        """Print comprehensive simulation parameters at startup."""
        print("=" * 70)
        print("FUSION RATE ANALYZER - SIMULATION PARAMETERS")
        print("=" * 70)
        
        # Physical parameters
        print("📊 Physical Parameters:")
        print(f"  Deuteron Lorentz factor (γ_d): {self.params['gamma_d']:.6f}")
        print(f"  Triton Lorentz factor (γ_t):   {self.params['gamma_t']:.6f}")
        print(f"  Base density (each species):   {self.params['density']:.3e} m⁻³")
        
        # Calculate velocities
        v_d = self.calculate_relativistic_velocity(self.params['gamma_d'])
        v_t = self.calculate_relativistic_velocity(self.params['gamma_t'])
        print(f"  Deuteron velocity:             {v_d:.3e} m/s ({v_d/self.C_LIGHT:.4f}c)")
        print(f"  Triton velocity:               {v_t:.3e} m/s ({v_t/self.C_LIGHT:.4f}c)")
        
        # Calculate CM energy and cross section
        E_cm, gamma_r = self.calculate_cm_energy(self.params['gamma_d'], self.params['gamma_t'])
        V_rel = self.calculate_relativistic_velocity(gamma_r)
        sigma_mb = self.calculate_cross_section(E_cm)
        print(f"  Center-of-mass energy:         {E_cm:.1f} keV")
        print(f"  D-T fusion cross section:      {sigma_mb:.3e} mb")
        
        print()
        
        # Simulation parameters
        print("⚙️  Simulation Parameters:")
        print(f"  Time step (dt):                {self.params['dt']:.3e} s")
        print(f"  Number of timesteps:           {self.params['timesteps']}")
        
        # Calculate simulation volume
        volume = (self.params['grid_size'][0] * self.params['cell_width'] *
                 self.params['grid_size'][1] * self.params['cell_height'] *
                 self.params['grid_size'][2] * self.params['cell_depth'])
        
        # Calculate simulation duration
        total_time = self.params['timesteps'] * self.params['dt']
        
        print(f"  Grid size:                     {self.params['grid_size'][0]} × {self.params['grid_size'][1]} × {self.params['grid_size'][2]} cells")
        print(f"  Cell dimensions:               {self.params['cell_width']:.2e} × {self.params['cell_height']:.2e} × {self.params['cell_depth']:.2e} m")
        print(f"  Simulation volume:             {volume:.3e} m³")
        print(f"  Simulation duration:           {total_time:.3e} s")
        
        print()
        
        # Derived quantities
        print("🔬 Derived Quantities:")
        
        # Particle numbers (each species has the base density)
        n_d = n_t = self.params['density']  # Each species density
        N_d_total = n_d * volume
        N_t_total = n_t * volume
        print(f"  Deuteron density:              {n_d:.3e} m⁻³")
        print(f"  Triton density:                {n_t:.3e} m⁻³")
        print(f"  Total deuterons in volume:     {N_d_total:.3e}")
        print(f"  Total tritons in volume:       {N_t_total:.3e}")
        
        # Fusion rate calculations
        direction_d = self.params.get('direction_d', None)
        direction_t = self.params.get('direction_t', None)
        reaction_rate, _, _, _ = self.calculate_fusion_rate(
            self.params['gamma_d'], self.params['gamma_t'], self.params['density'],
            direction_d, direction_t
        )
        rate_per_timestep = reaction_rate * volume * self.params['dt']
        total_expected = reaction_rate * volume * total_time
        
        print(f"  Fusion reaction rate:          {reaction_rate:.3e} reactions/m³/s")
        print(f"  Expected fusions per timestep: {rate_per_timestep:.3e}")
        print(f"  Total expected fusions:        {total_expected:.3e}")
        
        print()
        
        # Assessment
        if total_expected >= 1.0:
            status = "🟢 EXCELLENT"
            assessment = "High probability of observing fusion events"
        elif total_expected >= 0.1:
            status = "🟡 GOOD"
            assessment = "Moderate probability of observing fusion events"
        elif total_expected >= 0.01:
            status = "🟠 MARGINAL"
            assessment = "Low probability - consider increasing density/timesteps"
        else:
            status = "🔴 POOR"
            assessment = "Very low probability - parameters need optimization"
        
        print(f"📈 Assessment: {status}")
        print(f"   {assessment}")
        
        if total_expected < 0.1:
            print()
            print("💡 Recommendations to improve fusion yield:")
            print("   • Increase density to 5×10²⁵ - 1×10²⁶ m⁻³")
            print("   • Increase timesteps to 100-500")
            print("   • Use python suggest_parameters.py for optimization")
        
        print("=" * 70)
        print()


from fusion_rate_core import total_expected_fusions
def main():
    parser = argparse.ArgumentParser(description='Fusion Rate Analyzer for PIConGPU')
    
    parser.add_argument('--gamma-d', type=float, default=None,
                       help='Deuteron Lorentz factor (default: 1.01)')
    parser.add_argument('--gamma-t', type=float, default=None,
                       help='Triton Lorentz factor (default: 1.01)')
    parser.add_argument('--density', type=float, default=None,
                       help='Particle density in m^-3 (default: 1e25)')
    parser.add_argument('--timesteps', type=int, default=None,
                       help='Number of simulation timesteps (default: 2)')
    parser.add_argument('--output-folder', type=str, default='fusion_analysis',
                       help='Output folder name (default: fusion_analysis)')
    parser.add_argument('--auto-test', action='store_true',
                       help='Run automated testing with multiple parameter sets')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze existing simulation results, skip simulation run')
    parser.add_argument('--config', type=str, default='/home/optolo43/Fusion_Setups/etc/picongpu/1.cfg',
                       help='Path to PIConGPU config file')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = FusionRateAnalyzer(config_file=args.config)
    
    if args.auto_test:
        # Run automated testing
        print("Starting automated testing...")
        analyzer.automated_testing()
    else:
        # Run single analysis
        analyzer.run_full_analysis(
            gamma_d=args.gamma_d,
            gamma_t=args.gamma_t,
            density=args.density,
            timesteps=args.timesteps,
            output_folder=args.output_folder,
            analyze_only=args.analyze_only
        )


if __name__ == "__main__":
    main()
