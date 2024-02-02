# -----------------------------------------------------------------------------
# Air Resources Laboratory
#
# metdata.py - classes for meteorological data contents.
#
# 25 JAN 2024 (SYZ) - Initial.
# -----------------------------------------------------------------------------
from abc import ABC, abstractmethod
from datetime import date, datetime
import io
import logging
import math
import numpy
import os
from pytz import utc


from hysplitdata.meteo.utils import (_determine_record_len)


logger = logging.getLogger(__name__)

# Class hierarchy:
#
#    MeteorologicalFileContent
#    MeteorologicalFileReader


# foreward declaration
class MeteoDataSection: pass


class MeteoSection(ABC):
   
   def __init__(self):
      self.year = 0
      self.month = 0
      self.day = 0
      self.hour = 0
      # note minute is found in MeteoHeader.
      self.ic = 0
      self.vertical_level_index = 0
      self.cgrid = None
      self.kvar = None
      self.exponent = 0
      self.precision = None
      self.first_value = None

   @abstractmethod
   def is_header(self):
      pass

   @property
   @abstractmethod
   def record_identifier(self):
      pass
   
   @abstractmethod
   def dump(self):
      pass


class MeteoHeader(MeteoSection):
   '''
   Usually one INDX section is turned into a MeteoHeader object.
   However, the header information may be spread over two or more
   INDX sections. If this is the case, consecutive INDX sections
   are stitched to yield one MeteoHeader object. 
   '''
   
   def __init__(self):
      super(MeteoHeader,self).__init__()
      
      # variables from the file
      self.model_id = None
      self.icx = 0
      self.minute = 0
      self.pole_lat = None
      self.pole_lon = None
      self.ref_lat = None
      self.ref_lon = None
      self.grid_size = None
      self.orient = None
      self.tang_lat = None
      self.sync_xp = None
      self.sync_yp = None
      self.sync_lat = None
      self.sync_lon = None
      self.dummy = None
      self.nx = 0
      self.ny = 0
      self.nz = 0
      self.z_flag = 0
      self.lenh = 0
   
      # derived
      self.ldat = 0  # byte length of meteorological data (nx*ny)
      self.lrec = 0  # byte length of the record (50 + ldat)
      self.header_record_count = 0  # number of INDX records for the header
      self.header_storage_len = 0  # byte length of the header
      
      self.heights = []  # list of floating-point numbers
      self.data_by_height = []  # list of dict() objects.

   @property
   def record_identifier(self):
      return '{} {:04d}-{:02d}-{:02d} {:02d}:{:02d}'.format(
            self.kvar,
            self.year, self.month, self.day, self.hour, self.minute)

   def is_header(self):
      return True

   def dump(self):
      print(f'{self.kvar} {self.year:04d}-{self.month:02d}-{self.day:02d} '
            f'{self.hour:02d}:{self.minute:02d}z f{self.forecast_hr:02d}')
      print(f'   {self.model_id}, {self.nx}x{self.ny}x{self.nz}, '
            f'grid size {self.grid_size} ')
      for hgt_idx,a in enumerate(self.data_by_height):
         height = self.heights[hgt_idx]
         for var,o in a.items():
            print(f'   {var}, level {height}, chksum {o.checksum}')
            o.dump()

   def collect(self, kvar: str, height: float = None) -> list:
      r = []
      level = None if height is None else self.heights.index(height)
      for hgt_idx,a in enumerate(self.data_by_height):
         if level is None or level == hgt_idx:
            for var,o in a.items():
               if kvar is None or kvar == var:
                  r.append(o)
      return r

   def append_data(self, o: MeteoDataSection) -> None:
      if o is self:
         logger.debug('This is me!')
         return
      # Replace the data section after comparing the checksums.
      q = self.data_by_height[o.vertical_level_index]
      from_header = q[o.kvar].checksum
      # if o.checksum != from_header:
      #    logger.error(f'checksum mismatch: {o.record_identifier}: '
      #                 f'from header {from_header:02x}, computed {o.checksum:02x}')
      o.checksum = from_header
      q[o.kvar] = o

   def add_variable(self, height: float, var: str, chksum: int) -> None:
      if height not in self.heights:
         self.heights.append(height)
         self.data_by_height.append(dict())
      k = self.heights.index(height)
      a = self.data_by_height[k]
      if var in a:
         raise Exception(f'Variable {var} at height {height} already added')
      b = MeteoDataSection(self)
      b.checksum = chksum
      a[var] = b


class MeteoDataSection(MeteoSection):
   
   def __init__(self, header: MeteoHeader):
      super(MeteoDataSection,self).__init__()
      self.header = header
      self.checksum = 0
      self.packed = None  # raw byte array
      self.data = None
      self.__max_value = None
      self.__min_value = None

   @property
   def record_identifier(self):
      return '{} {:04d}-{:02d}-{:02d} {:02d}:{:02d}z height {}'.format(
            self.kvar,
            self.year, self.month, self.day, self.hour, self.header.minute,
            self.header.heights[self.vertical_level_index])

   def is_header(self):
      return False

   def compute_checksum(self, byte_array) -> int:
      return sum(byte_array) & 0x000000ff
      # ksum = 0
      # for b in byte_array:
      #    ksum += b
      #    if ksum >= 256:
      #       ksum -= 255
      # return ksum

   def unpack(self):
      self.data = numpy.zeros((self.header.ny,self.header.nx,), dtype=float)
      c = math.pow(2., self.exponent - 7)
      starter = self.first_value
      for j in range(self.header.ny):
         buf = self.packed[j*self.header.ny:j*self.header.ny+self.header.nx]
         row = self.data[j]
         row[0] = starter + (buf[0]-127)*c
         for k,b in enumerate(buf[1:]):
            row[k+1] = row[k] + (b-127)*c
         starter = row[0]

   def dump(self):
      pass
   
   @property
   def max_value(self):
      if self.__max_value is None:
         if self.data is None:
            self.unpack()
         self.__max_value = numpy.amax(self.data)
      return self.__max_value
   
   @property
   def min_value(self):
      if self.__min_value is None:
         if self.data is None:
            self.unpack()
         self.__min_value = numpy.amin(self.data)
      return self.__min_value


class MeteorologicalFileContent:

   def __init__(self, pathname: str):
      self.pathname = pathname
      self.indices = []  # list of MeteoHeader objects
   
   def add_header(self, sec: MeteoHeader) -> None:
      self.indices.append(sec)

   def dump(self):
      print(f'*** Content of {self.pathname} ***')
      for o in self.indices:
         o.dump()
      print(f'*** End of {self.pathname} ***')

   def collect(self, kvar: str, height: float = None) -> list:
      r = []
      for o in self.indices:
         r += o.collect(kvar, height)
      return r


class MeteorologicalFileReader:

   def __init__(self):
      self.record_byte_len = None
      self.record_count = None
      self.indx_record_count = 1  # number of records for INDX.
      self.last_header = None

   def _continue_reading_header(self, f, o: MeteoHeader) -> None:
      # Already read 50 bytes. Read next 108 bytes
      s = f.read(108).decode('ascii')

      o.model_id = s[0:4]
      o.icx = int(s[4:7])
      o.minute = int(s[7:9])
      o.pole_lat = s[9:16]
      o.pole_lon = s[16:23]
      o.ref_lat = s[23:30]
      o.ref_lon = s[30:37]
      o.grid_size = s[37:44]
      o.orient = s[44:51]
      o.tang_lat = s[51:58]
      o.sync_xp = s[58:65]
      o.sync_yp = s[65:72]
      o.sync_lat = s[72:79]
      o.sync_lon = s[79:86]
      o.dummy = s[86:93]
      o.nx = int(s[93:96])
      o.ny = int(s[96:99])
      o.nz = int(s[99:102])
      o.z_flag = int(s[102:104])
      o.lenh = int(s[104:108])
   
      if ord(o.cgrid[0]) >= 64 or ord(o.cgrid[1]) >= 64:
         o.nx += (ord(o.cgrid[0]) - 64) * 1000;
         o.ny += (ord(o.cgrid[1]) - 64) * 1000;
   
      o.ldat = o.nx * o.ny;
      o.lrec = 50 + o.ldat;
   
      o.header_record_count = int(o.lenh / o.ldat) + 1;
      o.header_storage_len = o.header_record_count * o.lrec;

      # So far we read 50 + 108 = 158 bytes
      s = f.read(o.lrec - 158).decode('ascii')
      for k in range(o.header_record_count-1):
         f.seek(50, os.SEEK_CUR)  # skip 50 bytes
         s += f.read(o.lrec - 50).decode('ascii')
      
      ss = io.StringIO(s)
      for k in range(o.nz):
         height = float(ss.read(6))
         npar = int(ss.read(2))
         for m in range(npar):
            par = ss.read(4)
            checksum = int(ss.read(3))
            ss.read(1)
            logger.debug(f'level {height}, var {par}, checksum {checksum}')
            o.add_variable(height, par, checksum)

   def _continue_reading_data(self, f, o: MeteoDataSection) -> None:
      # Already read 50 bytes.
      o.packed = f.read(self.record_byte_len)
      o.checksum = o.compute_checksum(o.packed)

   def _read_section(self, f) -> tuple:
      '''
      Return a section object and the number of bytes read.
      '''
      
      # First 50 bytes
      s = f.read(50).decode('ascii')

      kvar = s[14:18]
      if kvar == 'INDX':
         o = MeteoHeader()
         self.last_header = o
      else:
         o = MeteoDataSection(self.last_header)

      o.year = int(s[0:2])
      o.year += 2000 if o.year < 40 else 1900
      o.month = int(s[2:4])
      o.day = int(s[4:6])
      o.hour = int(s[6:8])
      o.forecast_hr = int(s[8:10])
      o.vertical_level_index = int(s[10:12])
      o.cgrid = s[12:14]
      o.kvar = s[14:18]
      o.exponent = int(s[18:22])
      o.precision = float(s[22:36])
      o.first_value = float(s[36:50])

      logger.debug(f'Reading {o.kvar} {o.vertical_level_index} '
                   f'{o.year:04d}-{o.month:02d}-{o.day:02d} '
                   f'{o.hour:02d}z f{o.forecast_hr:02d}')
      if o.kvar == 'INDX':
         bytes_read = self.record_byte_len * self.indx_record_count
         self._continue_reading_header(f, o)
      else:
         bytes_read = self.record_byte_len
         self._continue_reading_data(f, o)

      return (o, bytes_read,)

   def load(self, pathname: str) -> MeteorologicalFileContent:
      '''
      Read a meteorological file in its entirety.
      '''
      o = MeteorologicalFileContent(pathname)

      logger.debug(f'Reading {pathname} ...')
      
      flen = os.path.getsize(pathname)
      with open(pathname, 'rb') as f:
         lrec, nhdr = _determine_record_len(f)
         if flen % lrec != 0:
            logger.error(f'file length {flen} not divisible by record len {lrec}')
         self.record_byte_len = lrec
         self.indx_record_count = nhdr
         self.record_count = int(flen / lrec)
   
         # loop over each record
         pos = 0
         while pos < flen:
            f.seek(pos)
            sec, bytes_read = self._read_section(f)
            if sec.is_header():
               o.add_header(sec)
            else:
               self.last_header.append_data(sec)
            pos += bytes_read

      return o

   @staticmethod
   def read(pathname: str) -> MeteorologicalFileContent:
      return MeteorologicalFileReader().load(pathname)
 

def read_met_file(pathname: str) -> MeteorologicalFileContent:
   return MeteorologicalFileReader.read(pathname)