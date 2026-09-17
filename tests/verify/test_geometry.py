"""Tests for geometry module."""

import math
import pytest
import numpy as np
from hysplitdata.verify.geometry import (
    compute_cell_areas,
    compute_layer_thicknesses,
    METERS_PER_DEGREE_LAT,
)


def test_cell_area_equator():
    """Cell area at equator for 0.5 deg grid."""
    lons = np.arange(-90, 90, 0.5)  # 360 points
    lats = np.arange(-90, 90, 0.5)   # 360 points
    dlon, dlat = 0.5, 0.5

    areas = compute_cell_areas(lons, lats, (dlon, dlat))

    # At equator (lat=0), width = 111320 * 0.5, height = 111320 * 0.5
    expected = (METERS_PER_DEGREE_LAT * dlat) * (METERS_PER_DEGREE_LAT * dlon)
    # Find the equator row (lat=0, idx=180 in range -90..89.5 step 0.5)
    eq_row_idx = 180
    assert abs(areas[eq_row_idx, 0] - expected) < 1e-6


def test_cell_area_pole():
    """Cell area near poles should be small compared to equator."""
    lons = np.arange(-90, 90, 0.5)
    lats = np.arange(-89, 89, 0.5)  # Avoid exact poles
    areas = compute_cell_areas(lons, lats, (0.5, 0.5))

    # Near poles (lat ~88.5 or ~-88.5), cos(lat) is very small
    # equator area is ~3.1e9 m^2, pole area should be much less
    eq_area = areas[len(areas)//2, 0]
    assert areas[0, 0] < eq_area  # pole area < equator area
    assert areas[-1, -1] < eq_area
    # Ratio should be roughly cos(pole_lat): cos(88.5) ≈ 0.026
    assert areas[0, 0] / eq_area < 0.05


def test_cell_area_midlatitude():
    """Cell area at 45 deg latitude."""
    lons = np.arange(-90, 90, 1.0)
    lats = np.arange(-45, 45, 1.0)  # 90 values
    dlon, dlat = 1.0, 1.0

    areas = compute_cell_areas(lons, lats, (dlon, dlat))

    # At 45 deg, width = 111320 * cos(45) * 1.0
    expected = (METERS_PER_DEGREE_LAT * dlat) * (METERS_PER_DEGREE_LAT * math.cos(math.radians(45)) * dlon)
    # lat=45 is at index 89 (45 - (-45) / 1.0 = 90, but that's out of bounds)
    # Actually lat values are -45, -44, ..., 43. So lat=45 is not in the array.
    # lat=43 is at index 88
    eq_row_idx = 88  # lat=43
    cos_43 = math.cos(math.radians(43))
    expected_43 = (METERS_PER_DEGREE_LAT * dlat) * (METERS_PER_DEGREE_LAT * cos_43 * dlon)
    assert abs(areas[eq_row_idx, 0] - expected_43) < 1e-6


def test_layer_thickness_uniform():
    """Uniform spacing [100, 300, 500] -> thickness = 200m for each."""
    levels = [0, 100, 300, 500]
    thicknesses = compute_layer_thicknesses(levels)

    assert 0 not in thicknesses  # level 0 excluded
    assert abs(thicknesses[100] - 100) < 1e-6   # bottom: half_above = (300-100)/2 = 100
    assert abs(thicknesses[300] - 200) < 1e-6   # middle: 100+100 = 200
    assert abs(thicknesses[500] - 200) < 1e-6   # top: 2*(500-300)/2 = 200


def test_layer_thickness_edge_layers():
    """Bottom layer has only half_above, top layer estimates same spacing."""
    levels = [0, 100, 500]
    thicknesses = compute_layer_thicknesses(levels)

    # Bottom: half_above = (500-100)/2 = 200
    assert abs(thicknesses[100] - 200) < 1e-6
    # Top: 2*(500-100)/2 = 400
    assert abs(thicknesses[500] - 400) < 1e-6


def test_layer_thickness_single_level():
    """Single airborne level uses itself as thickness proxy."""
    levels = [0, 200]
    thicknesses = compute_layer_thicknesses(levels)
    assert abs(thicknesses[200] - 200) < 1e-6


def test_layer_thickness_excludes_zero():
    """Level 0 must NOT appear in thickness dict."""
    levels = [0, 100, 300]
    thicknesses = compute_layer_thicknesses(levels)
    assert 0 not in thicknesses


def test_layer_thickness_no_airborne():
    """Only level 0 -> empty dict."""
    levels = [0]
    thicknesses = compute_layer_thicknesses(levels)
    assert thicknesses == {}


def test_cell_areas_shape():
    """Output shape matches (nlat, nlon)."""
    lons = np.linspace(-90, 90, 181)
    lats = np.linspace(-60, 60, 121)
    areas = compute_cell_areas(lons, lats, (1.0, 1.0))
    assert areas.shape == (121, 181)

    # Also verify different nlon/nlat
    lons2 = np.linspace(0, 360, 200)
    lats2 = np.linspace(-30, 30, 61)
    areas2 = compute_cell_areas(lons2, lats2, (1.0, 1.0))
    assert areas2.shape == (61, 200)


def test_cell_areas_all_positive():
    """All cell areas should be positive (except poles)."""
    lons = np.linspace(-90, 90, 181)
    lats = np.linspace(-80, 80, 161)
    areas = compute_cell_areas(lons, lats, (1.0, 1.0))
    assert np.all(areas >= 0)
