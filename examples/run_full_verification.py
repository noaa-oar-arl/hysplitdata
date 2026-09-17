"""Generate a full verification report from a HYSPLIT output directory.

Reads both the PARINIT (for initial mass) and cdump (for concentration
grids), runs mass-balance and plume-dynamics checks, then writes CSVs
and a markdown report into an output directory.

Usage:
    python examples/run_full_verification.py ~/.aptool/single_run/
    python examples/run_full_verification.py ~/.aptool/single_run/ -p P091 P099
    python examples/run_full_verification.py ~/.aptool/single_run/ --all
"""
import argparse
import os
import sys

# Allow running directly from the examples/ directory:
EXAMPLES_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(EXAMPLES_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import hysplitdata
from hysplitdata.verify import VerificationConfig
from hysplitdata.verify.runner import VerificationRunner


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a full verification report from a HYSPLIT output directory.")
    parser.add_argument("outdir", help="Path to HYSPLIT output directory (contains cdump and PARINIT)")
    parser.add_argument(
        "-o", "--output-dir", default="./verification_output",
        help="Directory for CSVs, plots, and markdown report (default: ./verification_output)")
    parser.add_argument(
        "-p", "--pollutants", nargs="+",
        help="Pollutant IDs to verify (default: auto-detect from PARINIT)")
    parser.add_argument(
        "--all", dest="all_pollutants", action="store_true",
        help="Verify all pollutants in the cdump")
    parser.add_argument(
        "--initial-mass", type=float, default=None,
        help="Override the auto-estimated initial mass (particle count)")
    parser.add_argument(
        "--tolerance", type=float, default=0.1,
        help="Conservation tolerance in percent (default: 0.1)")
    parser.add_argument(
        "--no-plots", action="store_true",
        help="Skip plot generation (requires matplotlib)")
    parser.add_argument(
        "--dpi", type=int, default=150,
        help="Plot resolution in DPI (default: 150)")
    return parser.parse_args()


def find_file(outdir, name):
    """Find a file in the output directory (case-insensitive)."""
    for f in os.listdir(outdir):
        if f.lower() == name.lower():
            return os.path.join(outdir, f)
    return None


def estimate_initial_mass(pardump_path):
    """Sum all nonzero pollutant masses from PARINIT."""
    pd = hysplitdata.read_pardump(pardump_path)
    total = 0.0
    for p in pd.particles:
        for m in p.pollutant_mass:
            if m > 0:
                total += m
    return total


def main():
    args = parse_args()

    # Locate cdump and PARINIT
    cdump_path = find_file(args.outdir, "cdump")
    pardump_path = find_file(args.outdir, "PARINIT")

    if cdump_path is None:
        print("Error: no 'cdump' file found in %s" % args.outdir)
        sys.exit(1)
    if pardump_path is None:
        print("Warning: no 'PARINIT' file found — cannot auto-estimate initial mass")
        print("  Use --initial-mass to provide it manually.")
        if args.initial_mass is None:
            sys.exit(1)

    # Auto-estimate initial mass from PARINIT
    initial_mass = args.initial_mass
    if initial_mass is None:
        print("Reading PARINIT to estimate initial mass...")
        initial_mass = estimate_initial_mass(pardump_path)
        print("  Estimated initial mass: %.4e (particle count)" % initial_mass)

    # Read cdump
    print("Loading cdump from %s ..." % cdump_path)
    cdump = hysplitdata.read_cdump(cdump_path)
    print("  Pollutants: %d" % len(cdump.pollutants))
    print("  Vert levels: %s" % cdump.vert_levels)
    print("  Grid: %d x %d" % (len(cdump.longitudes), len(cdump.latitudes)))
    n_time_steps = len(cdump.grids) // (len(cdump.pollutants) * len(cdump.vert_levels))
    print("  Time steps: %d" % n_time_steps)

    # Decide which pollutants to analyze
    if args.all_pollutants:
        include = None  # means "all"
    elif args.pollutants:
        include = args.pollutants
    else:
        # Default: pick a representative subset
        include = [
            cdump.pollutants[len(cdump.pollutants) // 4],
            cdump.pollutants[len(cdump.pollutants) // 2],
            cdump.pollutants[3 * len(cdump.pollutants) // 4],
        ]
        print("  Default pollutants: %s" % include)

    # Build config
    config = VerificationConfig(
        initial_mass=initial_mass,
        output_dir=args.output_dir,
        particle_mass_g=None,  # Use particle count directly
        conservation_tolerance_pct=args.tolerance,
        plot_dpi=args.dpi,
        include_pollutants=include,
        cdump_path=cdump_path,
    )

    # Run verification
    print("Running verification...")
    runner = VerificationRunner(cdump, config)
    results = runner.run()

    # Print summary
    print()
    print("=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    print("Output directory: %s" % args.output_dir)
    if os.path.isdir(args.output_dir):
        files = sorted(os.listdir(args.output_dir))
        print("Files generated: %d" % len(files))
        for f in files:
            size = os.path.getsize(os.path.join(args.output_dir, f))
            print("  %s  (%d bytes)" % (f, size))

    # Print the report to stdout
    if results.report:
        print()
        print(results.report)


if __name__ == "__main__":
    main()