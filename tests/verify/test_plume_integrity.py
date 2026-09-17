"""Tests for plume_integrity module."""

import numpy as np
import pandas as pd
import pytest

from hysplitdata.conc.model import ConcentrationDump, ConcentrationGrid
from hysplitdata.verify import VerificationConfig
from hysplitdata.verify.plume_integrity import compute_plume_integrity


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


def test_negative_cells_detected():
    """Negative concentration cells should be counted."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-6, -1e-9], [2e-6, -2e-9]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, warnings = compute_plume_integrity(cdump, config)

    assert len(rows) == 1
    row = rows[0]
    assert row["negative_cells"] == 2
    assert row["category"] == "airborne"


def test_grid_coverage_pct():
    """Grid coverage percentage should reflect non-zero cells."""
    lons = [0, 1, 2]
    lats = [0, 1]
    # 2x3 = 6 cells, 4 non-zero
    data = [[1e-6, 0, 1e-6], [0, 1e-6, 1e-6]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_integrity(cdump, config)

    row = rows[0]
    assert row["nonzero_cells"] == 4
    assert abs(row["grid_coverage_pct"] - (4 / 6 * 100)) < 0.01


def test_deposited_level_category():
    """Level 0 should be categorized as 'deposited'."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-3, 2e-3], [3e-3, 0]]
    g = _make_grid(lons, lats, data, vert_level=0)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_integrity(cdump, config)

    row = rows[0]
    assert row["category"] == "deposited"
    assert row["vert_level_m"] == 0


def test_negative_deposited_warning():
    """Negative deposited cells should produce a warning."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-3, -1e-6], [0, 0]]
    g = _make_grid(lons, lats, data, vert_level=0)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, warnings = compute_plume_integrity(cdump, config)

    assert len(warnings) > 0
    assert any("deposited" in w.lower() for w in warnings)


def test_negative_airborne_warning():
    """Negative airborne cells should produce a warning."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-6, -1e-9], [0, 0]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, warnings = compute_plume_integrity(cdump, config)

    assert len(warnings) > 0
    assert any("level 100" in w for w in warnings)


def test_multiple_levels():
    """Multiple levels should each produce a row."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-6, 2e-6], [3e-6, 4e-6]]
    g1 = _make_grid(lons, lats, data, vert_level=100)
    g2 = _make_grid(lons, lats, data, vert_level=300)
    cdump = _make_cdump(lons, lats, [g1, g2])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_integrity(cdump, config)

    assert len(rows) == 2
    levels = [r["vert_level_m"] for r in rows]
    assert 100 in levels
    assert 300 in levels


def test_multiple_time_steps():
    """Multiple time steps should all be analyzed."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-6, 2e-6], [3e-6, 4e-6]]
    g1 = _make_grid(lons, lats, data, vert_level=100, time_index=0)
    g2 = _make_grid(lons, lats, data, vert_level=100, time_index=1)
    cdump = _make_cdump(lons, lats, [g1, g2])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_integrity(cdump, config)

    assert len(rows) == 2
    time_indices = [r["time_index"] for r in rows]
    assert 0 in time_indices
    assert 1 in time_indices


def test_no_negative_warning_for_clean_data():
    """Clean data should produce no negative-cell warnings."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-6, 2e-6], [3e-6, 4e-6]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, warnings = compute_plume_integrity(cdump, config)

    assert len(warnings) == 0


def test_min_positive_conc():
    """min_positive_conc should reflect the smallest positive value."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-6, 2e-6], [3e-6, 1e-10]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_integrity(cdump, config)

    assert abs(rows[0]["min_positive_conc"] - 1e-10) < 1e-20


def test_negative_mass_fraction():
    """Negative mass fraction should be positive ratio of |negative| / |total|."""
    lons = [0, 1]
    lats = [0, 1]
    data = [[1e-6, -1e-6], [1e-6, 1e-6]]
    g = _make_grid(lons, lats, data, vert_level=100)
    cdump = _make_cdump(lons, lats, [g])
    config = VerificationConfig(initial_mass=1.0)

    rows, _ = compute_plume_integrity(cdump, config)

    # |neg| = 1e-6, total_abs = 4e-6, so fraction = 0.25
    assert abs(rows[0]["negative_mass_fraction"] - 0.25) < 1e-10

