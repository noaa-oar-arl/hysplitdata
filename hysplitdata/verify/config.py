"""Configuration for HYSPLIT concentration dump verification."""

from typing import Optional, List


class VerificationConfig:
    """Configuration parameters for concentration dump verification.

    Attributes:
        initial_mass: Initial released mass in grams (or particle count for SUM).
        output_dir: Directory for output files (CSVs, plots, report).
        particle_mass_g: Mass per particle in grams, for SUM pollutant conversion.
        conservation_tolerance_pct: Alert threshold for conservation residual (%).
        plot_dpi: Resolution for generated plots.
        include_pollutants: Specific pollutants to analyze; None means all.
        cdump_path: Path to the analyzed cdump file (for report header).
    """

    def __init__(
        self,
        initial_mass: float,
        output_dir: str = "./verification_output",
        particle_mass_g: Optional[float] = None,
        conservation_tolerance_pct: float = 0.1,
        plot_dpi: int = 150,
        include_pollutants: Optional[List[str]] = None,
        cdump_path: str = "unknown",
    ):
        if initial_mass <= 0:
            raise ValueError(f"initial_mass must be positive, got {initial_mass}")
        if conservation_tolerance_pct < 0:
            raise ValueError(
                f"conservation_tolerance_pct must be non-negative, "
                f"got {conservation_tolerance_pct}"
            )
        self.initial_mass = initial_mass
        self.output_dir = output_dir
        self.particle_mass_g = particle_mass_g
        self.conservation_tolerance_pct = conservation_tolerance_pct
        self.plot_dpi = plot_dpi
        self.include_pollutants = include_pollutants
        self.cdump_path = cdump_path
