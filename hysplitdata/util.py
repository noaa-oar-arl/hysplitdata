# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# util.py
#
# Declare a function used by the package.
# ---------------------------------------------------------------------------


def restore_year(yr):
    return 2000 + yr if (yr < 40) else 1900 + yr
