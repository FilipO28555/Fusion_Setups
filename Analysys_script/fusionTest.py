"""
Standalone fusion test validator.
Reads PIConGPU simulation output and compares measured He4 count to analytical prediction.
Returns 1 if within 20% tolerance, 0 otherwise.
"""
import os
import sys
import re
import numpy as np
import pandas as pd
import scipy.constants as const

# Ensure we can import sibling analysis helpers
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from ReactionRate import sigma as sigma_dt
except Exception as e:
    print(f"Failed to import ReactionRate.sigma: {e}")
    sys.exit(1)

# Default grid and steps (can be overridden)
DEFAULT_GRID = (128, 128, 128)
DEFAULT_STEPS = 200

# Tolerance for validation (20%)
TOLERANCE = 0.20


def parse_cfg_grid_steps(cfg_path: str):
    """Parse grid size and steps from PIConGPU config file."""
    grid = DEFAULT_GRID
    steps = DEFAULT_STEPS
    if not os.path.isfile(cfg_path):
        return grid, steps
    try:
        with open(cfg_path, "r") as f:
            txt = f.read()
        m_grid = re.search(r"TBG_gridSize\s*=\s*\"(\d+)\s+(\d+)\s+(\d+)\"", txt)
        if m_grid:
            grid = tuple(int(x) for x in m_grid.groups())
        m_steps = re.search(r"TBG_steps\s*=\s*\"(\d+)\"", txt)
        if m_steps:
            steps = int(m_steps.group(1))
    except Exception:
        pass
    return grid, steps


def parse_sim_params_from_file(path: str):
    """Extract simulation parameters from simulation.param file."""
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, "r") as f:
        txt = f.read()
    
    def grab_float(name):
        m = re.search(rf"{name}[^=]*=\s*([0-9eE\.+\-]+)\s*;", txt)
        return float(m.group(1)) if m else None
    
    def grab_int(name):
        m = re.search(rf"{name}[^=]*=\s*(\d+)\s*;", txt)
        return int(m.group(1)) if m else None
    
    out["DELTA_T_SI"] = grab_float("DELTA_T_SI")
    out["CELL_WIDTH_SI"] = grab_float("CELL_WIDTH_SI")
    out["CELL_HEIGHT_SI"] = grab_float("CELL_HEIGHT_SI")
    out["CELL_DEPTH_SI"] = grab_float("CELL_DEPTH_SI")
    
    # Choose first occurrence of BASE_DENSITY_SI
    m = re.search(r"BASE_DENSITY_SI[^=]*=\s*([0-9eE\.+\-]+)\s*;", txt)
    out["BASE_DENSITY_SI"] = float(m.group(1)) if m else None
    
    # Choose first occurrence of TYPICAL_PARTICLES_PER_CELL
    m2 = re.search(r"TYPICAL_PARTICLES_PER_CELL[^=]*=\s*(\d+)\s*;", txt)
    out["TYPICAL_PARTICLES_PER_CELL"] = int(m2.group(1)) if m2 else None
    
    return out


def parse_particle_gamma_from_file(path: str):
    """Extract gamma parameter from particle.param file."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        txt = f.read()
    # Prefer Positive (both should be equal)
    m = re.search(r"DriftParamPositive[\s\S]*?gamma\s*=\s*([0-9eE\.+\-]+)\s*;", txt)
    if m:
        return float(m.group(1))
    m = re.search(r"DriftParamNegative[\s\S]*?gamma\s*=\s*([0-9eE\.+\-]+)\s*;", txt)
    if m:
        return float(m.group(1))
    return None


def compute_relative_velocity_and_energy_keV(gamma: float):
    """
    Calculate relative velocity and energy for head-on deuterium-tritium beams.
    This follows the exact same calculation as ReactionRate.py.
    """
    # Calculate velocity of particles from gamma (matches ReactionRate.py line 96)
    beta = np.sqrt(1 - 1/gamma**2)
    
    # Calculate relativistic relative velocity for head-on collision (matches ReactionRate.py line 99)
    v_rel = (2 * beta * const.c) / (1 + beta**2)
    
    # Calculate the relative Lorentz factor (matches ReactionRate.py line 102)
    gamma_rel = gamma**2 * (1 + beta**2)  # Equivalent to 2*gamma**2 - 1
    
    # Calculate reduced mass (matches ReactionRate.py lines 104-106)
    m_D = const.value('deuteron mass in u')  # Unified atomic mass units
    m_T = const.value('triton mass in u')
    mu_u = (m_D * m_T) / (m_D + m_T)
    mu_kg = mu_u * const.u
    
    # Calculate relative kinetic energy in the center-of-mass frame (matches ReactionRate.py line 109)
    E_rel_joules = (gamma_rel - 1) * mu_kg * const.c**2
    
    # Convert energy to keV for the sigma function (matches ReactionRate.py line 112)
    E_rel_keV = E_rel_joules / const.e / 1000.0
    
    return v_rel, E_rel_keV


def predict_total_events(gamma: float, base_density: float, cell_w: float, cell_h: float, 
                         cell_d: float, grid: tuple, dt: float, steps: int):
    """Calculate analytical prediction for total fusion events."""
    v_rel, E_rel_keV = compute_relative_velocity_and_energy_keV(gamma)
    
    # Cross-section in m^2
    sigma_m2 = float(sigma_dt(E_rel_keV))
    
    # Total volume
    total_volume = (cell_w * cell_h * cell_d) * (grid[0] * grid[1] * grid[2])
    
    # D and T densities equal to base density
    n_D = base_density
    n_T = base_density
    
    # Reactions per second in volume
    reactions_per_sec = n_D * n_T * sigma_m2 * v_rel * total_volume
    
    total_time = dt * steps
    total_events = reactions_per_sec * total_time
    
    return total_events, {
        "v_rel": v_rel,
        "E_rel_keV": E_rel_keV,
        "sigma_m2": sigma_m2,
        "volume": total_volume,
        "time": total_time,
    }


def read_he4_final_count(simOutput_path: str):
    """Read final He4 count from energy histogram file."""
    path = os.path.join(simOutput_path, "He4_energyHistogram_all.dat")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"He4_energyHistogram_all.dat not found in {path}")
    
    df = pd.read_csv(path, sep=r"\s+", comment="#", header=None, engine="python")
    final_total = float(df.iloc[-1, -1])
    return final_total


def validate_fusion_output(run_folder: str, cfg_path: str = None):
    """
    Validate fusion simulation output against analytical prediction.
    
    Args:
        run_folder: Path to simulation run folder (contains input/ and simOutput/)
        cfg_path: Optional path to config file (for grid/steps). If None, uses defaults.
    
    Returns:
        1 if measured He4 count is within 20% of prediction, 0 otherwise.
    """
    # Parse grid and steps from config if provided
    if cfg_path and os.path.isfile(cfg_path):
        grid, steps = parse_cfg_grid_steps(cfg_path)
    else:
        grid, steps = DEFAULT_GRID, DEFAULT_STEPS
    
    # Find parameter files in run folder
    sim_candidates = [
        os.path.join(run_folder, "input", "include", "picongpu", "param", "simulation.param"),
        os.path.join(run_folder, "include", "picongpu", "param", "simulation.param"),
    ]
    part_candidates = [
        os.path.join(run_folder, "input", "include", "picongpu", "param", "particle.param"),
        os.path.join(run_folder, "include", "picongpu", "param", "particle.param"),
    ]
    
    # Parse parameters
    params = {}
    gamma = None
    
    for p in sim_candidates:
        if os.path.isfile(p):
            params = parse_sim_params_from_file(p)
            break
    
    for p in part_candidates:
        if os.path.isfile(p):
            gamma = parse_particle_gamma_from_file(p)
            break
    
    # Validate we have all required parameters
    required_params = ["DELTA_T_SI", "CELL_WIDTH_SI", "CELL_HEIGHT_SI", 
                       "CELL_DEPTH_SI", "BASE_DENSITY_SI"]
    missing = [p for p in required_params if not params.get(p)]
    if missing or gamma is None:
        print(f"Error: Missing required parameters: {missing + (['gamma'] if gamma is None else [])}")
        return 0
    
    
    # print all parsed parameters for debugging
    print("Parsed simulation parameters:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    print(f"  gamma: {gamma}")
    print(f"  grid: {grid}")
    print(f"  steps: {steps}")
    
    # Calculate analytical prediction
    predicted_events, details = predict_total_events(
        gamma,
        params["BASE_DENSITY_SI"],
        params["CELL_WIDTH_SI"],
        params["CELL_HEIGHT_SI"],
        params["CELL_DEPTH_SI"],
        grid,
        params["DELTA_T_SI"],
        steps,
    )
    
    # Read measured He4 count
    simOutput_path = os.path.join(run_folder, "simOutput")
    try:
        measured_he4 = read_he4_final_count(simOutput_path)
    except FileNotFoundError as e:
        print(f"Error reading He4 data: {e}")
        return 0
    
    # Calculate relative error
    if predicted_events > 0:
        rel_error = abs(measured_he4 - predicted_events) / predicted_events
    else:
        print("Error: Predicted events is zero or negative")
        return 0
    
    # Print diagnostic information
    print(f"Analytical prediction: {predicted_events:.3e} events")
    print(f"Measured He4 count:    {measured_he4:.3e}")
    print(f"Relative error:        {rel_error:.2%}")
    print(f"Tolerance:             {TOLERANCE:.2%}")
    print(f"Parameters: gamma={gamma:.6f}, E_rel={details['E_rel_keV']:.2f} keV, "
          f"sigma={details['sigma_m2']:.3e} m^2")
    
    # Return 1 if within tolerance, 0 otherwise
    if rel_error <= TOLERANCE:
        print("✓ PASS: Result within tolerance")
        return 1
    else:
        print("✗ FAIL: Result outside tolerance")
        return 0


def main():
    """Command-line interface for standalone testing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate PIConGPU fusion simulation output against analytical prediction."
    )
    parser.add_argument(
        "run_folder",
        help="Path to simulation run folder (containing input/ and simOutput/)"
    )
    parser.add_argument(
        "--cfg",
        default=None,
        help="Path to PIConGPU config file (for grid/steps). If not provided, uses defaults."
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.20,
        help="Relative tolerance for validation (default: 0.20 = 20%%)"
    )
    
    args = parser.parse_args()
    
    # Update global tolerance if specified
    global TOLERANCE
    TOLERANCE = args.tolerance
    
    # Validate the run folder exists
    if not os.path.isdir(args.run_folder):
        print(f"Error: Run folder not found: {args.run_folder}")
        sys.exit(1)
    
    # Run validation
    result = validate_fusion_output(args.run_folder, args.cfg)
    
    # Exit with appropriate code
    sys.exit(0 if result == 1 else 1)


if __name__ == "__main__":
    main()
