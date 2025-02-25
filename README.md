# HYSPLITDATA

The HYSPLITDATA package provides Python classes for reading HYSPLIT output files.
The source code is written using Python 3 and the package requires a few external
packages to run: please see setup.py for the required external packages. HYSPLITDATA
is part of a precompiled HYSPLIT distribution. For detailed installation instructions,
refer to https://www.ready.noaa.gov/documents/Tutorial/html/disp_python.html

To upgrade HYSPLITDATA that is already installed along with your HYSPLIT distribution,
first activate the hysplit anaconda environment:

    $ conda activate hysplit

then execute the setup.py script as shown below

    $ python setup.py install

To verify the installation is correctly done, run unit tests. The unit tests for
HYSPLITDATA are written using the pytest framework. pytest is installed when python
packages are installed for HYSPLIT. To run the unit tests, change directory
to the tests subdirectory and run pytest:

    $ cd tests
    $ pytest

No error should have occurred. There may be warning messages but they may be ignored.

To read a trajectory dump file, say, tdump.20190712, in a Python script:

    import hysplitdata
    ...
    tdump = hysplitdata.read_tdump("tdump.20190712")

Reading a concentration dump file is done in a similar manner:

    import hysplitdata
    ...
    cdump = hysplitdata.read_cdump("cdump.20190712")


## Disclaimer
This repository is a scientific product and is not official communication of
the National Oceanic and Atmospheric Administration, or the United States
Department of Commerce. All NOAA GitHub project code is provided on an "as is"
basis and the user assumes responsibility for its use. Any claims against
the Department of Commerce or Department of Commerce bureaus stemming from
the use of this GitHub project will be governed by all applicable Federal law.
Any reference to specific commercial products, processes, or services by service
mark, trademark, manufacturer, or otherwise, does not constitute or imply their
endorsement, recommendation or favoring by the Department of Commerce.
The Department of Commerce seal and logo, or the seal and logo of a DOC bureau,
shall not be used in any manner to imply endorsement of any commercial product
or activity by DOC or the United States Government.
