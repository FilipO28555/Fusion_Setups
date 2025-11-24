"""
Copyright 2024-2024 Filip Optolowicz

This file is part of PIConGPU.

PIConGPU is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PIConGPU is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PIConGPU.
If not, see <http://www.gnu.org/licenses/>.
"""

import numpy as np

# Physical constants (since scipy.constants might not be available)
c = 299792458.0  # Speed of light in m/s
e = 1.602176634e-19  # Elementary charge in C
u = 1.66053906660e-27  # Atomic mass unit in kg

def sigma(E_keV):
    """
    Calculate D-T fusion cross-section using Bosch-Hale formula
    
    Args:
        E_keV: Center-of-mass energy in keV
        
    Returns:
        Cross-section in m^2
    """
    # Bosch-Hale parameters for D-T reaction
    A1 = 6.927e4
    A2 = 7.454e8
    A3 = 2.050e6
    A4 = 5.2002e4
    A5 = 0.0
    B_G = 34.3827
    
    # Convert to center-of-mass energy in keV
    E_cm = E_keV
    
    # Calculate sigma in millibarns
    theta = E_cm / (1 - ((A2 + A3*E_cm) / (1 + A4*E_cm)) * np.exp(-B_G / np.sqrt(E_cm)))
    sigma_mb = (A1 + A5*E_cm) / (1 + (theta - A5*E_cm)**2 / E_cm)
    
    # Convert millibarns to m^2 (1 barn = 1e-28 m^2)
    sigma_m2 = sigma_mb * 1e-31
    
    return sigma_m2

def totalRate(n_D, n_T, sigma_m2, v_rel, volume):
    """
    Calculate total reaction rate
    
    Args:
        n_D: Deuteron density (particles/m^3)
        n_T: Triton density (particles/m^3)
        sigma_m2: Cross-section (m^2)
        v_rel: Relative velocity (m/s)
        volume: Total volume (m^3)
        
    Returns:
        Reaction rate (reactions/s)
    """
    return n_D * n_T * sigma_m2 * v_rel * volume

def calculate_fusion_parameters(gamma, ppc, grid_size, steps):
    """
    Calculate fusion simulation parameters
    
    Args:
        gamma: Lorentz factor
        ppc: Particles per cell
        grid_size: Tuple of (nx, ny, nz)
        steps: Number of simulation steps
        
    Returns:
        Dictionary with calculated parameters
    """
    # Physical constants
    cell_size = 1e-6  # 1 micron cells
    delta_t = 1e-15   # 1 femtosecond timestep
    
    # Particle masses (in atomic mass units)
    m_D = 2.0135  # Deuteron
    m_T = 3.01604928  # Triton
    
    # Calculate beta and relative velocity
    beta = np.sqrt(1 - 1/gamma**2)
    v_rel = (2 * beta * c) / (1 + beta**2)
    
    # Calculate relative Lorentz factor
    gamma_rel = gamma**2 * (1 + beta**2)
    
    # Calculate reduced mass
    mu_u = (m_D * m_T) / (m_D + m_T)
    mu_kg = mu_u * u
    
    # Calculate relative kinetic energy in the center-of-mass frame
    E_rel_joules = (gamma_rel - 1) * mu_kg * c**2
    E_rel_keV = E_rel_joules / e / 1000.0
    
    # Calculate volume and densities
    nx, ny, nz = grid_size
    cell_volume = (cell_size)**3
    total_volume = cell_volume * nx * ny * nz
    total_particles = ppc * nx * ny * nz
    n_D = n_T = (total_particles / 2) / total_volume  # Equal D and T densities
    
    return {
        'E_rel_keV': E_rel_keV,
        'v_rel': v_rel,
        'total_volume': total_volume,
        'n_D': n_D,
        'n_T': n_T,
        'total_time': steps * delta_t,
        'gamma_rel': gamma_rel,
        'beta': beta
    }

def predict_he4_production(gamma, ppc, grid_size, steps):
    """
    Predict He4 production for given parameters
    
    Args:
        gamma: Lorentz factor
        ppc: Particles per cell
        grid_size: Tuple of (nx, ny, nz)
        steps: Number of simulation steps
        
    Returns:
        Predicted number of He4 particles
    """
    params = calculate_fusion_parameters(gamma, ppc, grid_size, steps)
    
    # Calculate cross-section
    sigma_m2 = sigma(params['E_rel_keV'])
    
    # Calculate total reaction rate
    total_reactions_per_sec = totalRate(
        params['n_D'], params['n_T'], sigma_m2, 
        params['v_rel'], params['total_volume']
    )
    
    # Calculate reactions in simulation timespan
    predicted_reactions = total_reactions_per_sec * params['total_time']
    
    return predicted_reactions, params
