from .meta import __version__, __author__, __email__

from .meteo.metdata import read_met_file

def read_tdump(fname: str):
   from .traj.model import TrajectoryDump
   return TrajectoryDump().get_reader().read(fname)

def read_cdump(fname: str):
   from .conc.model import ConcentrationDump
   return ConcentrationDump().get_reader().read(fname)