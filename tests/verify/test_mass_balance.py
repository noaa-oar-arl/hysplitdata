"""Tests for mass balance module."""

import datetime
import pytest
import numpy as np
import pytz
from hysplitdata.verify import VerificationConfig
from hysplitdata.verify.mass_balance import compute_mass_balance
from hysplitdata.verify.geometry import compute_cell_areas, compute_layer_thicknesses
from hysplitdata.conc.model import ConcentrationDump, ConcentrationGrid


@pytest.fixture
def cdump():
    """Load the existing test cdump file."""
    import hysplitdata
    import os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = hysplitdata.read_cdump(os.path.join(base, "data/cdump_two_pollutants"))
    return d


def test_mass_balance_inferred_deposition(cdump):
    """Test mass balance when no level-0 grids exist."""
    config = VerificationConfig(initial_mass=1.0)
    cell_areas = compute_cell_areas(cdump.longitudes, cdump.latitudes, cdump.grid_deltas)
    thicknesses = compute_layer_thicknesses(cdump.vert_levels)

    balance_rows, level_rows, warnings = compute_mass_balance(
        cdump, config, cell_areas=cell_areas, layer_thicknesses=thicknesses
    )

    assert len(balance_rows) > 0
    assert all(r["deposition_mode"] == "inferred" for r in balance_rows)
    # Should have a warning about no level-0 grids
    assert any("level-0" in w.lower() for w in warnings)


def test_mass_by_level_has_categories(cdump):
    """Level rows should have correct categories."""
    config = VerificationConfig(initial_mass=1.0)
    cell_areas = compute_cell_areas(cdump.longitudes, cdump.latitudes, cdump.grid_deltas)
    thicknesses = compute_layer_thicknesses(cdump.vert_levels)

    balance_rows, level_rows, warnings = compute_mass_balance(
        cdump, config, cell_areas=cell_areas, layer_thicknesses=thicknesses
    )

    # All levels should be airborne (no level 0 in this cdump)
    assert all(r["category"] == "airborne" for r in level_rows)


def test_mass_balance_positive_mass(cdump):
    """All mass values should be non-negative."""
    config = VerificationConfig(initial_mass=1.0)
    cell_areas = compute_cell_areas(cdump.longitudes, cdump.latitudes, cdump.grid_deltas)
    thicknesses = compute_layer_thicknesses(cdump.vert_levels)

    balance_rows, level_rows, warnings = compute_mass_balance(
        cdump, config, cell_areas=cell_areas, layer_thicknesses=thicknesses
    )

    for r in balance_rows:
        assert r["total_airborne_mass"] >= 0
        assert r["total_deposited_mass"] >= 0

    for r in level_rows:
        assert r["mass"] >= 0


def test_filter_pollutants(cdump):
    """Test include_pollutants filter."""
    config = VerificationConfig(initial_mass=1.0, include_pollutants=["TEST"])
    cell_areas = compute_cell_areas(cdump.longitudes, cdump.latitudes, cdump.grid_deltas)
    thicknesses = compute_layer_thicknesses(cdump.vert_levels)

    balance_rows, level_rows, warnings = compute_mass_balance(
        cdump, config, cell_areas=cell_areas, layer_thicknesses=thicknesses
    )

    assert len(balance_rows) > 0


def test_missing_pollutant_warning():
    """Requesting a non-existent pollutant should produce a warning."""
    # Create a minimal mock cdump
    cdump = ConcentrationDump()
    cdump.pollutants = ["TEST"]
    cdump.vert_levels = [100]
    cdump.grids = []
    cdump.longitudes = [-90, -89]
    cdump.latitudes = [-45, -44]
    cdump.grid_deltas = (1.0, 1.0)

    config = VerificationConfig(initial_mass=1.0, include_pollutants=["FAKE"])
    cell_areas = compute_cell_areas(cdump.longitudes, cdump.latitudes, cdump.grid_deltas)
    thicknesses = compute_layer_thicknesses(cdump.vert_levels)

    balance_rows, level_rows, warnings = compute_mass_balance(
        cdump, config, cell_areas=cell_areas, layer_thicknesses=thicknesses
    )

    assert any("not found" in w.lower() for w in warnings)
