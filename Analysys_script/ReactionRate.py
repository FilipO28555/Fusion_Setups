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

    The cross-section is derived from the astrophysical S-factor, which is
    approximated using a Pade polynomial.

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

def reactionRate(n1, n2, sigma_m2, v_rel):
    """Calculates reaction rate density (reactions per m^3 per second)."""
    return n1 * n2 * sigma_m2 * v_rel

def totalRate(n1, n2, sigma_m2, v_rel, vol):
    """Calculates total reactions per second in a given volume."""
    return n1 * n2 * sigma_m2 * v_rel * vol

# =============================================================================
# Main Simulation Function
# =============================================================================

def main():
    """
    Main function to set up parameters and calculate fusion reactions.
    """
    print("--- D-T Fusion Rate Simulation ---")

    # --- 1. Define Simulation and Particle Parameters ---
    n_D = 1e28  # Deuterium density (particles/m^3)
    n_T = 1e28  # Tritium density (particles/m^3)
    gamma = 1.1 # Lorentz factor for both clouds
    
    # Particle masses
    m_D = const.value('deuteron mass in u') # Unified atomic mass units
    m_T = const.value('triton mass in u')
    
    # Simulation geometry
    CELL_WIDTH = 6e-6   # meters
    CELL_HEIGHT = 6e-6  # meters
    CELL_DEPTH = 6e-6   # meters
    GRID_X, GRID_Y, GRID_Z = 128, 128, 128
    
    # Simulation time
    DELTA_T = 1e-16 # Timestep in seconds

    # --- 2. Relativistic Kinematics Calculation ---
    # Calculate velocity of particles from gamma
    beta = np.sqrt(1 - 1/gamma**2)
    
    # Calculate relativistic relative velocity for head-on collision
    v_rel = (2 * beta * const.c) / (1 + beta**2)
    
    # Calculate the relative Lorentz factor
    gamma_rel = gamma**2 * (1 + beta**2) # Equivalent to 2*gamma**2 - 1
    
    # Calculate reduced mass
    mu_u = (m_D * m_T) / (m_D + m_T)
    mu_kg = mu_u * const.u
    
    # Calculate relative kinetic energy in the center-of-mass frame
    E_rel_joules = (gamma_rel - 1) * mu_kg * const.c**2
    
    # Convert energy to keV for the sigma function
    E_rel_keV = E_rel_joules / const.e / 1000.0

    print(f"Relativistic relative velocity: {v_rel/const.c:.3f} c ({v_rel:.3e} m/s)")
    print(f"Relative kinetic energy (CM): {E_rel_keV:.3e} keV")
    print("-" * 35)

    # --- 3. Cross-Section and Volume Calculation ---
    
    # CRITICAL WARNING for the user
    print("⚠️  WARNING: The calculated relative energy is extremely high.")
    print("   The Pade approximation for the cross-section is being used")
    print("   far outside its valid physical range (~1-1000 keV).")
    print("   The following results are a numerical calculation based on the")
    print("   provided formula but are NOT physically realistic.")
    print("-" * 35)
    
    sigma_m2 = sigma(E_rel_keV)
    
    # Calculate total simulation volume
    cell_volume = CELL_WIDTH * CELL_HEIGHT * CELL_DEPTH
    total_volume = cell_volume * GRID_X * GRID_Y * GRID_Z

    print(f"Calculated cross-section: {sigma_m2 / 1e-31:.5f} milibarns ({sigma_m2:.3e} m^2)")
    print(f"Total simulation volume: {total_volume:.3e} m^3")

    # --- 4. Final Reaction Calculation ---
    # Calculate the total reaction rate (reactions/sec) in the volume
    total_reactions_per_sec = totalRate(n_D, n_T, sigma_m2, v_rel, total_volume)

    # Calculate the number of reactions in a single timestep
    reactions_in_timestep = total_reactions_per_sec * DELTA_T * 200

    print("-" * 35)
    print(f"Total reactions per second: {total_reactions_per_sec:.3e}")
    print(f"✅ Number of reactions in 200 timesteps ({DELTA_T} s): {reactions_in_timestep:.3e}")
    

if __name__ == "__main__":
    main()