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
from struct import unpack_from
import logging
import sys
import os
from pytz import utc


logger = logging.getLogger(__name__)

# Class hierarchy:
#
#    MeteorologicalFile
#       \
#        +-- ForecastFile
#        +-- ArchiveFile
#
#    MeteorologicalFileContent:

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


def _determine_record_len(f: object) -> int:
   f.seek(12)
   cgrid = f.read(2)
   logger.debug(f'cgrid <<{cgrid}>>')

   pos = 50 + 9 + 12*7;
   f.seek(pos)
   buff = f.read(15)
   v = unpack_from('>9s', buff, 0)
   s = v[0].decode('utf-8')
   logger.debug(f'nxyz <<{s}>>')

   nx = int(s[0:3])
   ny = int(s[3:6])
   nz = int(s[6:9])
   if cgrid[0] >= 64:
      nx += (cgrid[0] - 64) * 1000
   if cgrid[1] >= 64:
      ny += (cgrid[1] - 64) * 1000
   logger.debug(f'nx {nx}, ny {ny}, nz {nz}')
   
   v = unpack_from('>4s', buff, 11)
   s = v[0].decode('utf-8')
   logger.debug(f'lenh <<{s}>>')
   lenh = int(s)
   
   lrec = 50 + nx*ny
   logger.debug(f'record length {lrec}, extended header length {lenh}')
   nidx = int(lenh / (lrec - 50)) + 1
   logger.debug(f'INDX takes {nidx} record(s)')
   return (lrec, nidx,)


def _get_datetime_var(f: object) -> tuple:
   pos = f.tell()
   buff = f.read(18)
   logger.debug(f'read {buff} ({len(buff)} bytes) for datetime')
   v = unpack_from('>18s', buff, 0)
   s = v[0].decode('utf-8')
   year = int(s[0:2])
   if year < 40:
       year += 2000
   else:
       year += 1900
   month = int(s[2:4])
   day = int(s[4:6])
   hour = int(s[6:8])
   varname = s[14:18]
   # now the minute part
   if varname == 'INDX':
      f.seek(pos + 50)
      buff = f.read(9)
      logger.debug(f'read {buff} ({len(buff)} bytes) for minute')
      v = unpack_from('>2s', buff, 7)
      s = v[0].decode('utf-8')
      minute = int(s[0:2])
   else:
      minute = 0
   return (datetime(year, month, day, hour, minute, 0, tzinfo=utc), varname,)


def get_met_file(pathname: str) -> MeteorologicalFile:
   o = MeteorologicalFile(pathname)
   
   logger.debug(f'Reading {pathname} ...')
   
   flen = os.path.getsize(pathname)
   with open(pathname, 'rb') as f:
      lrec, nhdr = _determine_record_len(f)
      if flen % lrec != 0:
         logger.error(f'file length {flen} not divisible by record len {lrec}')
      nrec = int(flen / lrec)

      # datetime from the first record which is a INDX record.
      pos = 0
      f.seek(pos)
      start_datetime, var1 = _get_datetime_var(f)
      logger.debug(f'start datetime {start_datetime}')
      pos += lrec * nhdr

      # find the next INDX record and compute the time step size
      for k in range(nhdr, nrec):
         f.seek(pos)
         this_datetime, vark = _get_datetime_var(f)
         if vark == 'INDX':
            dt = this_datetime - start_datetime
            o.time_step = int(dt.total_seconds() / 60)
            logger.debug(f'time_step {o.time_step}')
            pos += lrec * nhdr
            break
         pos += lrec

      # last record
      f.seek(-lrec, 2)
      ending_datetime, var2 = _get_datetime_var(f)
      logger.debug(f'ending datetime {ending_datetime}')
      
      o.start_datetime = start_datetime
      o.ending_datetime = ending_datetime

   return o
