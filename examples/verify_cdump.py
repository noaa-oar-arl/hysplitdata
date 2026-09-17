"""Command-line interface for HYSPLIT concentration dump verification.

Estimates initial mass automatically from concentration data and
supports verifying multiple pollutants without scanning the full
cdump for each one.

Usage:
    python examples/verify_cdump.py path/to/cdump
    python examples/verify_cdump.py path/to/cdump -p P091 P099
    python examples/verify_cdump.py path/to/cdump --all
"""

import argparse
import os
import sys

# Allow running directly from the examples/ directory:
# add the project root (parent of examples/) to sys.path.
EXAMPLES_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(EXAMPLES_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import hysplitdata
from hysplitdata.verify import VerificationConfig
from hysplitdata.verify.geometry import compute_cell_areas, compute_layer_thicknesses
from hysplitdata.verify.mass_balance import compute_mass_balance
from hysplitdata.verify.plume_dynamics import compute_plume_dynamics


# HYSPLIT stores concentrations in #/cm3 or g/cm3; convert to SI (/m3 or g/m3)
CM3_TO_M3 = 1e6


def parse_args():
    parser = argparse.ArgumentParser(
        description="Verify HYSPLIT cdump for mass conservation and plume dynamics.")
    parser.add_argument("cdump", help="Path to cdump file")
    parser.add_argument(
        "-p", "--pollutants", nargs="+",
        help="Pollutant IDs to verify (default: P050 P075 P099)")
    parser.add_argument(
        "--all", dest="all_pollutants", action="store_true",
        help="Run verification for all pollutants in the cdump")
    parser.add_argument(
        "--initial-mass", type=float, default=None,
        help="Override the auto-estimated initial mass (grams)")
    return parser.parse_args()


class _SmallCDump:
    """Lightweight wrapper holding a subset of ConcentrationGrids.

    Built from the grids' parent ConcentrationDump so that each pollutant
    can be verified independently without iterating all 1400 grids.
    """

    def __init__(self, grids):
        parent = grids[0].parent
        self.grids = grids
        self.pollutants = parent.pollutants
        self.vert_levels = parent.vert_levels
        self.longitudes = parent.longitudes
        self.latitudes = parent.latitudes
        self.grid_deltas = parent.grid_deltas
        self._has_ground = parent.has_ground_level_grid()

    def has_ground_level_grid(self):
        return self._has_ground


def estimate_initial_mass(grids, cell_areas, layer_thicknesses):
    """Estimate airborne mass from the first time step (level > 0)."""
    mass = 0.0
    for g in grids:
        if g.time_index == 0 and g.vert_level > 0:
            conc_si = g.conc * CM3_TO_M3
            thickness = layer_thicknesses.get(g.vert_level)
            if thickness:
                mass += float(np.sum(conc_si * cell_areas * thickness))
    return mass


def format_residual(pct):
    """Return a human-readable label for a conservation residual."""
    if abs(pct) < 10:
        return "OK"
    elif pct < -5:
        return "LOSS"
    else:
        return "GAIN"


def verify_pollutant(poll, grids, cell_areas, layer_thicknesses, initial_mass=None):
    """Run mass-balance and plume-dynamics checks for a single pollutant."""
    if initial_mass is None:
        initial_mass = estimate_initial_mass(grids, cell_areas, layer_thicknesses)
    if initial_mass <= 0:
        return None

    sc = _SmallCDump(grids)

    config = VerificationConfig(
        initial_mass=initial_mass,
        output_dir=None,
        include_pollutants=[poll],
    )

    balance_rows, _, _ = compute_mass_balance(
        sc, config, cell_areas, layer_thicknesses)
    dyn_rows, _ = compute_plume_dynamics(sc, config, cell_areas)
    return balance_rows, dyn_rows, initial_mass


def main():
    args = parse_args()

    print("Loading cdump from %s ..." % args.cdump)
    cdump = hysplitdata.read_cdump(args.cdump)

    # Pre-compute geometry once (shared across all pollutants)
    cell_areas = compute_cell_areas(cdump.longitudes, cdump.latitudes, cdump.grid_deltas)
    layer_thicknesses = compute_layer_thicknesses(cdump.vert_levels)

    # Decide which pollutants to analyze
    if args.all_pollutants:
        poll_list = cdump.pollutants
    elif args.pollutants:
        poll_list = args.pollutants
    else:
        poll_list = ["P050", "P075", "P099"]

    for poll in poll_list:
        grids = [g for g in cdump.grids if g.pollutant == poll]
        if not grids:
            print("\n%s: not found in cdump" % poll)
            continue

        result = verify_pollutant(
            poll, grids, cell_areas, layer_thicknesses, args.initial_mass)
        if result is None:
            print("\n%s: no airborne data" % poll)
            continue

        balance_rows, dyn_rows, initial_mass = result

        print("\n=== %s  (initial_mass=%.4e) ===" % (poll, initial_mass))

        for r in balance_rows:
            res = r["conservation_residual_pct"]
            status = format_residual(res)
            print(
                "  t=%d  airborne=%.4e  deposited=%.4e  "
                "residual=%+.2f%% [%s]" % (
                    r["time_index"], r["total_airborne_mass"],
                    r["total_deposited_mass"], res, status))

        for r in dyn_rows:
            print(
                "  t=%d  com=(%.2f,%.2f)  sigma=(%.2f,%.2f)  "
                "area=%.0f km2  centroid=%.0f m" % (
                    r["time_index"], r["com_lat"], r["com_lon"],
                    r["sigma_lat"], r["sigma_lon"],
                    r["plume_area_km2"], r["vertical_centroid_m"]))

    print("\nDone!")


if __name__ == "__main__":
    main()
