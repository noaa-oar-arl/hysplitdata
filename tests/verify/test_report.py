"""Tests for report module."""

import os

import pytest
import pandas as pd

from hysplitdata.verify.config import VerificationConfig
from hysplitdata.verify.report import generate_report
from hysplitdata.verify.runner import VerificationResults


def _make_results_with_plots(tmp_path):
    """Create results that include fake plot files on disk."""
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

    plume_integrity = pd.DataFrame()
    plume_dynamics = pd.DataFrame()

    # Create two real plot files
    plot_dir = tmp_path / "plots"
    plot_dir.mkdir()
    plot_a = plot_dir / "mass_time_series.png"
    plot_b = plot_dir / "com_trajectory.png"
    plot_a.write_text("fake png")
    plot_b.write_text("fake png")

    return VerificationResults(
        mass_balance=mass_balance,
        mass_by_level=pd.DataFrame(),
        plume_integrity=plume_integrity,
        plume_dynamics=plume_dynamics,
        plots={
            "mass_time_series": str(plot_a),
            "com_trajectory":   str(plot_b),
        },
        warnings=[],
    )


@pytest.fixture
def sample_config():
    """Create a VerificationConfig for testing."""
    return VerificationConfig(initial_mass=1.0)


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
        "time_index": [0, 1, 2],
        "datetime": dates,
        "vert_level_m": [100, 100, 100],
        "category": ["airborne"] * 3,
        "mass": [0.5, 0.4, 0.25],
        "fraction_of_total": [0.5, 0.4, 0.25],
    })

    plume_integrity = pd.DataFrame()
    plume_dynamics = pd.DataFrame()

    return VerificationResults(
        mass_balance=mass_balance,
        mass_by_level=mass_by_level,
        plume_integrity=plume_integrity,
        plume_dynamics=plume_dynamics,
        warnings=["No level-0 grids found"],
    )


def test_report_generates_markdown(sample_results, sample_config):
    """Report should be a non-empty markdown string."""
    report = generate_report(sample_results, sample_config, cdump_path="test.cdump")
    assert isinstance(report, str)
    assert len(report) > 0


def test_report_contains_header(sample_results, sample_config):
    """Report should contain the main header."""
    report = generate_report(sample_results, sample_config, cdump_path="test.cdump")
    assert "# HYSPLIT Verification Report" in report


def test_report_contains_file_path(sample_results, sample_config):
    """Report should contain the cdump file path."""
    report = generate_report(sample_results, sample_config, cdump_path="my_cdump")
    assert "File: my_cdump" in report


def test_report_contains_configuration(sample_results, sample_config):
    """Report should contain the configuration section."""
    report = generate_report(sample_results, sample_config, cdump_path="test.cdump")
    assert "## Configuration" in report
    assert "Initial mass" in report
    assert "Deposition mode" in report
    assert "Conservation tolerance" in report


def test_report_contains_mass_conservation(sample_results, sample_config):
    """Report should contain mass conservation results."""
    report = generate_report(sample_results, sample_config, cdump_path="test.cdump")
    assert "## Mass Conservation" in report
    assert "Final airborne mass" in report
    assert "Final deposited mass" in report
    assert "Max conservation residual" in report


def test_report_contains_pass_fail(sample_results, sample_config):
    """Report should contain PASS/FAIL status for conservation check."""
    report = generate_report(sample_results, sample_config, cdump_path="test.cdump")
    assert "PASS" in report or "FAIL" in report


def test_report_contains_warnings(sample_results, sample_config):
    """Report should list all warnings."""
    report = generate_report(sample_results, sample_config, cdump_path="test.cdump")
    assert "## Warnings" in report
    assert "No level-0 grids found" in report


def test_report_no_warnings(sample_config):
    """Report should say (none) when there are no warnings."""
    dates = pd.date_range("2024-01-01", periods=1)
    results = VerificationResults(
        mass_balance=pd.DataFrame({
            "time_index": [0],
            "datetime": dates,
            "total_airborne_mass": [0.8],
            "total_deposited_mass": [0.1],
            "conservation_residual_pct": [0.01],
            "airborne_fraction": [0.8],
            "deposited_fraction": [0.1],
            "deposition_mode": ["direct"],
        }),
        mass_by_level=pd.DataFrame(),
        plume_integrity=pd.DataFrame(),
        plume_dynamics=pd.DataFrame(),
        warnings=[],
    )

    report = generate_report(results, sample_config, cdump_path="test.cdump")
    assert "(none)" in report


def test_report_empty_mass_balance(sample_config):
    """Report should handle empty mass balance gracefully."""
    results = VerificationResults(
        mass_balance=pd.DataFrame(),
        mass_by_level=pd.DataFrame(),
        plume_integrity=pd.DataFrame(),
        plume_dynamics=pd.DataFrame(),
        warnings=[],
    )

    report = generate_report(results, sample_config, cdump_path="test.cdump")
    assert "No data available" in report


def test_report_particle_mass_included(sample_config):
    """Report should include particle mass when set."""
    config = VerificationConfig(initial_mass=1000.0, particle_mass_g=1e-9)

    dates = pd.date_range("2024-01-01", periods=1)
    results = VerificationResults(
        mass_balance=pd.DataFrame({
            "time_index": [0],
            "datetime": dates,
            "total_airborne_mass": [800.0],
            "total_deposited_mass": [100.0],
            "conservation_residual_pct": [0.01],
            "airborne_fraction": [0.8],
            "deposited_fraction": [0.1],
            "deposition_mode": ["direct"],
        }),
        mass_by_level=pd.DataFrame(),
        plume_integrity=pd.DataFrame(),
        plume_dynamics=pd.DataFrame(),
        warnings=[],
    )

    report = generate_report(results, config, cdump_path="test.cdump")
    assert "Particle mass" in report


def test_report_pollutants_included(sample_config):
    """Report should list pollutants when specified."""
    config = VerificationConfig(
        initial_mass=1.0, include_pollutants=["TEST", "MORE"]
    )

    dates = pd.date_range("2024-01-01", periods=1)
    results = VerificationResults(
        mass_balance=pd.DataFrame({
            "time_index": [0],
            "datetime": dates,
            "total_airborne_mass": [0.8],
            "total_deposited_mass": [0.1],
            "conservation_residual_pct": [0.01],
            "airborne_fraction": [0.8],
            "deposited_fraction": [0.1],
            "deposition_mode": ["direct"],
        }),
        mass_by_level=pd.DataFrame(),
        plume_integrity=pd.DataFrame(),
        plume_dynamics=pd.DataFrame(),
        warnings=[],
    )

    report = generate_report(results, config, cdump_path="test.cdump")
    assert "Pollutants analyzed" in report
    assert "TEST" in report
    assert "MORE" in report


def test_report_includes_plots_when_available(tmp_path, sample_config):
    """Report should embed plots section when results.plots is populated."""
    results = _make_results_with_plots(tmp_path)
    config = VerificationConfig(initial_mass=1.0, output_dir=str(tmp_path / "plots"))

    report = generate_report(results, config, cdump_path="test.cdump")
    assert "## Plots" in report
    # Markdown image links use ![]()
    assert "![" in report
    # Should reference the plot filenames
    assert "mass_time_series.png" in report
    assert "com_trajectory.png" in report


def test_report_skips_plots_when_empty(sample_results, sample_config):
    """Report should not include a plots section when results.plots is empty."""
    report = generate_report(sample_results, sample_config, cdump_path="test.cdump")
    assert "## Plots" not in report


def test_report_skips_missing_plot_files(tmp_path, sample_config):
    """Report should omit plots that no longer exist on disk."""
    results = _make_results_with_plots(tmp_path)
    # Remove one plot file so only one remains
    (tmp_path / "plots" / "mass_time_series.png").unlink()

    config = VerificationConfig(initial_mass=1.0, output_dir=str(tmp_path / "plots"))
    report = generate_report(results, config, cdump_path="test.cdump")

    assert "## Plots" in report
    assert "com_trajectory.png" in report
    assert "mass_time_series.png" not in report
