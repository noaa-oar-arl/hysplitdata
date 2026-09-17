"""Plume dynamics analysis for HYSPLIT concentration dump files.

Computes center of mass, spread, and vertical centroid using only
airborne grids (level > 0).
"""

import logging
import math
import numpy as np

logger = logging.getLogger(__name__)


def compute_plume_dynamics(cdump, config, cell_areas=None):
    """Compute plume dynamics metrics for each time step.

    All metrics use only airborne grids (level > 0).

    Args:
        cdump: ConcentrationDump object.
        config: VerificationConfig.
        cell_areas: Pre-computed 2D array (nlat, nlon) in m^2, or None.

    Returns:
        Tuple of (rows, warnings).
    """
    from .geometry import compute_cell_areas as _compute_cell_areas

    if cell_areas is None:
        cell_areas = _compute_cell_areas(
            cdump.longitudes, cdump.latitudes, cdump.grid_deltas
        )

    warnings = []
    rows = []

    # Build latitude/longitude mesh grids for vectorized computation
    lon_mesh, lat_mesh = np.meshgrid(cdump.longitudes, cdump.latitudes)

    # Group grids by time_index
    grids_by_time = {}
    for g in cdump.grids:
        ti = g.time_index
        if ti not in grids_by_time:
            grids_by_time[ti] = {}
        grids_by_time[ti][g.vert_level] = g

    # Cell area for each cell
    cell_area_flat = cell_areas.flatten()

    for time_index in sorted(grids_by_time.keys()):
        level_grids = grids_by_time[time_index]
        dt = None

        # Accumulate across all airborne levels
        total_weighted_lat = 0.0
        total_weighted_lon = 0.0
        total_weighted_level = 0.0
        total_weight = 0.0

        for level in sorted(level_grids.keys()):
            if level == 0:
                continue  # Skip deposited
            g = level_grids[level]
            dt = dt or g.starting_datetime
            conc = g.conc

            # Weight by concentration * cell_area for proper integration
            weights = conc * cell_areas
            total_w = float(np.sum(weights))

            if total_w <= 0:
                continue

            total_weighted_lat += float(np.sum(weights * lat_mesh))
            total_weighted_lon += float(np.sum(weights * lon_mesh))
            total_weighted_level += float(np.sum(weights * level))
            total_weight += total_w

        if total_weight > 0:
            com_lat = total_weighted_lat / total_weight
            com_lon = total_weighted_lon / total_weight
            vert_centroid = total_weighted_level / total_weight

            # Compute spread (weighted std dev)
            sigma_lat = _weighted_std(cdump, level_grids, lat_mesh, cell_areas)
            sigma_lon = _weighted_std_lon(cdump, level_grids, lon_mesh, cell_areas, com_lat)
            sigma_z = _weighted_std_z(level_grids)

            # Plume area: sum actual cell areas where concentration > 0
            plume_area_km2 = _sum_active_cell_areas(level_grids, cell_areas) / 1e6
            nonzero = _count_nonzero(cdump, level_grids)
        else:
            com_lat = com_lon = vert_centroid = 0.0
            sigma_lat = sigma_lon = sigma_z = 0.0
            plume_area_km2 = 0.0
            nonzero = 0

        rows.append({
            "time_index": time_index,
            "datetime": dt,
            "com_lat": com_lat,
            "com_lon": com_lon,
            "vertical_centroid_m": vert_centroid,
            "sigma_lat": sigma_lat,
            "sigma_lon": sigma_lon,
            "sigma_z_m": sigma_z,
            "nonzero_cells": nonzero,
            "plume_area_km2": plume_area_km2,
        })

    return rows, warnings


def _weighted_std(cdump, level_grids, coord_mesh, cell_areas):
    """Compute concentration-weighted standard deviation for a coordinate.

    Uses a two-pass approach: first compute the global weighted mean (center of
    mass) across all levels, then compute weighted variance around that global
    mean.  This produces correct spread values for multi-level plumes.
    """
    # Pass 1: compute global weighted mean
    total_weight = 0.0
    weighted_sum = 0.0
    for level in sorted(level_grids.keys()):
        if level == 0:
            continue
        g = level_grids[level]
        conc = g.conc
        weights = conc * cell_areas
        w = float(np.sum(weights))
        if w <= 0:
            continue
        weighted_sum += float(np.sum(weights * coord_mesh))
        total_weight += w

    if total_weight <= 0:
        return 0.0

    global_mean = weighted_sum / total_weight

    # Pass 2: compute weighted variance around the global mean
    weighted_var = 0.0
    for level in sorted(level_grids.keys()):
        if level == 0:
            continue
        g = level_grids[level]
        conc = g.conc
        weights = conc * cell_areas
        weighted_var += float(np.sum(weights * (coord_mesh - global_mean) ** 2))

    return float(np.sqrt(weighted_var / total_weight))


def _weighted_std_lon(cdump, level_grids, coord_mesh, cell_areas, com_lat=0.0):
    """Compute concentration-weighted std dev for longitude.

    Applies a latitude correction (cos(lat)) to convert degrees of longitude
    to the equivalent distance at the plume's center-of-mass latitude, so
    that sigma_lon is directly comparable to sigma_lat.
    """
    raw_sigma = _weighted_std(cdump, level_grids, coord_mesh, cell_areas)
    # At the equator cos(lat)=1, so no correction; near poles the correction
    # shrinks sigma_lon to account for meridian convergence.
    raw_sigma *= math.cos(math.radians(com_lat))
    return raw_sigma


def _weighted_std_z(level_grids):
    """Compute concentration-weighted std dev of vertical level."""
    total_weight = 0.0
    weighted_sum = 0.0
    mean_level = 0.0
    for level in sorted(level_grids.keys()):
        if level == 0:
            continue
        g = level_grids[level]
        conc = g.conc
        cell_mass = float(np.sum(conc))
        if cell_mass <= 0:
            continue
        total_weight += cell_mass
        weighted_sum += cell_mass * level
    if total_weight > 0:
        mean_level = weighted_sum / total_weight

    weighted_var = 0.0
    for level in sorted(level_grids.keys()):
        if level == 0:
            continue
        g = level_grids[level]
        conc = g.conc
        cell_mass = float(np.sum(conc))
        if cell_mass <= 0:
            continue
        weighted_var += cell_mass * (level - mean_level) ** 2
    if total_weight > 0:
        return float(np.sqrt(weighted_var / total_weight))
    return 0.0


def _count_nonzero(cdump, level_grids):
    """Count total non-zero cells across all airborne levels at this time step."""
    total = 0
    for level in sorted(level_grids.keys()):
        if level == 0:
            continue
        g = level_grids[level]
        total += int(np.sum(g.conc > 0))
    return total


def _sum_active_cell_areas(level_grids, cell_areas):
    """Sum actual cell areas across all airborne levels where conc > 0.

    Unlike multiplying nonzero count by the mean cell area, this correctly
    accounts for latitude-dependent cell area variation.
    """
    total = 0.0
    for level in sorted(level_grids.keys()):
        if level == 0:
            continue
        g = level_grids[level]
        active = g.conc > 0
        total += float(np.sum(cell_areas[active]))
    return total
