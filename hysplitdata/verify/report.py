"""Markdown report generation for HYSPLIT verification results."""

import datetime
import os
from typing import List

# Friendly titles for each plot key
_PLOT_TITLES = {
    "mass_time_series":       "Mass Time Series",
    "mass_by_altitude":       "Mass by Altitude",
    "conservation_residual":  "Conservation Residual",
    "negative_cells":         "Negative Concentration Cells",
    "grid_coverage":          "Grid Coverage",
    "max_concentration":      "Maximum Concentration",
    "com_trajectory":         "Center-of-Mass Trajectory",
    "vertical_centroid":      "Vertical Centroid",
    "plume_spread_area":      "Plume Spread & Area",
}


def _relative_plot_path(plot_path, output_dir):
    """Return a relative path suitable for markdown links in the report.

    If plot_path is absolute and output_dir is set, compute the relative
    portion so that the report works when opened from the output directory.
    """
    if not plot_path or not output_dir:
        return plot_path
    try:
        return os.path.relpath(plot_path, output_dir)
    except ValueError:
        # On Windows, relpath can fail for paths on different drives
        return os.path.basename(plot_path)


def generate_report(results, config, cdump_path="unknown"):
    """Generate a markdown summary report from verification results.

    Args:
        results: VerificationResults object.
        config: VerificationConfig.
        cdump_path: Path to the analyzed cdump file.

    Returns:
        Markdown string.
    """
    mb = results.mass_balance
    lv = results.mass_by_level
    output_dir = config.output_dir

    lines = []
    lines.append("# HYSPLIT Verification Report")
    lines.append("")
    lines.append(f"File: {cdump_path}")
    lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Configuration
    lines.append("## Configuration")
    lines.append(f"- Initial mass: {config.initial_mass:.4f}")
    dep_mode = "inferred"
    if not mb.empty:
        dep_mode = mb.iloc[0].get("deposition_mode", "inferred")
    lines.append(f"- Deposition mode: {dep_mode}")
    lines.append(f"- Conservation tolerance: {config.conservation_tolerance_pct}%")
    if config.particle_mass_g is not None:
        lines.append(f"- Particle mass: {config.particle_mass_g} g")
    if config.include_pollutants:
        lines.append(f"- Pollutants analyzed: {', '.join(config.include_pollutants)}")
    lines.append("")

    # Mass Conservation
    lines.append("## Mass Conservation")
    if not mb.empty:
        final = mb.iloc[-1]
        lines.append(f"- Final airborne mass: {final['total_airborne_mass']:.4f}")
        lines.append(f"  ({final['airborne_fraction']*100:.1f}% of initial)")
        lines.append(f"- Final deposited mass: {final['total_deposited_mass']:.4f}")
        lines.append(f"  ({final['deposited_fraction']*100:.1f}% of initial)")

        max_residual = float(mb["conservation_residual_pct"].abs().max())
        status = "PASS" if max_residual <= config.conservation_tolerance_pct else "FAIL"
        lines.append(f"- Max conservation residual: {max_residual:.4f}% ({status})")

        # Monotonic checks
        # Use relative tolerance based on the magnitude of the values to
        # account for floating-point accumulation errors in mass balance.
        tol = 1e-6
        airborne_frac = mb["airborne_fraction"].values
        airborne_monotonic = all(
            airborne_frac[i] >= airborne_frac[i + 1] - tol
            for i in range(len(airborne_frac) - 1)
        )
        status_a = "PASS" if airborne_monotonic else "FAIL"
        lines.append(f"- Airborne fraction monotonic decrease: {status_a}")

        dep_frac = mb["deposited_fraction"].values
        dep_monotonic = all(
            dep_frac[i] <= dep_frac[i + 1] + tol
            for i in range(len(dep_frac) - 1)
        )
        status_d = "PASS" if dep_monotonic else "FAIL"
        lines.append(f"- Deposited fraction monotonic increase: {status_d}")
    else:
        lines.append("- No data available")
    lines.append("")

    # Plots section (only when plots were generated)
    if results.plots:
        lines.append("## Plots")
        lines.append("")
        for key in _PLOT_TITLES:
            plot_path = results.plots.get(key)
            if plot_path and os.path.exists(plot_path):
                rel = _relative_plot_path(plot_path, output_dir)
                title = _PLOT_TITLES[key]
                lines.append(f"- ![{title}]({rel})")
        lines.append("")

    # Warnings
    lines.append("## Warnings")
    if results.warnings:
        for w in results.warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- (none)")
    lines.append("")

    return "\n".join(lines)
