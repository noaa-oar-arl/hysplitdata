"""Tests for plots module."""

import os
import sys
import tempfile
import pytest

# Skip the entire file if matplotlib is not available
pytest.importorskip("matplotlib")

import numpy as np
import pandas as pd

from hysplitdata.verify.plots import generate_all_plots
from hysplitdata.verify.runner import VerificationResults


@pytest.fixture
def sample_results():
    """Create a minimal VerificationResults with sample data."""
    dates = pd.date_range("2024-01-01", periods=3, freq="6h")

    mass_balance = pd.DataFrame({
        "time_index": [0, 1, 2],
        "datetime": dates,
        "total_airborne_mass": [0.8, 0.6, 0.4],
        "total_deposited_mass": [0.1, 0.3, 0.5],
        "conservation_residual_pct": [0.01, -0.02, 0.005],
        "airborne_fraction": [0.8, 0.6, 0.4],
        "deposited_fraction": [0.1, 0.3, 0.5],
        "deposition_mode": ["inferred", "inferred", "inferred"],
    })

    mass_by_level = pd.DataFrame({
        "time_index": [0, 0, 1, 1, 2, 2],
        "datetime": dates[[0, 0, 1, 1, 2, 2]],
        "vert_level_m": [100, 300, 100, 300, 100, 300],
        "category": ["airborne"] * 6,
        "mass": [0.5, 0.3, 0.4, 0.2, 0.25, 0.15],
        "fraction_of_total": [0.5, 0.3, 0.4, 0.2, 0.25, 0.15],
    })

    plume_integrity = pd.DataFrame({
        "time_index": [0, 0, 1, 1, 2, 2],
        "datetime": dates[[0, 0, 1, 1, 2, 2]],
        "vert_level_m": [100, 300, 100, 300, 100, 300],
        "category": ["airborne"] * 6,
        "negative_cells": [2, 0, 1, 0, 0, 0],
        "negative_mass_fraction": [0.001, 0.0, 0.0005, 0.0, 0.0, 0.0],
        "max_conc": [1e-6, 5e-7, 8e-7, 4e-7, 6e-7, 3e-7],
        "min_positive_conc": [1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9],
        "max_lat": [45.0, 45.0, 46.0, 46.0, 47.0, 47.0],
        "max_lon": [-90.0, -90.0, -89.0, -89.0, -88.0, -88.0],
        "nonzero_cells": [100, 80, 120, 90, 110, 70],
        "grid_coverage_pct": [2.77, 2.21, 3.33, 2.49, 3.05, 1.94],
    })

    plume_dynamics = pd.DataFrame({
        "time_index": [0, 1, 2],
        "datetime": dates,
        "com_lat": [45.0, 46.0, 47.0],
        "com_lon": [-90.0, -89.0, -88.0],
        "vertical_centroid_m": [200.0, 210.0, 220.0],
        "sigma_lat": [0.5, 0.6, 0.7],
        "sigma_lon": [0.4, 0.5, 0.6],
        "sigma_z_m": [50.0, 55.0, 60.0],
        "nonzero_cells": [180, 210, 180],
        "plume_area_km2": [100.0, 120.0, 110.0],
    })

    return VerificationResults(
        mass_balance=mass_balance,
        mass_by_level=mass_by_level,
        plume_integrity=plume_integrity,
        plume_dynamics=plume_dynamics,
        warnings=[],
    )


def test_generate_all_plots_creates_files(sample_results):
    """All 9 plots should be generated and saved as PNG files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = generate_all_plots(sample_results, tmpdir, dpi=100)

        expected_plots = [
            "mass_time_series",
            "mass_by_altitude",
            "conservation_residual",
            "negative_cells",
            "grid_coverage",
            "max_concentration",
            "com_trajectory",
            "vertical_centroid",
            "plume_spread_area",
        ]

        for name in expected_plots:
            assert name in paths, f"Plot '{name}' was not generated"
            assert paths[name] is not None
            assert os.path.exists(paths[name]), f"File not found: {paths[name]}"
            assert paths[name].endswith(".png")


def test_generate_all_plots_empty_dataframes():
    """Empty DataFrames should not crash plot generation."""
    empty_results = VerificationResults(
        mass_balance=pd.DataFrame(),
        mass_by_level=pd.DataFrame(),
        plume_integrity=pd.DataFrame(),
        plume_dynamics=pd.DataFrame(),
        warnings=[],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        paths = generate_all_plots(empty_results, tmpdir, dpi=100)

        for name, path in paths.items():
            assert path is None, f"Plot '{name}' should be None for empty data"


def test_plot_output_dir_created():
    """Output directory should be created if it does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = os.path.join(tmpdir, "nested", "output")
        assert not os.path.exists(output_dir)

        dates = pd.date_range("2024-01-01", periods=2)
        results = VerificationResults(
            mass_balance=pd.DataFrame({
                "time_index": [0, 1],
                "datetime": dates,
                "total_airborne_mass": [0.8, 0.6],
                "total_deposited_mass": [0.1, 0.3],
                "conservation_residual_pct": [0.01, -0.02],
                "airborne_fraction": [0.8, 0.6],
                "deposited_fraction": [0.1, 0.3],
                "deposition_mode": ["inferred", "inferred"],
            }),
            mass_by_level=pd.DataFrame({
                "time_index": [0, 1],
                "datetime": dates,
                "vert_level_m": [100, 100],
                "category": ["airborne", "airborne"],
                "mass": [0.5, 0.4],
                "fraction_of_total": [0.5, 0.4],
            }),
            plume_integrity=pd.DataFrame({
                "time_index": [0, 1],
                "datetime": dates,
                "vert_level_m": [100, 100],
                "category": ["airborne", "airborne"],
                "negative_cells": [0, 0],
                "negative_mass_fraction": [0.0, 0.0],
                "max_conc": [1e-6, 8e-7],
                "min_positive_conc": [1e-9, 1e-9],
                "max_lat": [45.0, 46.0],
                "max_lon": [-90.0, -89.0],
                "nonzero_cells": [100, 120],
                "grid_coverage_pct": [2.77, 3.33],
            }),
            plume_dynamics=pd.DataFrame({
                "time_index": [0, 1],
                "datetime": dates,
                "com_lat": [45.0, 46.0],
                "com_lon": [-90.0, -89.0],
                "vertical_centroid_m": [200.0, 210.0],
                "sigma_lat": [0.5, 0.6],
                "sigma_lon": [0.4, 0.5],
                "sigma_z_m": [50.0, 55.0],
                "nonzero_cells": [180, 210],
                "plume_area_km2": [100.0, 120.0],
            }),
            warnings=[],
        )

        paths = generate_all_plots(results, output_dir, dpi=100)
        assert os.path.isdir(output_dir)
        assert any(p is not None for p in paths.values())


def test_mass_time_series_plot(sample_results):
    """Mass time series plot should produce a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from hysplitdata.verify.plots import _plot_mass_time_series
        path = _plot_mass_time_series(sample_results.mass_balance, tmpdir, 100)
        assert path is not None
        assert os.path.exists(path)


def test_mass_by_altitude_plot(sample_results):
    """Mass by altitude plot should produce a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from hysplitdata.verify.plots import _plot_mass_by_altitude
        path = _plot_mass_by_altitude(sample_results.mass_by_level, tmpdir, 100)
        assert path is not None
        assert os.path.exists(path)


def test_conservation_residual_plot(sample_results):
    """Conservation residual plot should produce a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from hysplitdata.verify.plots import _plot_conservation_residual
        path = _plot_conservation_residual(sample_results.mass_balance, tmpdir, 100)
        assert path is not None
        assert os.path.exists(path)


def test_negative_cells_plot(sample_results):
    """Negative cells plot should produce a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from hysplitdata.verify.plots import _plot_negative_cells
        path = _plot_negative_cells(sample_results.plume_integrity, tmpdir, 100)
        assert path is not None
        assert os.path.exists(path)


def test_grid_coverage_plot(sample_results):
    """Grid coverage plot should produce a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from hysplitdata.verify.plots import _plot_grid_coverage
        path = _plot_grid_coverage(sample_results.plume_integrity, tmpdir, 100)
        assert path is not None
        assert os.path.exists(path)


def test_max_concentration_plot(sample_results):
    """Max concentration plot should produce a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from hysplitdata.verify.plots import _plot_max_concentration
        path = _plot_max_concentration(sample_results.plume_integrity, tmpdir, 100)
        assert path is not None
        assert os.path.exists(path)


def test_com_trajectory_plot(sample_results):
    """Center of mass trajectory plot should produce a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from hysplitdata.verify.plots import _plot_com_trajectory
        path = _plot_com_trajectory(sample_results.plume_dynamics, tmpdir, 100)
        assert path is not None
        assert os.path.exists(path)


def test_vertical_centroid_plot(sample_results):
    """Vertical centroid plot should produce a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from hysplitdata.verify.plots import _plot_vertical_centroid
        path = _plot_vertical_centroid(sample_results.plume_dynamics, tmpdir, 100)
        assert path is not None
        assert os.path.exists(path)


def test_plume_spread_area_plot(sample_results):
    """Plume spread/area dual-axis plot should produce a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from hysplitdata.verify.plots import _plot_plume_spread_area
        path = _plot_plume_spread_area(sample_results.plume_dynamics, tmpdir, 100)
        assert path is not None
        assert os.path.exists(path)
