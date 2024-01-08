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

    import hysplitdata.traj.model
    ...
    tdump = hysplitdata.traj.model.TrajectoryDump().get_reader().read("tdump.20190712")

Reading a concentration dump file is done in a similar manner:

    import hysplitdata.conc.model
    ...
    cdump = hysplitdata.conc.model.ConcentrationDump().get_reader().read("cdump.20190712")
