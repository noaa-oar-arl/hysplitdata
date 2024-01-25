# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_metfile.py
#
# Performs unit tests on the functions and the class methods in metfile.py
#
# Last update: 22 MAR 2023
# ---------------------------------------------------------------------------

from datetime import date, datetime
import logging
import os
import pytest
from pytz import utc

from hysplitdata.meteo.metfile import (
   ArchiveFile,
   ForecastFile,
   get_met_file,
   MeteorologicalFile,
)


logger = logging.getLogger(__name__)


def test_MeteorologicalFile___init__():
    t1 = datetime(2021, 1, 27, 0, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 27, 6, 0, tzinfo=utc)
    o = MeteorologicalFile('/data/hysplit.t00z.foo', t1, t2)
    assert o.pathname == '/data/hysplit.t00z.foo'
    assert o.start_datetime == t1
    assert o.ending_datetime == t2
    assert o.time_step == 180


def test_MeteorologicalFile___eq__():
    # o1 produced at 0z
    fd = date(2021, 1, 27)
    t1 = datetime(2021, 1, 27, 0, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 27, 6, 0, tzinfo=utc)
    o1 = MeteorologicalFile('/data/hysplit.t00z.foo', t1, t2)
    # o2 produced at 6z
    fd = date(2021, 1, 27)
    t1 = datetime(2021, 1, 27,  6, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 27, 12, 0, tzinfo=utc)
    o2 = MeteorologicalFile('/data/hysplit.t06z.foo', t1, t2)
    # tests
    assert o1 == o1
    assert o1 is not o2
    assert not (o1 == None)


def test_MeteorologicalFile___str__():
    # o1 produced at 0z
    fd = date(2021, 1, 27)
    t1 = datetime(2021, 1, 27, 0, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 27, 6, 0, tzinfo=utc)
    o1 = MeteorologicalFile('/data/hysplit.t00z.foo', t1, t2)
    # test
    assert str(o1) == '/data/hysplit.t00z.foo'


def test_MeteorologicalFile_directory():
    t1 = datetime(2021, 1, 27, 0, 0, tzinfo=utc)
    t2 = datetime(2021, 2,  3, 0, 0, tzinfo=utc)
    o = MeteorologicalFile('/pub/forecast/20210128/hysplit.t00z.foo', t1, t2)
    # test
    assert o.directory == '/pub/forecast/20210128'


def test_MeteorologicalFile_filename():
    t1 = datetime(2021, 1, 27, 0, 0, tzinfo=utc)
    t2 = datetime(2021, 2,  3, 0, 0, tzinfo=utc)
    o = MeteorologicalFile('/pub/forecast/20210128/hysplit.t00z.foo', t1, t2)
    # test
    assert o.filename == 'hysplit.t00z.foo'


def test_MeteorologicalFile_encompass_range():
    t1 = datetime(2021, 1, 27, 0, 0, tzinfo=utc)
    t2 = datetime(2021, 2,  3, 0, 0, tzinfo=utc)
    o = MeteorologicalFile('/data/hysplit.t00z.foo', t1, t2)
    # no overlap
    r = (datetime(2021, 1, 26, 18, 0, tzinfo=utc),
         datetime(2021, 1, 27,  0, 0, tzinfo=utc))
    assert o.encompass_range(r) == False
    # partial overlap
    r = (datetime(2021, 1, 26, 18, 0, tzinfo=utc),
         datetime(2021, 1, 27,  6, 0, tzinfo=utc))
    assert o.encompass_range(r) == False
    # arg is completely inside the file time range.
    r = (datetime(2021, 1, 27,  0, 0, tzinfo=utc),
         datetime(2021, 1, 27,  6, 0, tzinfo=utc))
    assert o.encompass_range(r) == True
    r = (datetime(2021, 2,  2, 18, 0, tzinfo=utc),
         datetime(2021, 2,  3,  0, 0, tzinfo=utc))
    assert o.encompass_range(r) == True
    # no overlap
    r = (datetime(2021, 2,  2, 18, 0, tzinfo=utc),
         datetime(2021, 2,  3,  6, 0, tzinfo=utc))
    assert o.encompass_range(r) == False


def test_ForecastFile___init__():
    fd = date(2021, 1, 27)
    t1 = datetime(2021, 1, 27, 0, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 27, 6, 0, tzinfo=utc)
    o = ForecastFile('/data/hysplit.t00z.foo', fd, 0, t1, t2,
                     preference=1, time_step=360)
    assert o.pathname == '/data/hysplit.t00z.foo'
    assert o.forecast_date == fd
    assert o.cycle == 0
    assert o.start_datetime == t1
    assert o.ending_datetime == t2
    assert o.preference == 1
    assert o.time_step == 360


def test_ForecastFile_compare_priority():
    # o1 produced at 0z
    fd = date(2021, 1, 27)
    t1 = datetime(2021, 1, 27, 0, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 27, 6, 0, tzinfo=utc)
    o1 = ForecastFile('/data/hysplit.t00z.foo', fd, 0, t1, t2)
    # o2 produced at 6z
    fd = date(2021, 1, 27)
    t1 = datetime(2021, 1, 27,  6, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 27, 12, 0, tzinfo=utc)
    o2 = ForecastFile('/data/hysplit.t06z.foo', fd, 6, t1, t2)
    # o3 produced at 6z but on 1/26.
    fd = date(2021, 1, 26)
    t1 = datetime(2021, 1, 26,  6, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 26, 12, 0, tzinfo=utc)
    o3 = ForecastFile('/data/hysplit.t06z.foo', fd, 6, t1, t2)
    # tests
    ForecastFile.compare_priority(o1, o2) == -1
    ForecastFile.compare_priority(o2, o1) ==  1
    ForecastFile.compare_priority(o1, o1) ==  0
    ForecastFile.compare_priority(o2, o2) ==  0
    ForecastFile.compare_priority(o3, o2) == -1
    ForecastFile.compare_priority(o2, o3) ==  1
    # create o4 that is the same as o3 except for a higher preference
    o4 = ForecastFile('/data/hysplit.t06z.foo', fd, 6, t1, t2,
                      preference=1)
    ForecastFile.compare_priority(o3, o4) == -1
    ForecastFile.compare_priority(o4, o3) ==  1
    ForecastFile.compare_priority(o4, o4) ==  0


def test_ArchiveFile___init__():
    t1 = datetime(2021, 1, 27, 0, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 27, 6, 0, tzinfo=utc)
    o = ArchiveFile('/data/hysplit.t00z.foo', t1, t2, time_step=360)
    assert o.pathname == '/data/hysplit.t00z.foo'
    assert o.start_datetime == t1
    assert o.ending_datetime == t2
    assert o.time_step == 360


def test_ArchiveFile_compare_priority():
    # o1 produced at 0z
    t1 = datetime(2021, 1, 27, 0, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 27, 6, 0, tzinfo=utc)
    o1 = ArchiveFile('/data/hysplit.t00z.foo', t1, t2)
    # o2 produced at 6z
    t1 = datetime(2021, 1, 27,  6, 0, tzinfo=utc)
    t2 = datetime(2021, 1, 27, 12, 0, tzinfo=utc)
    o2 = ArchiveFile('/data/hysplit.t06z.foo', t1, t2)
    # tests
    ArchiveFile.compare_priority(o1, o2) == -1
    ArchiveFile.compare_priority(o2, o1) ==  1
    ArchiveFile.compare_priority(o1, o1) ==  0
    ArchiveFile.compare_priority(o2, o2) ==  0


def test_get_met_file():
   o = get_met_file('../data/oct1618.BIN')
   assert o.pathname == '../data/oct1618.BIN'
   assert o.start_datetime == datetime(1995,10,16,0,0,0,tzinfo=utc)
   assert o.ending_datetime == datetime(1995,10,18,22,0,0,tzinfo=utc)
   assert o.time_step == 120
   
   
   
   