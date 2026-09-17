"""Mass balance computations for HYSPLIT concentration dump files.

Computes airborne mass, deposited mass, and conservation residuals
for each output time step and each pollutant.
"""

import copy
import logging
import numpy as np

from .geometry import compute_cell_areas, compute_layer_thicknesses

logger = logging.getLogger(__name__)


# HYSPLIT concentration units are typically #/cm3 or g/cm3.
# Convert cm3 to m3: 1 cm3 = 1e-6 m3, so conc in /cm3 * 1e6 = /m3.
CM3_TO_M3 = 1e6


def compute_mass_balance(cdump, config, cell_areas=None, layer_thicknesses=None):
    """Compute mass balance for all time steps and pollutants.

    Args:
        cdump: ConcentrationDump object.
        config: VerificationConfig with initial_mass, etc.
        cell_areas: Pre-computed 2D array (nlat, nlon) in m^2, or None.
        layer_thicknesses: Pre-computed dict {level: thickness_m}, or None.

    Returns:
        Tuple of (balance_rows, level_rows, warnings) where:
        - balance_rows: list of dicts for mass_balance table
        - level_rows: list of dicts for mass_by_level table
        - warnings: list of warning strings
    """
    if cell_areas is None:
        cell_areas = compute_cell_areas(
            cdump.longitudes, cdump.latitudes, cdump.grid_deltas
        )

    if layer_thicknesses is None:
        layer_thicknesses = compute_layer_thicknesses(cdump.vert_levels)

    warnings = []
    has_level_zero = cdump.has_ground_level_grid()
    deposition_mode = "direct" if has_level_zero else "inferred"

    if not has_level_zero:
        warnings.append(
            "No level-0 (deposited) grids found. "
            "Deposited mass will be inferred as initial_mass - airborne_mass. "
            "This conflates all loss mechanisms."
        )

    # Determine which pollutants to analyze
    pollutants = cdump.pollutants
    if config.include_pollutants is not None:
        pollutants = [p for p in config.include_pollutants if p in cdump.pollutants]
        missing = set(config.include_pollutants) - set(cdump.pollutants)
        if missing:
            warnings.append(f"Requested pollutants not found: {missing}")

    # Group grids by (time_index, pollutant, vert_level)
    grids_by_time = _group_grids_by_time(cdump.grids, pollutants)

    # Particle mass conversion factor
    mass_factor = 1.0
    if config.particle_mass_g is not None:
        mass_factor = config.particle_mass_g

    balance_rows = []
    level_rows = []

    for time_index in sorted(grids_by_time.keys()):
        time_grids = grids_by_time[time_index]
        dt = time_grids.get_datetime()

        total_airborne = 0.0
        total_deposited = 0.0

        for level in sorted(time_grids.levels):
            grid = time_grids.get_grid(level)
            if grid is None:
                continue

            conc = grid.conc.copy()
            conc_si = conc * CM3_TO_M3

            if level == 0:
                cell_mass = conc_si * cell_areas * mass_factor
                level_mass = float(np.sum(cell_mass))
                category = "deposited"
                total_deposited += level_mass
            else:
                thickness = layer_thicknesses.get(level)
                if thickness is None or thickness <= 0:
                    warnings.append(
                        f"No valid thickness for level {level} at time_index "
                        f"{time_index}; skipping this level."
                    )
                    continue
                cell_mass = conc_si * cell_areas * thickness * mass_factor
                level_mass = float(np.sum(cell_mass))
                category = "airborne"
                total_airborne += level_mass

            fraction = level_mass / config.initial_mass if config.initial_mass > 0 else 0.0
            level_rows.append({
                "time_index": time_index,
                "datetime": dt,
                "vert_level_m": level,
                "category": category,
                "mass": level_mass,
                "fraction_of_total": fraction,
            })

        if not has_level_zero:
            total_deposited = max(0.0, config.initial_mass - total_airborne)

        residual = (
            (total_airborne + total_deposited - config.initial_mass)
            / config.initial_mass * 100.0
            if config.initial_mass > 0
            else 0.0
        )
        airborne_frac = total_airborne / config.initial_mass if config.initial_mass > 0 else 0.0
        deposited_frac = total_deposited / config.initial_mass if config.initial_mass > 0 else 0.0

        balance_rows.append({
            "time_index": time_index,
            "datetime": dt,
            "total_airborne_mass": total_airborne,
            "total_deposited_mass": total_deposited,
            "conservation_residual_pct": residual,
            "airborne_fraction": airborne_frac,
            "deposited_fraction": deposited_frac,
            "deposition_mode": deposition_mode,
        })

    return balance_rows, level_rows, warnings


class _TimeGrids:
    """Helper to hold grids for a single time step."""

    def __init__(self):
        self.grids = {}  # {vert_level: ConcentrationGrid}

    def add(self, grid):
        self.grids[grid.vert_level] = grid

    @property
    def levels(self):
        return sorted(self.grids.keys())

    def get_grid(self, level):
        return self.grids.get(level)

    def get_datetime(self):
        if self.grids:
            g = next(iter(self.grids.values()))
            return g.starting_datetime
        return None


def _group_grids_by_time(grids, pollutants):
    """Group ConcentrationGrid objects by time_index and pollutant filter.

    Returns dict {time_index: _TimeGrids}.
    """
    by_time = {}

    for g in grids:
        if g.pollutant not in pollutants:
            continue
        ti = g.time_index
        if ti not in by_time:
            by_time[ti] = _TimeGrids()
        existing = by_time[ti].get_grid(g.vert_level)
        if existing is not None:
            # Combine concentration arrays without mutating the original
            # grid object stored in cdump.grids.
            existing.conc = existing.conc.copy() + g.conc
        else:
            # Store a shallow copy so that any later modification to this
            # grid's conc attribute does not affect the original cdump.grids entry.
            g_copy = copy.copy(g)
            g_copy.conc = g.conc.copy()
            by_time[ti].add(g_copy)

    return by_time
