#!/usr/bin/env python3
"""
Comprehensive ASCII visualization and diagnostic of PARINIT file.

Produces:
  1. Mass vs altitude histograms
  2. Altitude distribution breakdown
  3. Sigma field diagnostics
  4. Data integrity checks
  5. Physical plausibility assessment
"""
import argparse
import numpy as np
import hysplitdata


def ascii_histogram(values, bins=20, title="", width=60):
    """Print an ASCII histogram."""
    if len(values) == 0:
        print(f"  (empty)")
        return
    counts, edges = np.histogram(values, bins=bins)
    max_count = counts.max() if counts.max() > 0 else 1
    print(f"\n  {title}")
    for i in range(len(counts)):
        bar_len = int(counts[i] / max_count * width) if max_count > 0 else 0
        bar = "#" * bar_len
        print(f"  {edges[i]:10.1f} - {edges[i+1]:10.1f} | {bar} {counts[i]:,}")


def print_section(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def check_plausibility(arr, name, min_val, max_val, unit):
    oob = ((arr < min_val) | (arr > max_val)).sum()
    pct = 100 * oob / len(arr)
    status = "OK" if oob == 0 else "WARN" if pct < 5 else "FAIL"
    return f"  [{status}] {name}: {oob:,}/{len(arr):,} ({pct:.1f}%) outside [{min_val}, {max_val}] {unit}"


def parse_args():
    parser = argparse.ArgumentParser(
        description="ASCII visualization and diagnostics for PARDUMP/PARINIT files.")
    parser.add_argument("pardump",
                        help="Path to PARDUMP or PARINIT file")
    return parser.parse_args()


def main():
    args = parse_args()
    pardump = hysplitdata.read_pardump(args.pardump)

    alts = np.array([p.altitude for p in pardump.particles])
    lats = np.array([p.latitude for p in pardump.particles])
    lons = np.array([p.longitude for p in pardump.particles])
    sigmahs = np.array([p.sigmah for p in pardump.particles])
    sigmaws = np.array([p.sigmaw for p in pardump.particles])
    sigmavs = np.array([p.sigmav for p in pardump.particles])
    ages = np.array([p.age for p in pardump.particles])
    sorts = np.array([p.sort_index for p in pardump.particles])
    dists = np.array([p.distribution for p in pardump.particles])
    polls = np.array([p.pollutant for p in pardump.particles])

    masses = np.zeros((len(pardump.particles), pardump.pollutants_per_particle))
    for pi in range(pardump.pollutants_per_particle):
        masses[:, pi] = np.array([p.pollutant_mass[pi] for p in pardump.particles])

    nonzero_mask = masses[:, 0] > 0
    active_aloft = nonzero_mask & (alts > 0)
    active_ground = nonzero_mask & (alts == 0)

    n_total = len(pardump.particles)
    n_aloft = active_aloft.sum()
    n_ground = active_ground.sum()
    n_inactive = (~nonzero_mask).sum()

    # SECTION 1: FILE OVERVIEW
    print_section("1. FILE OVERVIEW")
    print(f"  Total particles:          {n_total:,}")
    print(f"  Pollutants per particle:  {pardump.pollutants_per_particle}")
    print(f"  Dump timestamp:           {pardump.datetime}")
    domain_km_x = (lats.max() - lats.min()) * 111
    domain_km_y = (lons.max() - lons.min()) * 111 * np.cos(np.radians(lats.mean()))
    print(f"  Spatial extent:           lat {lats.min():.4f}-{lats.max():.4f}, "
          f"lon {lons.min():.4f}-{lons.max():.4f}")
    print(f"  Domain size:              {domain_km_x:.1f} x {domain_km_y:.1f} km")
    print()
    print("  Particle classification:")
    print(f"    Active aloft (alt>0, mass>0):  {n_aloft:,} ({100*n_aloft/n_total:.1f}%)")
    print(f"    Active ground (alt=0, mass>0): {n_ground:,} ({100*n_ground/n_total:.1f}%)")
    print(f"    Inactive (mass=0):             {n_inactive:,} ({100*n_inactive/n_total:.1f}%)")

    # SECTION 2: ALTITUDE DISTRIBUTION
    print_section("2. ALTITUDE DISTRIBUTION")
    print(f"\n  Overall: min={alts.min():.1f}, max={alts.max():.1f}, "
          f"mean={alts.mean():.1f}, median={np.median(alts):.1f} m")

    if n_aloft > 0:
        ascii_histogram(alts[active_aloft], bins=30,
                        title="Active particles aloft (alt > 0 m)")
        print(f"\n  Active aloft stats:")
        print(f"    min={alts[active_aloft].min():.1f} m, "
              f"max={alts[active_aloft].max():.1f} m, "
              f"mean={alts[active_aloft].mean():.1f} m, "
              f"median={np.median(alts[active_aloft]):.1f} m")

    # SECTION 3: MASS VS ALTITUDE
    print_section("3. MASS VS ALTITUDE (KEY DIAGNOSTIC)")
    if n_aloft > 0:
        alt_bins = [0, 500, 1000, 2000, 3000, 5000, 8000, 12000, 16000, 20000]
        mass0 = masses[:, 0]
        print(f"\n  Mass[0] by altitude band (active particles aloft only):")
        print(f"  {'Alt band (m)':<16} {'Count':>6} {'Nonzero':>8} "
              f"{'Mean (nz)':>12} {'Median (nz)':>13} {'Max':>12}")
        print(f"  {'-'*68}")
        for i in range(len(alt_bins) - 1):
            lo, hi = alt_bins[i], alt_bins[i + 1]
            mask = active_aloft & (alts > lo) & (alts <= hi)
            if mask.sum() > 0:
                vals = mass0[mask]
                nz = vals[vals > 0]
                nz_count = len(nz)
                if nz_count > 0:
                    print(f"  {lo:5.0f}-{hi:6.0f}      {mask.sum():6d} {nz_count:8d} "
                          f"{nz.mean():12.2e} {np.median(nz):13.2e} {nz.max():12.2e}")
                else:
                    print(f"  {lo:5.0f}-{hi:6.0f}      {mask.sum():6d} {0:8d} "
                          f"{'(zero)':>12} {'(zero)':>13} {'(zero)':>12}")

    # SECTION 4: POLLUTANT MASS SUMMARY
    print_section("4. POLLUTANT MASS SUMMARY")
    n_active = n_aloft + n_ground
    print(f"\n  {'P':>3} {'Nonzero':>8} {'% Active':>8} "
          f"{'Mean (nz)':>14} {'Min (nz)':>14} {'Max (nz)':>14}")
    print(f"  {'-'*65}")
    for pi in range(pardump.pollutants_per_particle):
        nz = masses[:, pi] > 0
        if nz.sum() > 0:
            vals = masses[:, pi][nz]
            pct = 100 * nz.sum() / n_active if n_active > 0 else 0
            print(f"  {pi:3d} {nz.sum():8d} {pct:7.1f}% "
                  f"{vals.mean():14.2e} {vals.min():14.2e} {vals.max():14.2e}")
        else:
            print(f"  {pi:3d} {0:8d} {0.0:7.1f}% "
                  f"{'(zero)':>14} {'(zero)':>14} {'(zero)':>14}")

    # SECTION 5: SIGMA FIELD DIAGNOSTICS
    print_section("5. SIGMA / TURBULENCE FIELD DIAGNOSTICS")
    print(f"\n  sigmah (horizontal dispersion, m):")
    print(f"    Overall: min={sigmahs.min():.2e}, max={sigmahs.max():.2e}, "
          f"mean={sigmahs.mean():.2e}")
    print(f"    Exactly zero: {(sigmahs==0).sum():,}/{n_total:,} "
          f"({100*(sigmahs==0).sum()/n_total:.1f}%)")

    print(f"\n  sigmaw (w-turbulence, m/s):")
    print(f"    Overall: min={sigmaws.min():.2e}, max={sigmaws.max():.2e}, "
          f"mean={sigmaws.mean():.2e}")
    print(f"    Zero: {(sigmaws==0).sum():,}")
    pos_fin = ((sigmaws > 0) & (sigmaws < 1e6)).sum()
    extreme = (sigmaws > 1e6).sum()
    print(f"    Positive finite (<1e6 m/s): {pos_fin:,}")
    print(f"    Extreme (>1e6 m/s): {extreme:,}")
    if n_aloft > 0:
        aloft_sw = sigmaws[active_aloft]
        print(f"    Active aloft: min={aloft_sw.min():.2e}, "
              f"max={aloft_sw.max():.2e}, mean={aloft_sw.mean():.2e}")

    print(f"\n  sigmav (v-turbulence, m/s):")
    print(f"    Overall: min={sigmavs.min():.2e}, max={sigmavs.max():.2e}, "
          f"mean={sigmavs.mean():.2e}")
    n_sent = (sigmavs == -1.0).sum()
    print(f"    Exactly -1.0 (sentinel): {n_sent:,}/{n_total:,} "
          f"({100*n_sent/n_total:.1f}%)")
    print(f"    Positive: {(sigmavs>0).sum():,}")
    neg_excl = ((sigmavs < 0) & (sigmavs != -1.0)).sum()
    print(f"    Negative (excl -1.0): {neg_excl:,}")
    if n_aloft > 0:
        aloft_sv = sigmavs[active_aloft]
        print(f"    Active aloft: min={aloft_sv.min():.2e}, "
              f"max={aloft_sv.max():.2e}, mean={aloft_sv.mean():.2e}")

    print(f"\n  age:")
    print(f"    min={ages.min():.4f}, max={ages.max():.4f}")
    print(f"    Exactly zero: {(ages==0).sum():,}/{n_total:,}")

    # SECTION 6: DATA INTEGRITY CHECKS
    print_section("6. DATA INTEGRITY CHECKS")
    neg_mass = (masses < 0).sum()
    print(f"  [{'OK' if neg_mass==0 else 'WARN'}] Negative masses: {neg_mass:,}")
    neg_sv = (sigmavs < 0).sum()
    print(f"  [{'OK' if neg_sv==0 else 'WARN'}] Negative sigmav: {neg_sv:,}")
    ext_sw = (sigmaws > 1e6).sum()
    print(f"  [{'OK' if ext_sw==0 else 'WARN'}] Extreme sigmaw (>1e6 m/s): {ext_sw:,}")
    all_sigmah_zero = (sigmahs == 0).all()
    print(f"  [INFO] sigmah all zero: {all_sigmah_zero} (expected: not yet computed)")
    all_age_zero = (ages == 0).all()
    print(f"  [INFO] age all zero: {all_age_zero} (expected for init file)")
    is_perm = np.array_equal(np.sort(sorts), np.arange(1, n_total + 1))
    print(f"  [{'OK' if is_perm else 'WARN'}] sort_index is 1..N permutation: {is_perm}")

    # SECTION 7: PHYSICAL PLAUSIBILITY
    print_section("7. PHYSICAL PLAUSIBILITY ASSESSMENT")
    print(f"\n  Altitude: {check_plausibility(alts, 'altitude', 0, 20000, 'm')}")
    if n_aloft > 0:
        print(check_plausibility(sigmaws[active_aloft], 'sigmaw aloft', 0, 20, 'm/s'))
        print(check_plausibility(sigmavs[active_aloft], 'sigmav aloft', 0, 50, 'm/s'))

    # SECTION 8: KEY FINDINGS
    print_section("8. KEY FINDINGS & RECOMMENDATIONS")
    print()
    print("  FINDINGS:")
    print("  ---------")

    # Finding 1: Inactive vs active particle ratio
    inactive_pct = 100 * n_inactive / n_total
    print(f"  1. {inactive_pct:.1f}% of particles ({n_inactive:,}/{n_total:,}) are "
          f"INACTIVE (zero mass).")
    if inactive_pct > 80:
        print("     High inactive fraction suggests many particles were deposited "
              "or removed.")
    elif inactive_pct > 20:
        print("     Moderate inactive fraction is typical for post-simulation dumps.")
    else:
        print("     Low inactive fraction suggests recent emission or minimal deposition.")

    # Finding 2: Active particle breakdown
    print()
    print(f"  2. Particles with nonzero mass[0]: {n_aloft + n_ground:,} total:")
    print(f"     - {n_aloft:,} aloft (alt > 0 m)  ({100*n_aloft/(n_aloft+n_ground):.1f}%)")
    print(f"     - {n_ground:,} at ground (alt = 0 m)  ({100*n_ground/(n_aloft+n_ground):.1f}%)")

    # Finding 3: Sigma field health check
    print()
    sigmah_all_zero = (sigmahs == 0).all()
    sigmaw_extreme = (sigmaws > 1e6).sum()
    sigmav_sentinel = (sigmavs == -1.0).sum()
    age_all_zero = (ages == 0).all()
    sigmaw_uninitialized = sigmaw_extreme > 0
    sigmav_uninitialized = sigmav_sentinel > 0
    any_sigma_issue = sigmah_all_zero or sigmaw_uninitialized or sigmav_uninitialized

    if any_sigma_issue:
        print("  3. Sigma/turbulence fields show signs of being uninitialized:")
        if sigmah_all_zero:
            print(f"     - sigmah = 0.0 for all {n_total:,} particles")
        if sigmaw_uninitialized:
            print(f"     - sigmaw: {sigmaw_extreme:,} values > 1e6 m/s "
                  f"(physically impossible; max={sigmaws.max():.2e})")
        if sigmav_uninitialized:
            print(f"     - sigmav: {sigmav_sentinel:,} sentinel -1.0 values "
                  f"({100*sigmav_sentinel/n_total:.1f}%)")
        if age_all_zero:
            print("     - age = 0.0 for all particles (not yet computed)")
    else:
        print("  3. Sigma/turbulence fields appear healthy (all populated).")

    # Finding 4: Mass[0] dynamic range
    if n_aloft > 0 or n_ground > 0:
        nz_vals = masses[:, 0][nonzero_mask]
        mn = nz_vals.min()
        mx = nz_vals.max()
        if mn > 0:
            dyn_range = np.log10(mx / mn)
            print()
            print(f"  4. mass[0] dynamic range: {dyn_range:.1f} orders of magnitude "
                  f"({mn:.2e} to {mx:.2e}).")
            if dyn_range > 10:
                print("     Large range suggests mixed emission sources or particle ages.")
            elif dyn_range < 3:
                print("     Narrow range suggests uniform emission characteristics.")

    # Finding 5: Pollutant diversity
    print()
    nz_counts = []
    for pi in range(pardump.pollutants_per_particle):
        nz_counts.append((pi, int((masses[:, pi] > 0).sum())))
    unique_counts = sorted(set(c for _, c in nz_counts))
    if len(unique_counts) > 2:
        print(f"  5. Pollutants show {len(unique_counts)} distinct nonzero-count groups:")
        for c in unique_counts:
            if c == 0:
                continue
            group = [p for p, cnt in nz_counts if cnt == c]
            labels = ", ".join(f"P{p}" for p in group[:6])
            if len(group) > 6:
                labels += f" (+{len(group)-6} more)"
            print(f"     {c:,} nonzero particles: {labels}")
    elif len(unique_counts) == 2:
        active_count = [c for c in unique_counts if c > 0][0]
        active_polls = [p for p, c in nz_counts if c > 0]
        print(f"  5. All {len(active_polls)} active pollutants share the same "
              f"{active_count:,} nonzero particles (uniform composition).")

    # Recommendations
    print()
    print("  RECOMMENDATIONS:")
    print("  ----------------")
    if any_sigma_issue:
        print("  - Sigma/turbulence fields (sigmah, sigmaw, sigmav) appear "
              "uninitialized or contain garbage.")
        print("    For meaningful turbulence diagnostics, use a PARDUMP produced")
        print("    after the dispersion simulation has run (not a PARINIT).")
    else:
        print("  - Sigma fields look populated — turbulence diagnostics should be "
              "reliable.")
    if n_aloft > 0:
        print(f"  - For mass-altitude analysis, focus on the {n_aloft:,} active aloft "
              "particles.")
    if inactive_pct > 80:
        print("  - The high inactive-particle fraction suggests this file is from a")
        print("    late simulation stage or an initialisation file with pre-deposited "
              "particles.")
    if pardump.datetime.year < 1950 or pardump.datetime.year > 2050:
        print(f"  - Timestamp year ({pardump.datetime.year}) is unusual. Verify the")
        print("    date interpretation (HYSPLIT stores years as 2-digit values).")
    print()


if __name__ == "__main__":
    main()