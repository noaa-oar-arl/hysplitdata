# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_util.py
#
# Performs unit tests on functions and class methods defined in util.py.
# ---------------------------------------------------------------------------

import pytest
from hysplitdata import util


def test_restore_year():
    assert util.restore_year( 0) == 2000
    assert util.restore_year(39) == 2039
    assert util.restore_year(40) == 1940
    assert util.restore_year(99) == 1999


def test_myzip():
    a = util.myzip([1, 2], [3, 4])

    assert len(a) == 2
    assert a[0] == (1, 3)
    assert a[1] == (2, 4)
