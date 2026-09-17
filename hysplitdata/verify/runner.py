"""Orchestrates the full verification pipeline."""

import logging
import os
from typing import TYPE_CHECKING, Optional, List, Dict

if TYPE_CHECKING:
    import pandas as pd

from .config import VerificationConfig
from .geometry import compute_cell_areas, compute_layer_thicknesses
from .mass_balance import compute_mass_balance
from .plume_integrity import compute_plume_integrity
from .plume_dynamics import compute_plume_dynamics
from .report import generate_report

logger = logging.getLogger(__name__)


class VerificationResults:
    """Container for all verification outputs.

    Attributes:
        mass_balance: DataFrame with per-time-step mass balance.
        mass_by_level: DataFrame with per-level mass breakdown.
        plume_integrity: DataFrame with plume integrity metrics.
        plume_dynamics: DataFrame with plume dynamics metrics.
        plots: Dict mapping plot name to file path.
        report: Markdown summary report string.
        warnings: List of warning messages.
    """

    def __init__(
        self,
        mass_balance,
        mass_by_level,
        plume_integrity,
        plume_dynamics,
        plots=None,
        report="",
        warnings=None,
    ):
        self.mass_balance = mass_balance
        self.mass_by_level = mass_by_level
        self.plume_integrity = plume_integrity
        self.plume_dynamics = plume_dynamics
        self.plots = plots if plots is not None else {}
        self.report = report
        self.warnings = warnings if warnings is not None else []


class VerificationRunner:
    """Runs the full verification pipeline on a concentration dump."""

    def __init__(self, cdump, config: VerificationConfig):
        """
        Args:
            cdump: ConcentrationDump object from hysplitdata.read_cdump().
            config: VerificationConfig with parameters.
        """
        self.cdump = cdump
        self.config = config
        self.cell_areas = compute_cell_areas(
            cdump.longitudes, cdump.latitudes, cdump.grid_deltas
        )
        self.layer_thicknesses = compute_layer_thicknesses(cdump.vert_levels)

    def run(self) -> VerificationResults:
        """Execute all verification steps and return results."""
        logger.info("Starting verification with initial_mass = %s", self.config.initial_mass)
        all_warnings = []

        # Phase 1: Mass balance
        logger.info("Computing mass balance...")
        balance_rows, level_rows, warnings = compute_mass_balance(
            self.cdump, self.config,
            cell_areas=self.cell_areas,
            layer_thicknesses=self.layer_thicknesses,
        )
        all_warnings.extend(warnings)

        # Phase 2: Plume integrity
        logger.info("Computing plume integrity...")
        integrity_rows, integrity_warnings = compute_plume_integrity(
            self.cdump, self.config, cell_areas=self.cell_areas
        )
        all_warnings.extend(integrity_warnings)

        # Phase 3: Plume dynamics
        logger.info("Computing plume dynamics...")
        dynamics_rows, dynamics_warnings = compute_plume_dynamics(
            self.cdump, self.config, cell_areas=self.cell_areas
        )
        all_warnings.extend(dynamics_warnings)

        # Assemble results
        try:
            import pandas as pd
        except ImportError as e:
            logger.error("pandas is required for verification results: %s", e)
            raise

        mb_df = pd.DataFrame(balance_rows)
        lv_df = pd.DataFrame(level_rows)
        pi_df = pd.DataFrame(integrity_rows)
        pd_df = pd.DataFrame(dynamics_rows)

        results = VerificationResults(
            mass_balance=mb_df,
            mass_by_level=lv_df,
            plume_integrity=pi_df,
            plume_dynamics=pd_df,
            warnings=all_warnings,
        )

        # Emit warnings
        for w in all_warnings:
            logger.warning(w)

        # Write CSVs
        if self.config.output_dir:
            os.makedirs(self.config.output_dir, exist_ok=True)
            self._write_csv(results, "mass_balance.csv", "mass_balance")
            self._write_csv(results, "mass_by_level.csv", "mass_by_level")
            self._write_csv(results, "plume_integrity.csv", "plume_integrity")
            self._write_csv(results, "plume_dynamics.csv", "plume_dynamics")
            logger.info("CSV results written to %s", self.config.output_dir)

        # Phase 4: Plots
        logger.info("Generating plots...")
        try:
            from .plots import generate_all_plots

            results.plots = generate_all_plots(
                results, self.config.output_dir, dpi=self.config.plot_dpi
            )
            logger.info("Plots written to %s", self.config.output_dir)
        except ImportError as e:
            logger.warning("Plot generation skipped (missing dependency): %s", e)
        except Exception as e:
            logger.warning("Plot generation failed: %s", e)

        # Phase 4b: Report
        logger.info("Generating report...")
        results.report = generate_report(
            results, self.config, cdump_path=self.config.cdump_path)
        if self.config.output_dir:
            report_path = os.path.join(self.config.output_dir, "verification_report.md")
            with open(report_path, "w") as f:
                f.write(results.report)
            logger.info("Report written to %s", report_path)

        return results

    def _write_csv(self, results, filename, attr_name):
        df = getattr(results, attr_name)
        path = os.path.join(self.config.output_dir, filename)
        df.to_csv(path, index=False)
