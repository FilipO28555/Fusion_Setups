#!/usr/bin/env python3
"""
Read particle momenta for each timestep from PIConGPU openPMD output.

Requirements:
  pip install openpmd-api

Usage examples:
  # Pass the openPMD output directory; script auto-detects pattern
  python read_particle_momenta.py --series ./TestRun/simOutput/openPMD

  # Explicit file-based layout pattern (ADIOS2):
  python read_particle_momenta.py --series ./TestRun/simOutput/openPMD/simData_%06T.bp

  # Group-based single file (HDF5):
  python read_particle_momenta.py --series ./TestRun/simOutput/simData.h5

This script prints basic info and saves per-iteration CSV files with columns:
  species, id(optional), px, py, pz

Notes:
- PIConGPU writes momentum as particles/<species>/momentum/(x|y|z)
- Values are in code units; multiply by unitSI for SI if --scaleSI is set.
"""

import argparse
import re
from collections import Counter
from pathlib import Path

import numpy as np
import openpmd_api as opmd
from collections import defaultdict


def to_numpy(component, series):
    """Read a RecordComponent into a numpy array using slice + flush (compat)."""
    arr = component[:]
    series.flush()
    return np.array(arr)


ess_bp = re.compile(r"^(?P<prefix>.+)_(?P<num>\d+)\.bp$")


def deduce_series_path(series_arg: str) -> str:
    """Return a valid openPMD Series path or pattern from a user argument.

    Accepts:
    - A directory that contains file-based ADIOS2 .bp iteration directories
    - A single .bp iteration directory path
    - A single .h5 file (group-based layout)
    - An explicit pattern containing %T (passed as-is)
    """
    p = Path(series_arg)

    # If explicit pattern
    if "%T" in p.name:
        return str(p)

    # If a directory is provided
    if p.is_dir():
        # Case: this directory itself is like simData_000001.bp/
        m_self = ess_bp.match(p.name)
        if m_self:
            prefix = m_self.group("prefix")
            width = len(m_self.group("num"))
            return str(p.parent / f"{prefix}_%0{width}T.bp")

        # Case: a directory that contains many simData_XXXXXX.bp/ dirs
        bp_dirs = [d for d in p.iterdir() if d.is_dir() and ess_bp.match(d.name)]
        if bp_dirs:
            matches = [ess_bp.match(d.name) for d in bp_dirs]
            prefixes = [m.group("prefix") for m in matches]
            widths = [len(m.group("num")) for m in matches]
            # Choose most common prefix and width
            prefix = Counter(prefixes).most_common(1)[0][0]
            width = Counter(widths).most_common(1)[0][0]
            return str(p / f"{prefix}_%0{width}T.bp")

        # Maybe a group-based file sits inside (rare)
        h5_files = list(p.glob("*.h5"))
        if h5_files:
            return str(h5_files[0])

        raise ValueError(f"No openPMD files found in directory: {p}")

    # If a single file path is given
    if p.suffix == ".h5" and p.exists():
        return str(p)

    # If a single .bp dir was given as a path string that does not exist here
    # Try to treat it as a directory path and deduce pattern (user typo?)
    m = ess_bp.match(p.name)
    if m and p.parent.exists():
        width = len(m.group("num"))
        prefix = m.group("prefix")
        candidate = p.parent / f"{prefix}_%0{width}T.bp"
        return str(candidate)

    raise ValueError(
        "Argument must be an openPMD directory, a pattern with %T, or an .h5 file: "
        f"{series_arg}"
    )


def main():
    parser = argparse.ArgumentParser(description="Read particle momenta from openPMD series")
    parser.add_argument(
        "--series",
        required=True,
        help=(
            "Path to openPMD output: directory with *.bp iterations, a %T pattern, "
            "a single simData_000001.bp directory, or a .h5 file"
        ),
    )
    parser.add_argument("--out", default="momenta_csv", help="Output directory for CSV files")
    parser.add_argument("--scaleSI", action="store_true", help="Scale values by unitSI to SI units")
    parser.add_argument("--rtol", type=float, default=1e-10, help="Relative tolerance for momentum-sum equality check")
    parser.add_argument("--atol", type=float, default=0.0, help="Absolute tolerance for momentum-sum equality check")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    series_path = deduce_series_path(args.series)
    series = opmd.Series(series_path, opmd.Access.read_only)

    # Print openPMD standard info (compatible across API versions)
    std = getattr(series, "openPMD", None)
    if std is None:
        try:
            std = series.get_openPMD()
        except Exception:
            std = "unknown"
    print(f"openPMD standard: {std}")

    totals = []  # per-iteration total momentum sums [px_sum, py_sum, pz_sum]
    species_totals = defaultdict(list)  # species -> list of (sum_px, sum_py, sum_pz) per iteration

    # Build a sorted list of iteration IDs, compatible with older API containers
    try:
        iter_ids = list(series.iterations)
    except TypeError:
        # Fallback for types that are not directly iterable
        keys_attr = getattr(series.iterations, "keys", None)
        if keys_attr is None:
            raise
        iter_ids = list(keys_attr())
    iter_ids.sort()

    for idx, it in enumerate(iter_ids):
        iteration = series.iterations[it]
        species_names = list(iteration.particles)
        print(f"Iteration {it}: species = {species_names}")

        rows = []
        iter_px_sum = 0.0
        iter_py_sum = 0.0
        iter_pz_sum = 0.0

        # ensure previously known species lists are aligned to current index
        for name in list(species_totals.keys()):
            if len(species_totals[name]) < idx:
                species_totals[name].extend([(0.0, 0.0, 0.0)] * (idx - len(species_totals[name])))

        present_set = set(species_names)
        for species_name in species_names:
            species = iteration.particles[species_name]
            if "momentum" not in species:
                print(f"  Species {species_name} has no 'momentum' record; skipping")
                continue
            record = species["momentum"]

            # Ensure 3 components
            if not all(c in record for c in ("x", "y", "z")):
                print(f"  Species {species_name} momentum components incomplete: {list(record.keys())}")
                continue

            px = to_numpy(record["x"], series)
            py = to_numpy(record["y"], series)
            pz = to_numpy(record["z"], series)

            if args.scaleSI:
                px = px * record["x"].unit_SI
                py = py * record["y"].unit_SI
                pz = pz * record["z"].unit_SI

            # accumulate total momentum sums for this iteration
            sx = float(np.sum(px))
            sy = float(np.sum(py))
            sz = float(np.sum(pz))
            iter_px_sum += sx
            iter_py_sum += sy
            iter_pz_sum += sz
            # backfill zeros for species first seen now
            if len(species_totals[species_name]) < idx:
                species_totals[species_name].extend([(0.0, 0.0, 0.0)] * (idx - len(species_totals[species_name])))
            species_totals[species_name].append((sx, sy, sz))

            # Optional particle ids
            ids = None
            if "id" in species:
                try:
                    ids = to_numpy(species["id"][opmd.Mesh_Record_Component.SCALAR], series)
                except Exception:
                    ids = None

            n = px.size
            if ids is None or ids.size != n:
                rows.extend((species_name, "", float(px[i]), float(py[i]), float(pz[i])) for i in range(n))
            else:
                rows.extend((species_name, int(ids[i]), float(px[i]), float(py[i]), float(pz[i])) for i in range(n))

        # fill zeros for species missing in this iteration to keep alignment
        for name in list(species_totals.keys()):
            if name not in present_set and len(species_totals[name]) < idx + 1:
                species_totals[name].append((0.0, 0.0, 0.0))

        # store per-iteration total momentum sums
        totals.append((iter_px_sum, iter_py_sum, iter_pz_sum))

        out_path = out_dir / f"momenta_{it:06d}.csv"
        with out_path.open("w") as f:
            f.write("species,id,px,py,pz\n")
            for r in rows:
                f.write(f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]}\n")
        print(f"  Wrote {len(rows)} rows to {out_path}")

    # simple test: check if total particle momentum sums are the same across iterations
    if totals:
        totals_arr = np.array(totals)  # shape (n_iter, 3)
        ref = totals_arr[0]
        ok = np.allclose(totals_arr, ref, rtol=args.rtol, atol=args.atol)
        max_dev = np.max(np.abs(totals_arr - ref), axis=0)
        print(
            f"Momentum-sum constant across iterations: {'YES' if ok else 'NO'}\n"
            f"  Reference (iter 0): px={ref[0]:.6e}, py={ref[1]:.6e}, pz={ref[2]:.6e}\n"
            f"  Max deviation: dpx={max_dev[0]:.6e}, dpy={max_dev[1]:.6e}, dpz={max_dev[2]:.6e} (rtol={args.rtol}, atol={args.atol})"
        )

        # Plot absolute and relative change of total momentum across iterations
        try:
            import matplotlib.pyplot as plt

            iters = np.array(iter_ids, dtype=int)
            diff = totals_arr - ref  # absolute change per component
            # relative error (absolute) per component, guard zero reference
            denom = np.where(np.abs(ref) > 0, np.abs(ref), np.nan)
            rel = np.abs(diff) / denom

            fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

            axes[0].plot(iters, diff[:, 0], label="dpx", marker="o")
            axes[0].plot(iters, diff[:, 1], label="dpy", marker="s")
            axes[0].plot(iters, diff[:, 2], label="dpz", marker="^")
            axes[0].set_ylabel("Absolute change of sum(p)")
            axes[0].grid(True, ls=":")
            axes[0].legend()

            axes[1].plot(iters, rel[:, 0], label="|dpx|/|px0|", marker="o")
            axes[1].plot(iters, rel[:, 1], label="|dpy|/|py0|", marker="s")
            axes[1].plot(iters, rel[:, 2], label="|dpz|/|pz0|", marker="^")
            axes[1].set_xlabel("Iteration")
            axes[1].set_ylabel("Relative change of sum(p)")
            axes[1].set_yscale("symlog", linthresh=1e-16)
            axes[1].grid(True, ls=":")
            axes[1].legend()

            fig.suptitle("Total momentum change across iterations")
            plot_path = out_dir / "momentum_sum_change.png"
            fig.tight_layout(rect=[0, 0.03, 1, 0.95])
            fig.savefig(plot_path, dpi=150)
            print(f"Saved plot: {plot_path}")

            # Plot per-species total momentum sums (absolute)
            species_names_all = sorted(species_totals.keys())
            # pad any species with fewer entries to match iterations
            for name in species_names_all:
                if len(species_totals[name]) < len(iters):
                    missing = len(iters) - len(species_totals[name])
                    species_totals[name].extend([(np.nan, np.nan, np.nan)] * missing)

            fig2, ax2 = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
            labels = ("sum(px)", "sum(py)", "sum(pz)")
            for comp_idx in range(3):
                for name in species_names_all:
                    arr = np.array(species_totals[name])  # shape (n_iter, 3)
                    ax2[comp_idx].plot(iters, arr[:, comp_idx], label=name)
                ax2[comp_idx].set_ylabel(labels[comp_idx])
                ax2[comp_idx].grid(True, ls=":")
                if comp_idx == 0:
                    ax2[comp_idx].legend(ncol=min(4, len(species_names_all)))
            ax2[-1].set_xlabel("Iteration")
            fig2.suptitle("Per-species total momentum across iterations")
            plot_path2 = out_dir / "species_momentum_sums.png"
            fig2.tight_layout(rect=[0, 0.03, 1, 0.95])
            fig2.savefig(plot_path2, dpi=150)
            print(f"Saved plot: {plot_path2}")

            # Plot per-species relative change vs first iteration
            fig3, ax3 = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
            for comp_idx in range(3):
                for name in species_names_all:
                    arr = np.array(species_totals[name])
                    ref_s = arr[0, comp_idx]
                    denom_s = np.abs(ref_s) if np.abs(ref_s) > 0 else np.nan
                    rel_s = np.abs(arr[:, comp_idx] - ref_s) / denom_s
                    ax3[comp_idx].plot(iters, rel_s, label=name)
                ax3[comp_idx].set_ylabel(f"rel {labels[comp_idx]}")
                ax3[comp_idx].set_yscale("symlog", linthresh=1e-16)
                ax3[comp_idx].grid(True, ls=":")
                if comp_idx == 0:
                    ax3[comp_idx].legend(ncol=min(4, len(species_names_all)))
            ax3[-1].set_xlabel("Iteration")
            fig3.suptitle("Per-species relative momentum change")
            plot_path3 = out_dir / "species_momentum_relative.png"
            fig3.tight_layout(rect=[0, 0.03, 1, 0.95])
            fig3.savefig(plot_path3, dpi=150)
            print(f"Saved plot: {plot_path3}")

            # New: single plot of magnitude per species + overall total magnitude
            # choose order of interest; fall back to all present
            preferred = ["d", "t", "n", "He4"]
            names_plot = [n for n in preferred if n in species_totals]
            if not names_plot:
                names_plot = species_names_all

            fig4, ax4 = plt.subplots(1, 1, figsize=(10, 5))
            for name in names_plot:
                arr = np.array(species_totals[name])  # (n_iter, 3)
                mag = np.sqrt(np.sum(arr**2, axis=1))
                ax4.plot(iters, mag, label=name)
            total_mag = np.sqrt(np.sum(totals_arr**2, axis=1))
            ax4.plot(iters, total_mag, label="total", linestyle="--", color="k")
            ax4.set_xlabel("Iteration")
            ax4.set_ylabel("|sum(p)| per species / total")
            ax4.grid(True, ls=":")
            ax4.legend(ncol=min(5, len(names_plot) + 1))
            fig4.suptitle("Per-species momentum magnitude and total")
            plot_path4 = out_dir / "species_momentum_magnitude.png"
            fig4.tight_layout(rect=[0, 0.03, 1, 0.95])
            fig4.savefig(plot_path4, dpi=150)
            print(f"Saved plot: {plot_path4}")
        except ImportError:
            print("matplotlib not installed; skipping plot (pip install matplotlib)")
    else:
        print("No particle momentum data found to test conservation.")

    series.close()


if __name__ == "__main__":
    main()
