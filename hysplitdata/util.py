# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# util.py
#
# Declare a function used by the package.
# ---------------------------------------------------------------------------

import sys


def restore_year(yr):
    return 2000 + yr if (yr < 40) else 1900 + yr


def myzip(xlist, ylist):
    if sys.version_info[0] >= 3:
        # Python 3 or later
        return list(zip(xlist, ylist))
    else:
        # Python 1 and 2
        return zip(xlist, ylist)
