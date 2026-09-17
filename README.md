# HYSPLITDATA

The HYSPLITDATA package provides Python classes for reading HYSPLIT output files.
The source code is written using Python 3 and the package requires a few external
packages to run: please see setup.py for the required external packages. HYSPLITDATA
is part of a precompiled HYSPLIT distribution. For detailed installation instructions,
refer to https://www.ready.noaa.gov/documents/Tutorial/html/disp_python.html

To upgrade HYSPLITDATA that is already installed along with your HYSPLIT distribution,
first activate the hysplit anaconda environment:

    $ conda activate hysplit

then execute the setup.py script as shown below

    $ python setup.py install

To verify the installation is correctly done, run unit tests. The unit tests for
HYSPLITDATA are written using the pytest framework. pytest is installed when python
packages are installed for HYSPLIT. To run the unit tests, change directory
to the tests subdirectory and run pytest:

    $ cd tests
    $ pytest

No error should have occurred. There may be warning messages but they may be ignored.

To read a trajectory dump file, say, tdump.20190712, in a Python script:

    import hysplitdata
    ...
    tdump = hysplitdata.read_tdump("tdump.20190712")

Reading a concentration dump file is done in a similar manner:

    import hysplitdata
    ...
    cdump = hysplitdata.read_cdump("cdump.20190712")

Reading a particle dump file (PARDUMP) provides per-particle tracking data
including pollutant masses, spatial coordinates, and deposition sigmas:

    import hysplitdata
    ...
    pardump = hysplitdata.read_pardump("pardump.20240101")
    for p in pardump.particles:
        print(p.latitude, p.longitude, p.altitude, p.pollutant_mass)


## Verification Module

The `hysplitdata.verify` submodule provides a toolkit for verifying HYSPLIT
concentration dump files (cdump). It computes mass conservation diagnostics,
plume integrity checks, and temporal plume dynamics.

### Installation

The verify module requires optional dependencies. Install them with:

    $ pip install hysplitdata[verify]

Or install from requirements.txt:

    $ pip install -r requirements.txt

### Programmatic Usage

```python
import hysplitdata
from hysplitdata.verify import VerificationConfig, VerificationRunner

# Read a concentration dump file
cdump = hysplitdata.read_cdump("cdump.20240101")

# Configure verification parameters
config = VerificationConfig(
    initial_mass=1000.0,            # grams (or particle count for SUM)
    output_dir="./verification_output",
    conservation_tolerance_pct=0.1, # alert threshold in %
    plot_dpi=150,
)

# Run the full verification pipeline
runner = VerificationRunner(cdump, config)
results = runner.run()

# Access results
print(results.mass_balance)        # DataFrame: per-time-step mass balance
print(results.plume_integrity)     # DataFrame: negative cells, coverage, etc.
print(results.plume_dynamics)      # DataFrame: center of mass, spread, etc.
print(results.report)              # Markdown summary report string
```

### Command-Line Usage

A CLI script is provided at `examples/verify_cdump.py`:

    $ python examples/verify_cdump.py --initial-mass 1000 cdump.20240101
    $ python examples/verify_cdump.py --initial-mass 1000 --output-dir ./out --pollutant TEST cdump.20240101

Options:
- `--initial-mass` — Required. Initial released mass in grams.
- `--particle-mass` — Mass per particle in grams (for SUM pollutant).
- `--output-dir` — Output directory for CSVs, plots, and report.
- `--tolerance` — Conservation residual tolerance in percent (default 0.1).
- `--pollutant` — Filter to a specific pollutant.
- `--no-plots` — Skip plot generation.
- `--dpi` — Plot resolution in DPI (default 150).

### What It Computes

1. **Mass Balance** — Airborne and deposited mass per time step, conservation residual.
2. **Plume Integrity** — Negative concentration cells, grid coverage, max concentration location.
3. **Plume Dynamics** — Horizontal/vertical center of mass, spread (σ), plume area.
4. **Visualization** — 9 matplotlib-based plots covering all diagnostics above.
5. **Report** — Markdown summary with PASS/FAIL conservation status.

### Limitations

- Level 0 gives total deposited mass; per-particle mass tracking requires PARDUMP.
- Inferred deposition mode (when no level-0 grids) conflates all sinks.
- Top layer thickness is estimated as 2× spacing.
- The "SUM" pollutant needs `particle_mass_g` for mass conversion.

## Disclaimer
This repository is a scientific product and is not official communication of
the National Oceanic and Atmospheric Administration, or the United States
Department of Commerce. All NOAA GitHub project code is provided on an "as is"
basis and the user assumes responsibility for its use. Any claims against
the Department of Commerce or Department of Commerce bureaus stemming from
the use of this GitHub project will be governed by all applicable Federal law.
Any reference to specific commercial products, processes, or services by service
mark, trademark, manufacturer, or otherwise, does not constitute or imply their
endorsement, recommendation or favoring by the Department of Commerce.
The Department of Commerce seal and logo, or the seal and logo of a DOC bureau,
shall not be used in any manner to imply endorsement of any commercial product
or activity by DOC or the United States Government.
