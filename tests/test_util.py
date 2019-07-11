import pytest
from hysplitdata import util


def test_restore_year():
    assert util.restore_year( 0) == 2000
    assert util.restore_year(39) == 2039
    assert util.restore_year(40) == 1940
    assert util.restore_year(99) == 1999

