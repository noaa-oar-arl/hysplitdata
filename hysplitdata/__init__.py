"""
This is HYSPLITDATA, a Python package for reading
HYSPLIT trajectory, concentration, and meteorological
data files.
"""

from .meta import __version__, __author__, __email__

from .meteo.metdata import read_met_file


def read_tdump(fname: str):
    """
    Read a HYSPLIT trajectory dump file
    and return a TrajectoryDump object.
    """
    from .traj.model import TrajectoryDump

    return TrajectoryDump().get_reader().read(fname)


def read_cdump(fname: str):
    """
    Read a HYSPLIT concentration dump file
    and return a ConcentrationDump object.
    """
    from .conc.model import ConcentrationDump

    return ConcentrationDump().get_reader().read(fname)
