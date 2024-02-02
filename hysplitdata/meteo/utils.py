# -----------------------------------------------------------------------------
# Air Resources Laboratory
#
# utils.py - utilities for reading a meteorological data file.
#
# 25 JAN 2024 (SYZ) - Initial.
# -----------------------------------------------------------------------------
from abc import ABC
from datetime import date, datetime
from struct import unpack_from
import logging
# import sys
import os
from pytz import utc


logger = logging.getLogger(__name__)


def _determine_record_len(f: object) -> tuple:
   '''
   For a given file object that is open for reading a meteorological
   file, determine the record length in bytes and the number of records
   that are required to constitute an INDX. Note that an INDX may consists
   of one or more records.
   '''
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
   '''
   Read a record and return its datetime and variable name it represents.
   '''
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


def get_temporal_coverage(pathname: str) -> tuple:
   '''
   Return the start time, the ending time, and the record interval
   in minutes.
   '''
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
            time_step = int(dt.total_seconds() / 60)
            logger.debug(f'time_step {time_step}')
            pos += lrec * nhdr
            break
         pos += lrec

      # last record
      f.seek(-lrec, 2)
      ending_datetime, var2 = _get_datetime_var(f)
      logger.debug(f'ending datetime {ending_datetime}')

   return (start_datetime, ending_datetime, time_step,)
