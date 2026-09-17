"""Geometry computations for HYSPLIT concentration grid cells.

Computes latitude-corrected cell areas and vertical layer thicknesses.
Level 0 (deposited) has NO thickness — it is a surface quantity.
"""

import math
import numpy as np


# Meters per degree of latitude (approximately constant)
METERS_PER_DEGREE_LAT = 111320.0


def compute_cell_areas(longitudes, latitudes, grid_deltas):
    """Compute the area of each grid cell in square meters.

    Returns a 2D array of shape (nlat, nlon) where each element is the
    area of the corresponding grid cell.  The area varies by latitude row
    because east-west cell width shrinks toward the poles.

    Args:
        longitudes: Array of longitude values in degrees.
        latitudes: Array of latitude values in degrees.
        grid_deltas: Tuple (dlon, dlat) in degrees.

    Returns:
        numpy array of shape (nlat, nlon) with cell areas in m^2.
    """
    dlon, dlat = grid_deltas
    nlat = len(latitudes)
    nlon = len(longitudes)

    # Width of one degree of longitude at each latitude (nlat,)
    meters_per_deg_lon = np.array(
        [METERS_PER_DEGREE_LAT * math.cos(math.radians(lat)) for lat in latitudes]
    )

    # Cell dimensions in meters for each row (nlat,)
    cell_width = meters_per_deg_lon * abs(dlon)
    cell_height = np.full(nlat, METERS_PER_DEGREE_LAT * abs(dlat))

    # Per-row area: (nlat,), then broadcast to (nlat, nlon)
    row_areas = cell_height * cell_width  # (nlat,)
    areas = np.broadcast_to(row_areas[:, np.newaxis], (nlat, nlon)).copy()
    return areas


def compute_layer_thicknesses(vert_levels):
    """Compute the thickness of each vertical layer in meters.

    Level 0 (deposited mass) is excluded — it has no thickness.
    For airborne levels (>, 0), thickness is computed as the average of
    the half-spacing above and below each level.  Edge layers use the
    single available spacing.

    Args:
        vert_levels: Sorted list of vertical levels in meters.

    Returns:
        Dict mapping level (int) to thickness (float).  Level 0 is NOT included.
    """
    # Filter to airborne levels only (>, 0)
    airborne_levels = sorted([lv for lv in vert_levels if lv > 0])

    if not airborne_levels:
        return {}

    thicknesses = {}
    n = len(airborne_levels)

    for i, level in enumerate(airborne_levels):
        half_below = 0.0
        half_above = 0.0

        if i > 0:
            half_below = (level - airborne_levels[i - 1]) / 2.0
        if i < n - 1:
            half_above = (airborne_levels[i + 1] - level) / 2.0

        if i == 0 and i == n - 1:
            # Single airborne level — estimate thickness as 2x distance from ground
            # or use a default; use level itself as a rough thickness proxy
            thicknesses[level] = float(level)
        elif i == 0:
            # Bottom layer: only has spacing above
            thicknesses[level] = half_above
        elif i == n - 1:
            # Top layer: only has spacing below; estimate same spacing above
            thicknesses[level] = half_below * 2.0
        else:
            thicknesses[level] = half_below + half_above

    return thicknesses
