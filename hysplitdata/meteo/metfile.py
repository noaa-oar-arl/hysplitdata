# -----------------------------------------------------------------------------
# Air Resources Laboratory
#
# metfile.py - classes for meteorological data files.
#
# 07 MAR 2023 (SYZ) - Initial.
# 08 MAR 2023 (SYZ) - Read the minute part from INDX records
# 16 MAR 2023 (SYZ) - Correctly handle extended headers
# 22 MAR 2023 (SYZ) - Move ArchiveFile and ForecastFile classes to here.
# -----------------------------------------------------------------------------
from abc import ABC
from datetime import date, datetime
import logging
import os
from pytz import utc

from .utils import get_temporal_coverage

logger = logging.getLogger(__name__)

# Class hierarchy:
#
#    MeteorologicalFile
#       \
#        +-- ForecastFile
#        +-- ArchiveFile
#

class MeteorologicalFile(ABC):
    """
    Meteorological file just with the pathname, the start time,
    and the ending time. These are used when checking if a HYSPLIT
    run has enough meteorological data coverage.
    """

    def __init__(self,
                 pathname : str,
                 start_datetime : datetime = None,
                 ending_datetime : datetime = None,
                 time_step : int = 3*60):
        self.pathname = pathname
        self.start_datetime = start_datetime
        self.ending_datetime = ending_datetime
        self.time_step = time_step  # time step in minutes

    def __eq__(self, o):
        return o is not None and self.pathname == o.pathname

    def __str__(self):
        return self.pathname  # for backward compatibility

    @property
    def directory(self):
        return os.path.dirname(self.pathname)

    @property
    def filename(self):
        return os.path.basename(self.pathname)

    def encompass_range(self,
                        datetime_range : tuple) -> bool:
        """
        Test if the file completely encompasses the given time range.
        """
        l, u = datetime_range
        if l > u:
            l, u = u, l

        if self.start_datetime <= l and u <= self.ending_datetime:
            return True
        return False


class ForecastFile(MeteorologicalFile):
    """
    Represents a forecast file.
    Additional properties like forecast date and forecast cycle are added.
    """
    def __init__(self,
                 pathname : str,
                 forecast_date : date,
                 cycle : int,
                 start_datetime : datetime,
                 ending_datetime : datetime,
                 preference : int = 0,
                 time_step : int = 3*60):
        super(ForecastFile, self).__init__(pathname,
                                           start_datetime,
                                           ending_datetime,
                                           time_step=time_step)
        self.forecast_date = forecast_date
        self.cycle = cycle
        self.preference = preference  # the larger, the more preferred
        # For now we are using:
        #
        # 0   - forecast files
        # 1   - archive files

    @staticmethod
    def compare_priority(a, b):
        """
        Compare two forecast files to determine the priority for selection.
        """
        if a.forecast_date < b.forecast_date:
            return -1
        elif a.forecast_date > b.forecast_date:
            return 1
        # when both forecast files were produced on the same date.
        if a.cycle < b.cycle:
            return -1
        elif a.cycle > b.cycle:
            return 1
        return a.preference - b.preference


class ArchiveFile(MeteorologicalFile):
    """
    Represents an archive file.
    """

    def __init__(self,
                 pathname : str,
                 start_datetime : datetime,
                 ending_datetime : datetime,
                 time_step : int = 3*60):
        super(ArchiveFile, self).__init__(pathname,
                                          start_datetime,
                                          ending_datetime,
                                          time_step=time_step)

    @staticmethod
    def compare_priority(a, b):
        if a.ending_datetime < b.ending_datetime:
            return -1
        elif a.ending_datetime > b.ending_datetime:
            return 1
        return 0


def get_met_file(pathname: str) -> MeteorologicalFile:
   start_time, ending_time, step = get_temporal_coverage(pathname)
   
   o = MeteorologicalFile(pathname)
   o.start_datetime = start_time
   o.ending_datetime = ending_time
   o.time_step = step
   
   return o
