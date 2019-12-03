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

setup(
    name="hysplitdata",
    version="0.0.1",
    description="HYSPLIT Data Model",
    author="Sonny Zinn",
    author_email="sonny.zinn@noaa.gov",
    packages=["hysplitdata", "hysplitdata.traj", "hysplitdata.conc"],
    python_requires="==3.7",
    install_requires=['numpy==1.16', "pytz==2019.1"]
)
