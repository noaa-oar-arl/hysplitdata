"""Plume integrity checks for HYSPLIT concentration dump files.

Detects negative concentrations, hot spots, and quantifies plume coverage.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


def compute_plume_integrity(cdump, config, cell_areas=None):
    """Compute plume integrity metrics for each time step.

    Airborne grids (level > 0) and deposited grids (level == 0) are checked
    separately because they have different expectations.

    Args:
        cdump: ConcentrationDump object.
        config: VerificationConfig.
        cell_areas: Pre-computed 2D array (nlat, nlon) in m^2, or None.

    Returns:
        Tuple of (rows, warnings) where rows is a list of dicts.
    """
    from .geometry import compute_cell_areas as _compute_cell_areas

    if cell_areas is None:
        cell_areas = _compute_cell_areas(
            cdump.longitudes, cdump.latitudes, cdump.grid_deltas
        )

    warnings = []
    rows = []

    # Group grids by time_index
    grids_by_time = {}
    for g in cdump.grids:
        ti = g.time_index
        if ti not in grids_by_time:
            grids_by_time[ti] = {}
        grids_by_time[ti][g.vert_level] = g

    total_cells = cell_areas.size

    for time_index in sorted(grids_by_time.keys()):
        level_grids = grids_by_time[time_index]
        dt = None

        for level in sorted(level_grids.keys()):
            g = level_grids[level]
            dt = dt or g.starting_datetime
            conc = g.conc

            neg_mask = conc < 0
            neg_count = int(np.sum(neg_mask))
            neg_mass_frac = 0.0

            if neg_count > 0:
                neg_sum = float(np.abs(neg_mask.astype(float) * conc).sum())
                total_abs = float(np.abs(conc).sum())
                neg_mass_frac = neg_sum / total_abs if total_abs > 0 else 0.0

            nonzero = int(np.sum(conc > 0))
            coverage = nonzero / total_cells * 100.0 if total_cells > 0 else 0.0

            max_val = float(np.max(conc)) if conc.size > 0 else 0.0
            pos_vals = conc[conc > 0]
            min_pos = float(np.min(pos_vals)) if pos_vals.size > 0 else 0.0

            # Location of max concentration
            if conc.size > 0:
                idx = np.unravel_index(np.argmax(conc), conc.shape)
                max_lat = cdump.latitudes[idx[0]]
                max_lon = cdump.longitudes[idx[1]]
            else:
                max_lat, max_lon = 0.0, 0.0

            category = "deposited" if level == 0 else "airborne"

            rows.append({
                "time_index": time_index,
                "datetime": dt,
                "vert_level_m": level,
                "category": category,
                "negative_cells": neg_count,
                "negative_mass_fraction": neg_mass_frac,
                "max_conc": max_val,
                "min_positive_conc": min_pos,
                "max_lat": max_lat,
                "max_lon": max_lon,
                "nonzero_cells": nonzero,
                "grid_coverage_pct": coverage,
            })

            if neg_count > 0 and category == "airborne":
                warnings.append(
                    f"Time {time_index}: {neg_count} negative concentration cells "
                    f"at level {level} m."
                )
            elif neg_count > 0 and category == "deposited":
                warnings.append(
                    f"Time {time_index}: {neg_count} negative deposited mass cells "
                    f"at level 0."
                )

    return rows, warnings
