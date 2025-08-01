#!/usr/bin/env python
#
# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# setup.py
#
# For installation of this package.
#
# usage: python setup.py install
# ---------------------------------------------------------------------------

from setuptools import setup
from hysplitdata import meta

setup(
    name="hysplitdata",
    version=meta.__version__,
    description="HYSPLIT Data Model",
    author=meta.__author__,
    author_email=meta.__email__,
    packages=["hysplitdata", "hysplitdata.traj", "hysplitdata.conc",
              "hysplitdata.meteo"],
    python_requires=">=3.9",
    install_requires=["numpy==2.0.2", "pytz==2025.2", "pytest==8.3.5"]
)
