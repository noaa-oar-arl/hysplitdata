"""Tests for plume_dynamics module."""

import numpy as np
import pandas as pd
import pytest

from hysplitdata.conc.model import ConcentrationDump, ConcentrationGrid
from hysplitdata.verify import VerificationConfig
from hysplitdata.verify.plume_dynamics import compute_plume_dynamics


def _make_grid(lons, lats, conc_data, vert_level, time_index=0, pollutant="TEST", parent=None):
    """Helper to build a ConcentrationGrid with given concentration data."""
    g = ConcentrationGrid(parent)
    g.pollutant = pollutant
    g.vert_level = vert_level
    g.time_index = time_index
    g.conc = np.array(conc_data, dtype=float)
    g.starting_datetime = pd.Timestamp("2024-01-01 00:00:00")
    return g


def _make_cdump(lons, lats, grids):
    """Helper to build a ConcentrationDump with given grids."""
    cdump = ConcentrationDump()
    cdump.longitudes = lons
    cdump.latitudes = lats
    cdump.grid_deltas = (1.0, 1.0)
    cdump.pollutants = ["TEST"]
    cdump.vert_levels = sorted(set(g.vert_level for g in grids))
    cdump.grids = grids
    # Back-fill parent references
    for g in grids:
        g.parent = cdump
    return cdump


def test_center_of_mass_computation():
    """Center of mass should be weighted by concentration."""
    lons = [-1, 0, 1]
    lats = [0, 1, 2]
    data = [[0, 1, 0], [1, 10, 1], [0, 1, 0]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_dynamics(cdump, config)

    row = rows[0]
    assert abs(row["com_lat"] - 1.0) < 0.1
    assert abs(row["com_lon"] - 0.0) < 0.1


def test_deposited_level_excluded():
    """Level 0 (deposited) should be excluded from dynamics."""
    lons = [0]
    lats = [0]
    g0 = _make_grid(lons, lats, [[1e6]], vert_level=0)  # huge deposited
    g1 = _make_grid(lons, lats, [[1]], vert_level=100)
    cdump = _make_cdump(lons, lats, [g0, g1])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_dynamics(cdump, config)

    # Centroid should be 100m (only airborne level)
    assert abs(rows[0]["vertical_centroid_m"] - 100.0) < 0.1


def test_spread_positive():
    """Spread values should be positive for a non-trivial plume."""
    lons = [-1, 0, 1]
    lats = [0, 1, 2]
    data = [[1, 1, 1], [1, 10, 1], [1, 1, 1]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_dynamics(cdump, config)

    row = rows[0]
    assert row["sigma_lat"] > 0
    assert row["sigma_lon"] > 0
    assert row["sigma_z_m"] == 0.0  # single level -> no vertical spread


def test_vertical_spread_multiple_levels():
    """Vertical spread should be non-zero with multiple levels."""
    lons = [0]
    lats = [0]
    g1 = _make_grid(lons, lats, [[10]], vert_level=100)
    g2 = _make_grid(lons, lats, [[10]], vert_level=300)
    cdump = _make_cdump(lons, lats, [g1, g2])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_dynamics(cdump, config)

    assert rows[0]["sigma_z_m"] > 0


def test_plume_area_computed():
    """Plume area should be computed in km²."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-6, 0], [0, 1e-6]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_dynamics(cdump, config)

    assert rows[0]["plume_area_km2"] > 0
    assert rows[0]["nonzero_cells"] == 2


def test_empty_plume_returns_zeros():
    """A grid with all-zero concentrations should return zero metrics."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[0, 0], [0, 0]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_dynamics(cdump, config)

    row = rows[0]
    assert row["com_lat"] == 0.0
    assert row["com_lon"] == 0.0
    assert row["vertical_centroid_m"] == 0.0
    assert row["sigma_lat"] == 0.0
    assert row["sigma_lon"] == 0.0
    assert row["sigma_z_m"] == 0.0
    assert row["plume_area_km2"] == 0.0


def test_multiple_time_steps():
    """Multiple time steps should each produce a row."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-6, 2e-6], [3e-6, 4e-6]]
    g1 = _make_grid(lons, lats, data, vert_level=100, time_index=0)
    g2 = _make_grid(lons, lats, data, vert_level=100, time_index=1)
    cdump = _make_cdump(lons, lats, [g1, g2])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_dynamics(cdump, config)

    assert len(rows) == 2
    assert rows[0]["time_index"] == 0
    assert rows[1]["time_index"] == 1


def test_datetime_populated():
    """Each row should have its datetime populated."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-6, 2e-6], [3e-6, 4e-6]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_dynamics(cdump, config)

    assert rows[0]["datetime"] is not None


def test_only_deposited_returns_zeros():
    """If only level-0 grids exist, all dynamics should be zero."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-3, 2e-3], [3e-3, 4e-3]]
    g = _make_grid(lons, lats, data, vert_level=0)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_dynamics(cdump, config)

    row = rows[0]
    assert row["com_lat"] == 0.0
    assert row["vertical_centroid_m"] == 0.0
    assert row["plume_area_km2"] == 0.0
