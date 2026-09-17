#!/usr/bin/env python3
"""Deep diagnostics of PARINIT file — cross-tabulate fields to find patterns."""
import argparse
import numpy as np
import hysplitdata


def parse_args():
    parser = argparse.ArgumentParser(
        description="Cross-tabulate PARDUMP/PARINIT fields to find patterns.")
    parser.add_argument("pardump",
                        help="Path to PARDUMP or PARINIT file")
    return parser.parse_args()


args = parse_args()
pardump = hysplitdata.read_pardump(args.pardump)

alts = np.array([p.altitude for p in pardump.particles])
sigmavs = np.array([p.sigmav for p in pardump.particles])
sigmaws = np.array([p.sigmaw for p in pardump.particles])
sigmahs = np.array([p.sigmah for p in pardump.particles])
sorts = np.array([p.sort_index for p in pardump.particles])
masses0 = np.array([p.pollutant_mass[0] for p in pardump.particles])
# Bounds-check before accessing pollutant_mass[3]
masses3 = np.array([
    p.pollutant_mass[3] if len(p.pollutant_mass) > 3 else 0.0
    for p in pardump.particles
])

at_ground = alts == 0
aloft = alts > 0

print('=== Cross-correlation ===')
print(f'alt=0 AND sigmav=-1: {np.sum(at_ground & (sigmavs == -1.0)):,}')
print(f'alt>0 AND sigmav=-1: {np.sum(aloft & (sigmavs == -1.0)):,}')
print(f'alt>0 AND sigmav>0: {np.sum(aloft & (sigmavs > 0)):,}')
print(f'alt>0 AND sigmav<0: {np.sum(aloft & (sigmavs < 0)):,}')

print()
print(f'alt=0 sigmaw nonzero: {np.sum(at_ground & (sigmaws != 0)):,}')
print(f'alt>0 sigmaw nonzero: {np.sum(aloft & (sigmaws != 0)):,}')

# sort_index range
print(f'sort_index: min={sorts.min()}, max={sorts.max()}, unique={len(np.unique(sorts))}')

# Do the 13000 nonzero mass particles have any pattern?
nonzero = masses0 > 0
print()
print(f'Nonzero mass[0]: {nonzero.sum():,}')
print(f'  of those at alt>0: {np.sum(nonzero & aloft):,}')
print(f'  of those at alt=0: {np.sum(nonzero & at_ground):,}')
nz_alts = alts[nonzero]
print(f'  altitude range: {nz_alts.min():.1f} - {nz_alts.max():.1f}')
print(f'  altitude mean: {nz_alts.mean():.1f}, median: {np.median(nz_alts):.1f}')

# Check sigmav for active vs inactive particles
nz_sigmav = sigmavs[nonzero]
print(f'  nonzero-mass sigmav: min={nz_sigmav.min():.6e}, max={nz_sigmav.max():.6e}, mean={nz_sigmav.mean():.6e}')

# Check sigmaw for active vs inactive particles
nz_sigmaw = sigmaws[nonzero]
print(f'  nonzero-mass sigmaw: min={nz_sigmaw.min():.6e}, max={nz_sigmaw.max():.6e}, mean={nz_sigmaw.mean():.6e}')

# mass[0] distribution for nonzero particles
print()
print('=== mass[0] distribution (nonzero) ===')
print(f'  percentile 5: {np.percentile(masses0[nonzero], 5):.2e}')
print(f'  percentile 25: {np.percentile(masses0[nonzero], 25):.2e}')
print(f'  percentile 50: {np.percentile(masses0[nonzero], 50):.2e}')
print(f'  percentile 75: {np.percentile(masses0[nonzero], 75):.2e}')
print(f'  percentile 95: {np.percentile(masses0[nonzero], 95):.2e}')
print(f'  max: {np.max(masses0[nonzero]):.2e}')

# mass[3] (second species with mass) for nonzero particles
print()
print('=== mass[3] distribution (nonzero) ===')
nz3 = masses3 > 0
print(f'  nonzero count: {nz3.sum():,}')
if nz3.sum() > 0:
    print(f'  min={np.min(masses3[nz3]):.6e}, max={np.max(masses3[nz3]):.6e}, mean={np.mean(masses3[nz3]):.6e}')
    print(f'  unique values: {np.unique(masses3[nz3])}')

# Check all 23 pollutants for nonzero mass patterns
print()
print('=== All pollutants: nonzero mass & mean for nonzero subset ===')
for pi in range(pardump.pollutants_per_particle):
    masses_pi = np.array([p.pollutant_mass[pi] for p in pardump.particles])
    nz = masses_pi > 0
    if nz.sum() > 0:
        vals = masses_pi[nz]
        print(f'  P{pi:2d}: count={nz.sum():6d}, mean={vals.mean():.6e}, '
              f'min={vals.min():.6e}, max={vals.max():.6e}')
