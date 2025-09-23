#!/usr/bin/env python3
import os
import re
import sys
import json
import time
import math
import shutil
import random
import getpass
import subprocess
from datetime import datetime
import csv

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.constants as const

# Ensure we can import sibling analysis helpers
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from ReactionRate import sigma as sigma_dt
except Exception as e:
    print(f"Failed to import ReactionRate.sigma: {e}")
    raise

# Paths
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))  # /home/.../Fusion_Setups
RUN_SH = os.path.join(ROOT, "run.sh")
PARAM_DIR = os.path.join(ROOT, "include", "picongpu", "param")
PARTICLE_PARAM = os.path.join(PARAM_DIR, "particle.param")
SIMULATION_PARAM = os.path.join(PARAM_DIR, "simulation.param")
CFG_DIR = os.path.join(ROOT, "etc", "picongpu")
CFG_FILE = os.path.join(CFG_DIR, "1.cfg")
RESULTS_DIR = os.path.expanduser("~/Fusion_Setups/Results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Defaults from config (parsed when needed)
DEFAULT_GRID = (128, 128, 128)
DEFAULT_STEPS = 200

# Parameter ranges
GAMMA_MIN = 1.0001
GAMMA_MAX = 20.0
DT_MIN = 1e-18
DT_MAX = 1e-15
CELL_MIN = 1e-7
CELL_MAX = 1e-5
DENSITY_MIN = 1e26
DENSITY_MAX = 1e30
PPC_MIN = 1
PPC_MAX = 13

MIN_EVENTS_TARGET = 1e7

# Default CSV schema used when creating a new results file
RESULT_SCHEMA = [
    "timestamp",
    "tag",
    "sample_index",
    "folder",
    "gamma",
    "dt",
    "cell_w",
    "cell_h",
    "cell_d",
    "base_density",
    "ppc",
    "grid_x",
    "grid_y",
    "grid_z",
    "steps",
    "predicted_events",
    "predicted_events_ran",
    "measured_He4_final",
    "E_rel_keV",
    "v_rel",
    "sigma_m2",
    "volume",
    "total_time",
    "he4_file",
]

# -----------------------------
# Utility: parse cfg for grid/steps
# -----------------------------

def parse_cfg_grid_steps(cfg_path: str):
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

# -----------------------------
# Editing helpers for param files
# -----------------------------

def replace_in_file(path: str, pattern: str, repl: str, flags=re.MULTILINE):
    with open(path, "r") as f:
        content = f.read()
    new_content, n = re.subn(pattern, repl, content, flags=flags)
    if n == 0:
        raise RuntimeError(f"Pattern not found for replacement in {path}: {pattern}")
    with open(path, "w") as f:
        f.write(new_content)
    return n

def set_particle_gamma(gamma_val: float):
    # DriftParamNegative.gamma
    replace_in_file(
        PARTICLE_PARAM,
        r"(struct\s+DriftParamNegative[\s\S]*?static\s+constexpr\s+float_64\s+gamma\s*=\s*)([0-9eE\.+\-]+)(\s*;)",
        rf"\g<1>{gamma_val:.8f}\g<3>",
        flags=re.MULTILINE | re.DOTALL,
    )
    # DriftParamPositive.gamma
    replace_in_file(
        PARTICLE_PARAM,
        r"(struct\s+DriftParamPositive[\s\S]*?static\s+constexpr\s+float_64\s+gamma\s*=\s*)([0-9eE\.+\-]+)(\s*;)",
        rf"\g<1>{gamma_val:.8f}\g<3>",
        flags=re.MULTILINE | re.DOTALL,
    )


def set_simulation_params(delta_t: float, cell_w: float, cell_h: float, cell_d: float, base_density: float, ppc: int):
    # Time step and cell sizes
    replace_in_file(
        SIMULATION_PARAM,
        r"(constexpr\s+float_64\s+DELTA_T_SI\s*=\s*)([0-9eE\.+\-]+)(\s*;)",
        rf"\g<1>{delta_t:.6e}\g<3>",
    )
    replace_in_file(
        SIMULATION_PARAM,
        r"(constexpr\s+float_64\s+CELL_WIDTH_SI\s*=\s*)([0-9eE\.+\-]+)(\s*;)",
        rf"\g<1>{cell_w:.6e}\g<3>",
    )
    replace_in_file(
        SIMULATION_PARAM,
        r"(constexpr\s+float_64\s+CELL_HEIGHT_SI\s*=\s*)([0-9eE\.+\-]+)(\s*;)",
        rf"\g<1>{cell_h:.6e}\g<3>",
    )
    replace_in_file(
        SIMULATION_PARAM,
        r"(constexpr\s+float_64\s+CELL_DEPTH_SI\s*=\s*)([0-9eE\.+\-]+)(\s*;)",
        rf"\g<1>{cell_d:.6e}\g<3>",
    )
    # Base density: set both branches (#ifdef and #else)
    replace_in_file(
        SIMULATION_PARAM,
        r"(constexpr\s+float_64\s+BASE_DENSITY_SI\s*=\s*)([0-9eE\.+\-]+)(\s*;)",
        rf"\g<1>{base_density:.6e}\g<3>",
    )
    # Typical particles per cell: set both branches
    replace_in_file(
        SIMULATION_PARAM,
        r"(constexpr\s+uint32_t\s+TYPICAL_PARTICLES_PER_CELL\s*=\s*)(\d+)(\s*;)",
        rf"\g<1>{int(ppc)}\g<3>",
    )

# -----------------------------
# Parsing params from destination folder
# -----------------------------

def parse_sim_params_from_file(path: str):
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
    # choose first occurrence (either branch)
    m = re.search(r"BASE_DENSITY_SI[^=]*=\s*([0-9eE\.+\-]+)\s*;", txt)
    out["BASE_DENSITY_SI"] = float(m.group(1)) if m else None
    m2 = re.search(r"TYPICAL_PARTICLES_PER_CELL[^=]*=\s*(\d+)\s*;", txt)
    out["TYPICAL_PARTICLES_PER_CELL"] = int(m2.group(1)) if m2 else None
    return out


def parse_particle_gamma_from_file(path: str):
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

# -----------------------------
# Physics helpers
# -----------------------------

def compute_relative_velocity_and_energy_keV(gamma: float):
    beta = math.sqrt(1.0 - 1.0 / (gamma * gamma))
    # Relativistic relative velocity for head-on beams with same |beta|
    v_rel = (2.0 * beta * const.c) / (1.0 + beta * beta)
    gamma_rel = gamma * gamma * (1.0 + beta * beta)
    # deuteron and triton masses in unified atomic mass units (u)
    m_D_u = const.value('deuteron mass in u')
    m_T_u = const.value('triton mass in u')
    mu_u = (m_D_u * m_T_u) / (m_D_u + m_T_u)
    mu_kg = mu_u * const.u
    E_rel_J = (gamma_rel - 1.0) * mu_kg * const.c * const.c
    E_rel_keV = E_rel_J / const.e / 1000.0
    return v_rel, E_rel_keV


def predict_total_events(gamma: float, base_density: float, cell_w: float, cell_h: float, cell_d: float, grid: tuple, dt: float, steps: int):
    v_rel, E_rel_keV = compute_relative_velocity_and_energy_keV(gamma)
    # Cross-section in m^2
    sigma_m2 = float(sigma_dt(E_rel_keV))
    # Volume
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

# -----------------------------
# Sampling helpers
# -----------------------------

def log_uniform(a: float, b: float):
    # sample log-uniform in [a, b]
    return 10 ** np.random.uniform(np.log10(a), np.log10(b))


def sample_parameters_until_threshold(grid, steps, min_events=MIN_EVENTS_TARGET, max_tries=200):
    best = None
    best_events = -1.0
    for i in range(max_tries):
        # gamma: sample (gamma-1) log-uniform in [1e-4, 1]
        gminus1 = log_uniform(1e-4, 1.0)
        gamma = min(max(1.0 + gminus1, GAMMA_MIN), GAMMA_MAX)
        # dt and cell sizes log-uniform
        dt = log_uniform(DT_MIN, DT_MAX)
        cell_w = log_uniform(CELL_MIN, CELL_MAX)
        cell_h = log_uniform(CELL_MIN, CELL_MAX)
        cell_d = log_uniform(CELL_MIN, CELL_MAX)
        base_density = log_uniform(DENSITY_MIN, DENSITY_MAX)
        ppc = int(np.random.randint(PPC_MIN, PPC_MAX + 1))
        events, details = predict_total_events(gamma, base_density, cell_w, cell_h, cell_d, grid, dt, steps)
        if events > best_events:
            best_events = events
            best = {
                "gamma": gamma,
                "dt": dt,
                "cell_w": cell_w,
                "cell_h": cell_h,
                "cell_d": cell_d,
                "base_density": base_density,
                "ppc": ppc,
                "predicted_events": events,
            }
        if events >= min_events:
            return best, details
    return best, details

# -----------------------------
# Run orchestration
# -----------------------------

def run_simulation(folder_name: str, reuse_build: bool = False):
    """Execute run.sh with optional -r to reuse existing build. Use login shell for Spack hooks.
    Ensures run.sh is executable; if not, chmod +x and invoke via 'bash run.sh'.
    """
    # Ensure run.sh exists and is executable; if not, adjust permissions
    if not os.path.isfile(RUN_SH):
        raise FileNotFoundError(f"run.sh not found at {RUN_SH}")
    if not os.access(RUN_SH, os.X_OK):
        try:
            os.chmod(RUN_SH, 0o755)
        except Exception as e:
            print(f"Warning: could not chmod +x run.sh ({e}). Will call via 'bash run.sh'.")
    flag = " -r" if reuse_build else ""
    # Call via bash explicitly to avoid exec bit issues
    cmd = f"bash -lc 'bash ./run.sh {folder_name}{flag}'"
    print(f"Running: {cmd}")
    proc = subprocess.run(cmd, shell=True, cwd=ROOT)
    if proc.returncode != 0:
        raise RuntimeError(f"Simulation run.sh failed with code {proc.returncode}")


def get_run_folder(folder_name: str):
    project = os.environ.get("PROJECT")
    if not project:
        project = os.path.expanduser("~/..")
    user = os.environ.get("USER") or getpass.getuser()
    return os.path.join(project, user, folder_name)


def read_he4_final_count(run_folder: str):
    # Expect: <run_folder>/simOutput/He4_energyHistogram_all.dat
    path = os.path.join(run_folder, "simOutput", "He4_energyHistogram_all.dat")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"He4_energyHistogram_all.dat not found in {path}")
    df = pd.read_csv(path, sep=r"\s+", comment="#", header=None, engine="python")
    final_total = float(df.iloc[-1, -1])
    return final_total, path


def parse_params_from_destination_or_source(run_folder: str):
    # Try from destination folder (TBG layout): <run>/input/include/picongpu/param/*.param
    sim_candidates = [
        os.path.join(run_folder, "input", "include", "picongpu", "param", "simulation.param"),
        os.path.join(run_folder, "include", "picongpu", "param", "simulation.param"),
    ]
    part_candidates = [
        os.path.join(run_folder, "input", "include", "picongpu", "param", "particle.param"),
        os.path.join(run_folder, "include", "picongpu", "param", "particle.param"),
    ]

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

    # Fallback to source files if missing
    if not params.get("DELTA_T_SI"):
        params.update(parse_sim_params_from_file(SIMULATION_PARAM))
    if gamma is None:
        gamma = parse_particle_gamma_from_file(PARTICLE_PARAM)
    params["gamma"] = gamma
    return params

# -----------------------------
# PPC sweep executor
# -----------------------------

def run_ppc_sweep(base_samples: int, ppc_min: int, ppc_max: int, grid, steps, tag: str, min_events: float, results_csv: str, no_plot: bool):
    """Sample base parameter sets (meeting min_events) and for each run PPC in [ppc_min, ppc_max].
    Note: Changing TYPICAL_PARTICLES_PER_CELL requires recompilation, so we always recompile per run.
    """
    for sidx in range(1, base_samples + 1):
        print(f"\n=== Sampling base parameters set {sidx}/{base_samples} ===")
        sample, _details = sample_parameters_until_threshold(grid, steps, min_events=min_events)
        if sample is None:
            raise RuntimeError("Failed to sample parameters")
        print(
            f"Base set {sidx} chosen (predicted_events={sample['predicted_events']:.3e}):\n"
            f"  gamma={sample['gamma']:.6f}, dt={sample['dt']:.3e}s\n"
            f"  cell=({sample['cell_w']:.3e}, {sample['cell_h']:.3e}, {sample['cell_d']:.3e}) m\n"
            f"  base_density={sample['base_density']:.3e} 1/m^3"
        )

        # Sweep PPC values (compile each run)
        for ppc in range(int(ppc_min), int(ppc_max) + 1):
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"{tag or 'ppcsweep'}_s{sidx}_ppc{ppc}_{stamp}"
            print(f"\n--- Running base set {sidx}, PPC={ppc} -> {folder_name} ---")

            # Apply params for this run (only PPC varies)
            set_particle_gamma(float(sample['gamma']))
            set_simulation_params(
                delta_t=float(sample['dt']),
                cell_w=float(sample['cell_w']),
                cell_h=float(sample['cell_h']),
                cell_d=float(sample['cell_d']),
                base_density=float(sample['base_density']),
                ppc=int(ppc),
            )

            # Read-back from source files and compute prediction for CSV consistency
            # (Use the sampled parameters directly)
            events_pred_src, details_src = predict_total_events(
                sample['gamma'],
                sample['base_density'],
                sample['cell_w'],
                sample['cell_h'],
                sample['cell_d'],
                grid,
                sample['dt'],
                steps,
            )

            # Run simulation: always compile (no -r) since PPC/params changed
            run_simulation(folder_name, reuse_build=False)

            # Read destination params and results
            run_folder = get_run_folder(folder_name)
            dest_params = parse_params_from_destination_or_source(run_folder)
            he4_count, he4_path = read_he4_final_count(run_folder)

            row = {
                "timestamp": stamp,
                "tag": tag or "ppcsweep",
                "sample_index": sidx,
                "folder": folder_name,
                "gamma": float(dest_params["gamma"]),
                "dt": float(dest_params["DELTA_T_SI"]),
                "cell_w": float(dest_params["CELL_WIDTH_SI"]),
                "cell_h": float(dest_params["CELL_HEIGHT_SI"]),
                "cell_d": float(dest_params["CELL_DEPTH_SI"]),
                "base_density": float(dest_params["BASE_DENSITY_SI"]),
                "ppc": int(ppc),
                "grid_x": int(grid[0]),
                "grid_y": int(grid[1]),
                "grid_z": int(grid[2]),
                "steps": int(steps),
                "predicted_events": float(events_pred_src),
                "measured_He4_final": float(he4_count),
                "E_rel_keV": float(details_src["E_rel_keV"]),
                "v_rel": float(details_src["v_rel"]),
                "sigma_m2": float(details_src["sigma_m2"]),
                "volume": float(details_src["volume"]),
                "total_time": float(details_src["time"]),
                "he4_file": he4_path,
            }
            append_results_csv(row, results_csv)
            print(f"Run saved. Measured He4={he4_count:.3e}. CSV updated: {results_csv}")

            if not no_plot:
                out_png = os.path.join(RESULTS_DIR, "predicted_vs_measured_by_ppc.png")
                plot_results_by_ppc(results_csv, out_png)
                print(f"Summary plot saved to {out_png}")

# -----------------------------
# Main CLI
# -----------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Automated PIConGPU fusion tests: randomize params, run, and compare to analytic prediction.")
    parser.add_argument("--runs", type=int, default=1, help="Number of simulations to perform (repeat sampling each time)")
    parser.add_argument("--min-events", type=float, default=MIN_EVENTS_TARGET, help="Minimum predicted events threshold before running a sampled set")
    parser.add_argument("--tag", type=str, default="auto", help="Folder name prefix for runs")
    parser.add_argument("--sleep", type=float, default=2.0, help="Sleep seconds after run before reading outputs (safety margin)")
    parser.add_argument("--no-plot", action="store_true", help="Do not generate summary plot")
    parser.add_argument("--ppc-fixed", type=int, default=None, help="Fix TYPICAL_PARTICLES_PER_CELL to this value instead of randomizing")
    # PPC sweep options
    parser.add_argument("--base-samples", type=int, default=0, help="Number of base parameter sets to sample and sweep over PPC")
    parser.add_argument("--ppc-min", type=int, default=None, help="Minimum PPC for sweep (inclusive)")
    parser.add_argument("--ppc-max", type=int, default=None, help="Maximum PPC for sweep (inclusive)")
    args = parser.parse_args()

    grid, steps = parse_cfg_grid_steps(CFG_FILE)
    print(f"Using grid={grid}, steps={steps} from {CFG_FILE}")

    results_csv = os.path.join(RESULTS_DIR, "results.csv")

    # If PPC sweep requested, run it and exit
    if args.base_samples and args.ppc_min is not None and args.ppc_max is not None:
        run_ppc_sweep(
            base_samples=args.base_samples,
            ppc_min=args.ppc_min,
            ppc_max=args.ppc_max,
            grid=grid,
            steps=steps,
            tag=args.tag,
            min_events=args.min_events,
            results_csv=results_csv,
            no_plot=args.no_plot,
        )
        return

    # Default: single/random runs (existing behavior)
    for i in range(args.runs):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{args.tag}_r{i+1}_{stamp}"
        print(f"\n=== Sampling parameters for run {i+1}/{args.runs} ===")
        sample, _details = sample_parameters_until_threshold(grid, steps, min_events=args.min_events)
        if sample is None:
            raise RuntimeError("Failed to sample parameters")
        if args.ppc_fixed is not None:
            sample['ppc'] = int(args.ppc_fixed)

        print(f"Chosen parameters (predicted_events={sample['predicted_events']:.3e}):\n"
              f"  gamma={sample['gamma']:.6f}, dt={sample['dt']:.3e}s\n"
              f"  cell=({sample['cell_w']:.3e}, {sample['cell_h']:.3e}, {sample['cell_d']:.3e}) m\n"
              f"  base_density={sample['base_density']:.3e} 1/m^3, ppc={sample['ppc']}")

        # Edit param files
        set_particle_gamma(sample['gamma'])
        set_simulation_params(sample['dt'], sample['cell_w'], sample['cell_h'], sample['cell_d'], sample['base_density'], sample['ppc'])

        # Compute prediction from read-back source params for CSV
        # (Use the sampled parameters directly)
        events_pred_src, details_src = predict_total_events(
            sample['gamma'],
            sample['base_density'],
            sample['cell_w'],
            sample['cell_h'],
            sample['cell_d'],
            grid,
            sample['dt'],
            steps,
        )

        # Persist chosen params
        chosen_json = os.path.join(RESULTS_DIR, f"{folder_name}_chosen_params.json")
        with open(chosen_json, "w") as f:
            json.dump({**sample, "predicted_events_src": events_pred_src}, f, indent=2)

        # Run simulation: always compile (no -r) since params changed
        run_simulation(folder_name, reuse_build=False)
        time.sleep(args.sleep)

        run_folder = get_run_folder(folder_name)
        ran_params = parse_params_from_destination_or_source(run_folder)

        # Also compute prediction from destination params (debug)
        events_pred_ran, details_ran = predict_total_events(
            ran_params["gamma"],
            ran_params["BASE_DENSITY_SI"],
            ran_params["CELL_WIDTH_SI"],
            ran_params["CELL_HEIGHT_SI"],
            ran_params["CELL_DEPTH_SI"],
            grid,
            ran_params["DELTA_T_SI"],
            steps,
        )

        he4_count, he4_path = read_he4_final_count(run_folder)

        row = {
            "timestamp": stamp,
            "folder": folder_name,
            "gamma": ran_params["gamma"],
            "dt": ran_params["DELTA_T_SI"],
            "cell_w": ran_params["CELL_WIDTH_SI"],
            "cell_h": ran_params["CELL_HEIGHT_SI"],
            "cell_d": ran_params["CELL_DEPTH_SI"],
            "base_density": ran_params["BASE_DENSITY_SI"],
            "ppc": ran_params["TYPICAL_PARTICLES_PER_CELL"],
            "grid_x": grid[0],
            "grid_y": grid[1],
            "grid_z": grid[2],
            "steps": steps,
            "predicted_events": events_pred_src,
            "predicted_events_ran": events_pred_ran,
            "measured_He4_final": he4_count,
            "E_rel_keV": details_src["E_rel_keV"],
            "v_rel": details_src["v_rel"],
            "sigma_m2": details_src["sigma_m2"],
            "volume": details_src["volume"],
            "total_time": details_src["time"],
            "he4_file": he4_path,
        }
        append_results_csv(row, results_csv)
        print(f"Run saved. Measured He4={he4_count:.3e}. CSV updated: {results_csv}")

        if not args.no_plot:
            out_png = os.path.join(RESULTS_DIR, "predicted_vs_measured_by_ppc.png")
            plot_results_by_ppc(results_csv, out_png)
            print(f"Summary plot saved to {out_png}")


def append_results_csv(row: dict, results_csv: str):
    """Append a row to CSV. If file exists, enforce its header order; otherwise create with RESULT_SCHEMA.
    This avoids inconsistent column counts that break pandas read_csv.
    """
    if os.path.isfile(results_csv):
        # Read existing header to keep column order stable
        with open(results_csv, "r", newline="") as f:
            reader = csv.reader(f)
            try:
                existing_cols = next(reader)
            except StopIteration:
                existing_cols = RESULT_SCHEMA
        filtered = {k: row.get(k, "") for k in existing_cols}
        with open(results_csv, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=existing_cols)
            writer.writerow(filtered)
    else:
        # Create new file with default schema
        with open(results_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=RESULT_SCHEMA)
            writer.writeheader()
            writer.writerow({k: row.get(k, "") for k in RESULT_SCHEMA})


def plot_results_by_ppc(results_csv: str, out_png: str):
    try:
        df = pd.read_csv(results_csv, engine="python", on_bad_lines="skip")
    except TypeError:
        # Fallback for very old pandas without on_bad_lines
        df = pd.read_csv(results_csv, engine="python")
    if df.empty:
        print("No results to plot.")
        return
    # Sort by PPC if present
    if "ppc" in df.columns:
        df = df.sort_values("ppc")
        x = df["ppc"]
    else:
        x = df.index
    plt.figure(figsize=(10, 6))
    if "predicted_events" in df.columns:
        plt.scatter(x, df["predicted_events"], label="Predicted", marker="o", s=30)
    if "measured_He4_final" in df.columns:
        plt.scatter(x, df["measured_He4_final"], label="Measured He4", marker="x", s=30)
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("TYPICAL_PARTICLES_PER_CELL")
    plt.ylabel("Events / He4 count (log)")
    plt.title("Predicted vs Measured (He4) vs TYPICAL_PARTICLES_PER_CELL")
    plt.grid(True, which="both", linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


if __name__ == "__main__":
    main()
