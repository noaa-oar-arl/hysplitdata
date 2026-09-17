#!/usr/bin/env python3
"""Quick analysis of a PARDUMP/PARINIT file.

Usage:
    python examples/examine_pardump.py path/to/PARINIT
"""
import argparse
import numpy as np
import hysplitdata


def parse_args():
    parser = argparse.ArgumentParser(
        description="Quick summary statistics for a PARDUMP/PARINIT file.")
    parser.add_argument("pardump", help="Path to PARDUMP or PARINIT file")
    return parser.parse_args()


args = parse_args()
pardump = hysplitdata.read_pardump(args.pardump)

print(f"Particles: {len(pardump.particles):,}")
print(f"Pollutants: {pardump.pollutants_per_particle}")
print(f"Raw year in file: {pardump.year}")
print(f"Month: {pardump.month}, Day: {pardump.day}, Hour: {pardump.hour}, Minute: {pardump.minute}")
print(f"datetime: {pardump.datetime}")
print()

# Altitude stats
alts = np.array([p.altitude for p in pardump.particles])
print("=== Altitude (m AGL) ===")
print(f"  min={alts.min():.2f}, max={alts.max():.2f}, mean={alts.mean():.2f}")
print(f"  median={np.median(alts):.2f}")
bins = [0, 500, 2000, 5000, 10000, 20000]
labels = ["0-500", "500-2000", "2000-5000", "5000-10000", ">10000"]
for i in range(len(bins)-1):
    lo, hi = bins[i], bins[i+1]
    if i == len(bins)-2:
        n = np.sum(alts > lo)
    else:
        n = np.sum((alts > lo) & (alts <= hi))
    print(f"  {labels[i]}: {n:,} ({100*n/len(alts):.1f}%)")
print()

# Sigma stats
sigmaws = np.array([p.sigmaw for p in pardump.particles])
print("=== sigmaw (w-component turbulence, m/s) ===")
print(f"  min={sigmaws.min():.2e}, max={sigmaws.max():.2e}, mean={sigmaws.mean():.2e}")
print(f"  zero count: {np.sum(sigmaws == 0):,}")
print(f"  unique values (first 30): {np.unique(sigmaws)[:30]}")
print()

sigmavs = np.array([p.sigmav for p in pardump.particles])
print("=== sigmav (v-component turbulence, m/s) ===")
print(f"  min={sigmavs.min():.2e}, max={sigmavs.max():.2e}, mean={sigmavs.mean():.2e}")
print(f"  zero count: {np.sum(sigmavs == 0):,}")
print(f"  unique values (first 30): {np.unique(sigmavs)[:30]}")
print()

sigmahs = np.array([p.sigmah for p in pardump.particles])
print("=== sigmah (horizontal sigma) ===")
print(f"  min={sigmahs.min():.2e}, max={sigmahs.max():.2e}, mean={sigmahs.mean():.2e}")
print(f"  zero count: {np.sum(sigmahs == 0):,}")
print()

# Age stats
ages = np.array([p.age for p in pardump.particles])
print("=== age ===")
print(f"  min={ages.min():.4f}, max={ages.max():.4f}, mean={ages.mean():.4f}")
print()

# Mass per pollutant index
print("=== Mass by pollutant index ===")
for pi in range(pardump.pollutants_per_particle):
    masses = np.array([p.pollutant_mass[pi] for p in pardump.particles])
    total = masses.sum()
    nonzero = np.count_nonzero(masses)
    print(f"  Pollutant {pi:2d}: total={total:.6e}, nonzero={nonzero:,}/{len(masses):,}")
print()

# Distribution and pollutant indices
dists = np.array([p.distribution for p in pardump.particles])
polls = np.array([p.pollutant for p in pardump.particles])
print("=== distribution ===")
print(f"  unique: {np.unique(dists, return_counts=True)}")
print()
print("=== pollutant index ===")
print(f"  unique: {np.unique(polls, return_counts=True)}")
print()

# Lat/lon range
lats = np.array([p.latitude for p in pardump.particles])
lons = np.array([p.longitude for p in pardump.particles])
print("=== Spatial extent ===")
print(f"  lat: {lats.min():.4f} to {lats.max():.4f}")
print(f"  lon: {lons.min():.4f} to {lons.max():.4f}")
