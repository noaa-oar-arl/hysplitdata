"""Plot generation for HYSPLIT verification results."""

import logging
import os
from typing import Optional, List

import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def generate_all_plots(results, output_dir, dpi=150):
    """Generate all verification plots and save to output_dir.

    Args:
        results: VerificationResults object.
        output_dir: Directory to save plot files.
        dpi: Plot resolution.

    Returns:
        Dict mapping plot name to file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    try:
        paths["mass_time_series"] = _plot_mass_time_series(
            results.mass_balance, output_dir, dpi
        )
    except Exception as e:
        logger.warning("Failed to generate mass_time_series plot: %s", e)

    try:
        paths["mass_by_altitude"] = _plot_mass_by_altitude(
            results.mass_by_level, output_dir, dpi
        )
    except Exception as e:
        logger.warning("Failed to generate mass_by_altitude plot: %s", e)

    try:
        paths["conservation_residual"] = _plot_conservation_residual(
            results.mass_balance, output_dir, dpi
        )
    except Exception as e:
        logger.warning("Failed to generate conservation_residual plot: %s", e)

    # --- Plume integrity plots ---
    try:
        paths["negative_cells"] = _plot_negative_cells(
            results.plume_integrity, output_dir, dpi
        )
    except Exception as e:
        logger.warning("Failed to generate negative_cells plot: %s", e)

    try:
        paths["grid_coverage"] = _plot_grid_coverage(
            results.plume_integrity, output_dir, dpi
        )
    except Exception as e:
        logger.warning("Failed to generate grid_coverage plot: %s", e)

    try:
        paths["max_concentration"] = _plot_max_concentration(
            results.plume_integrity, output_dir, dpi
        )
    except Exception as e:
        logger.warning("Failed to generate max_concentration plot: %s", e)

    # --- Plume dynamics plots ---
    try:
        paths["com_trajectory"] = _plot_com_trajectory(
            results.plume_dynamics, output_dir, dpi
        )
    except Exception as e:
        logger.warning("Failed to generate com_trajectory plot: %s", e)

    try:
        paths["vertical_centroid"] = _plot_vertical_centroid(
            results.plume_dynamics, output_dir, dpi
        )
    except Exception as e:
        logger.warning("Failed to generate vertical_centroid plot: %s", e)

    try:
        paths["plume_spread_area"] = _plot_plume_spread_area(
            results.plume_dynamics, output_dir, dpi
        )
    except Exception as e:
        logger.warning("Failed to generate plume_spread_area plot: %s", e)

    return paths


def _plot_mass_time_series(df, output_dir, dpi):
    """Stacked area: airborne and deposited mass over time."""
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    times = pd.to_datetime(df["datetime"])

    ax.fill_between(
        times, 0, df["total_airborne_mass"],
        label="Airborne", alpha=0.7, color="steelblue"
    )
    ax.fill_between(
        times,
        df["total_airborne_mass"],
        df["total_airborne_mass"] + df["total_deposited_mass"],
        label="Deposited", alpha=0.7, color="darkgreen"
    )

    ax.set_xlabel("Time")
    ax.set_ylabel("Mass")
    ax.set_title("Mass Over Time")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    path = os.path.join(output_dir, "mass_time_series.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_mass_by_altitude(df, output_dir, dpi):
    """Stacked bar: mass by altitude for each time step."""
    if df.empty:
        return None

    airborne = df[df["category"] == "airborne"]
    if airborne.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))

    time_indices = sorted(airborne["time_index"].unique())
    levels = sorted(airborne["vert_level_m"].unique())

    x = np.arange(len(time_indices))
    bottom = np.zeros(len(time_indices))

    for level in levels:
        masses = []
        for ti in time_indices:
            row = airborne[(airborne["time_index"] == ti) & (airborne["vert_level_m"] == level)]
            masses.append(row["mass"].values[0] if len(row) > 0 else 0)
        ax.bar(x, masses, bottom=bottom, label=f"{level} m", alpha=0.8)
        bottom += masses

    ax.set_xticks(x)
    ax.set_xticklabels([str(t) for t in time_indices])
    ax.set_xlabel("Time Index")
    ax.set_ylabel("Mass")
    ax.set_title("Mass by Altitude")
    ax.legend(title="Level (m)", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()

    path = os.path.join(output_dir, "mass_by_altitude.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_conservation_residual(df, output_dir, dpi):
    """Line plot: conservation residual over time with tolerance band."""
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 4))
    times = pd.to_datetime(df["datetime"])

    ax.plot(times, df["conservation_residual_pct"], "o-", color="red", label="Residual")
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)

    # Tolerance bands (use 0.1% default if not available)
    tolerance = 0.1
    ax.axhline(y=tolerance, color="orange", linestyle=":", alpha=0.5, label=f"+/- {tolerance}%")
    ax.axhline(y=-tolerance, color="orange", linestyle=":", alpha=0.5)

    ax.set_xlabel("Time")
    ax.set_ylabel("Conservation Residual (%)")
    ax.set_title("Mass Conservation Residual")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    path = os.path.join(output_dir, "conservation_residual.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_negative_cells(df, output_dir, dpi):
    """Stacked bar: negative cell counts by level over time."""
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 4))

    time_indices = sorted(df["time_index"].unique())
    levels = sorted(df["vert_level_m"].unique())

    x = np.arange(len(time_indices))
    bottom = np.zeros(len(time_indices))

    for level in levels:
        counts = []
        for ti in time_indices:
            row = df[(df["time_index"] == ti) & (df["vert_level_m"] == level)]
            counts.append(row["negative_cells"].values[0] if len(row) > 0 else 0)
        label = f"Level {level} m"
        color = "crimson" if level == 0 else "orangered"
        ax.bar(x, counts, bottom=bottom, label=label, alpha=0.8, color=color)
        bottom += counts

    ax.set_xticks(x)
    ax.set_xticklabels([str(t) for t in time_indices])
    ax.set_xlabel("Time Index")
    ax.set_ylabel("Negative Cell Count")
    ax.set_title("Negative Concentration Cells")
    ax.legend(title="Level (m)", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()

    path = os.path.join(output_dir, "negative_cells.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_grid_coverage(df, output_dir, dpi):
    """Line plot: grid coverage % over time per level."""
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 4))

    time_indices = sorted(df["time_index"].unique())
    levels = sorted(df["vert_level_m"].unique())

    for level in levels:
        coverages = []
        tix = []
        for ti in time_indices:
            row = df[(df["time_index"] == ti) & (df["vert_level_m"] == level)]
            if len(row) > 0:
                coverages.append(row["grid_coverage_pct"].values[0])
                tix.append(ti)
        if coverages:
            label = f"Level {level} m"
            ax.plot(tix, coverages, "o-", label=label, alpha=0.8)

    ax.set_xlabel("Time Index")
    ax.set_ylabel("Grid Coverage (%)")
    ax.set_title("Plume Grid Coverage Over Time")
    ax.legend(title="Level (m)", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True, alpha=0.3)

    path = os.path.join(output_dir, "grid_coverage.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_max_concentration(df, output_dir, dpi):
    """Line plot: max concentration over time per level."""
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 4))

    time_indices = sorted(df["time_index"].unique())
    levels = sorted(df["vert_level_m"].unique())

    for level in levels:
        max_concs = []
        tix = []
        for ti in time_indices:
            row = df[(df["time_index"] == ti) & (df["vert_level_m"] == level)]
            if len(row) > 0:
                max_concs.append(row["max_conc"].values[0])
                tix.append(ti)
        if max_concs:
            label = f"Level {level} m"
            ax.plot(tix, max_concs, "o-", label=label, alpha=0.8)

    ax.set_xlabel("Time Index")
    ax.set_ylabel("Max Concentration")
    ax.set_title("Max Concentration Over Time")
    ax.legend(title="Level (m)", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True, alpha=0.3)

    path = os.path.join(output_dir, "max_concentration.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_com_trajectory(df, output_dir, dpi):
    """Scatter + line: center of mass trajectory on a lat-lon map projection."""
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))

    lats = df["com_lat"].values
    lons = df["com_lon"].values

    ax.plot(lons, lats, "o-", color="steelblue", linewidth=2, markersize=6)

    # Annotate first and last points
    if len(lats) > 0:
        ax.annotate(
            "START", (lons[0], lats[0]), color="green",
            fontsize=10, fontweight="bold",
            xytext=(5, 5), textcoords="offset points"
        )
        ax.annotate(
            "END", (lons[-1], lats[-1]), color="red",
            fontsize=10, fontweight="bold",
            xytext=(5, 5), textcoords="offset points"
        )

    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_title("Center of Mass Trajectory")
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    path = os.path.join(output_dir, "com_trajectory.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_vertical_centroid(df, output_dir, dpi):
    """Line plot: vertical centroid height over time."""
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 4))
    times = pd.to_datetime(df["datetime"])

    ax.plot(times, df["vertical_centroid_m"], "o-", color="purple", label="Centroid")

    ax.set_xlabel("Time")
    ax.set_ylabel("Height (m)")
    ax.set_title("Vertical Centroid Over Time")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    path = os.path.join(output_dir, "vertical_centroid.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_plume_spread_area(df, output_dir, dpi):
    """Dual-axis: plume spread (σ) on left axis, plume area on right axis."""
    if df.empty:
        return None

    fig, ax1 = plt.subplots(figsize=(10, 4))

    times = pd.to_datetime(df["datetime"])

    # Left axis: spread
    ax1.plot(times, df["sigma_lat"], "o-", color="blue", label="σ lat", alpha=0.8)
    ax1.plot(times, df["sigma_lon"], "s-", color="green", label="σ lon", alpha=0.8)
    ax1.plot(times, df["sigma_z_m"], "^-", color="orange", label="σ z", alpha=0.8)
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Spread (degrees / m)", color="black")
    ax1.tick_params(axis="y", labelcolor="black")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # Right axis: plume area
    ax2 = ax1.twinx()
    ax2.plot(times, df["plume_area_km2"], "D-", color="red", label="Area (km²)", alpha=0.8)
    ax2.set_ylabel("Plume Area (km²)", color="red")
    ax2.tick_params(axis="y", labelcolor="red")
    ax2.legend(loc="upper right")

    ax1.set_title("Plume Spread and Area Over Time")
    fig.autofmt_xdate()

    path = os.path.join(output_dir, "plume_spread_area.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path
