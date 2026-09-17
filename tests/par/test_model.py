# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_model.py
#
# Performs unit tests on functions and class methods defined in par/model.py.
# ---------------------------------------------------------------------------

import datetime
import io
import os
import pytest
import pytz
from hysplitdata import util
from hysplitdata.par import model


@pytest.fixture
def utc():
    return pytz.utc


def _make_test_pardump():
    """Create a ParticleDump with known data for roundtrip testing."""
    pardump = model.ParticleDump()
    pardump.year = 2024
    pardump.month = 6
    pardump.day = 15
    pardump.hour = 12
    pardump.minute = 30
    pardump.pollutants_per_particle = 3

    # Particle 0
    p0 = model.Particle()
    p0.pollutant_mass = [1.5e-6, 2.3e-6, 0.0]
    p0.latitude = 39.90
    p0.longitude = -84.22
    p0.altitude = 100.0
    p0.sigmah = 50.0
    p0.sigmaw = 10.0
    p0.sigmav = 5.0
    p0.age = 3.5
    p0.distribution = 1
    p0.pollutant = 0
    p0.meteorgrid = 1
    p0.sort_index = 0

    # Particle 1
    p1 = model.Particle()
    p1.pollutant_mass = [0.0, 5.0e-6, 1.2e-6]
    p1.latitude = 40.10
    p1.longitude = -83.95
    p1.altitude = 250.0
    p1.sigmah = 75.0
    p1.sigmaw = 20.0
    p1.sigmav = 15.0
    p1.age = 7.2
    p1.distribution = 0
    p1.pollutant = 2
    p1.meteorgrid = 2
    p1.sort_index = 5

    pardump.particles = [p0, p1]
    return pardump


# ---- Particle tests ----


def test_Particle___init__():
    p = model.Particle()

    assert p.pollutant_mass == []
    assert p.latitude == 0.0
    assert p.longitude == 0.0
    assert p.altitude == 0.0
    assert p.sigmah == 0.0
    assert p.sigmaw == 0.0
    assert p.sigmav == 0.0
    assert p.age == 0.0
    assert p.distribution == 0
    assert p.pollutant == 0
    assert p.meteorgrid == 1
    assert p.sort_index == 0


def test_Particle_dump():
    p = model.Particle()
    p.latitude = 35.0
    p.longitude = -80.0
    p.age = 2.5
    p.pollutant_mass = [1.0, 2.0]

    stream = io.StringIO()
    p.dump(stream)
    output = stream.getvalue()

    assert "latitude = 35.0" in output
    assert "longitude = -80.0" in output
    assert "age = 2.5" in output


# ---- ParticleDump tests ----


def test_ParticleDump___init__():
    pd = model.ParticleDump()

    assert pd.year == 0
    assert pd.month == 0
    assert pd.day == 0
    assert pd.hour == 0
    assert pd.minute == 0
    assert pd.particles == []
    assert pd.pollutants_per_particle == 0


def test_ParticleDump_datetime(utc):
    pd = model.ParticleDump()
    pd.year = 2024
    pd.month = 6
    pd.day = 15
    pd.hour = 12
    pd.minute = 30

    dt = pd.datetime
    assert dt.year == 2024
    assert dt.month == 6
    assert dt.day == 15
    assert dt.hour == 12
    assert dt.minute == 30
    assert dt.tzinfo == utc


def test_ParticleDump_get_reader():
    pd = model.ParticleDump()
    r = pd.get_reader()

    assert isinstance(r, model.ParticleDumpFileReader)
    assert r.particle_dump is pd


def test_ParticleDump_get_writer():
    pd = model.ParticleDump()
    w = pd.get_writer()

    assert isinstance(w, model.ParticleDumpFileWriter)
    assert w.particle_dump is pd


# ---- FileWriterDecorator tests ----


def test_FileWriterDecorator_write_int4():
    mem = io.BytesIO()
    f = model.FileWriterDecorator(mem)
    f.write_int4(42)
    data = mem.getvalue()
    assert data == b'\x00\x00\x00*'


def test_FileWriterDecorator_write_real4():
    mem = io.BytesIO()
    f = model.FileWriterDecorator(mem)
    f.write_real4(3.14159)
    data = mem.getvalue()
    import struct
    val = struct.unpack('>f', data)[0]
    assert val == pytest.approx(3.14159, rel=1e-5)


def test_FileWriterDecorator_write_record_marker():
    mem = io.BytesIO()
    f = model.FileWriterDecorator(mem)
    f.write_record_marker(100)
    data = mem.getvalue()
    import struct
    val = struct.unpack('>i', data)[0]
    assert val == 100


# ---- Roundtrip test ----


def test_roundtrip_pardump():
    """Write a PARDUMP with known data, read it back, and verify all fields."""
    original = _make_test_pardump()
    test_file = "pardump_roundtrip_test"

    try:
        # Write
        original.get_writer().write(test_file)

        # Read back
        read = model.ParticleDump()
        read.get_reader().read(test_file)

        # Verify header
        assert read.year == original.year
        assert read.month == original.month
        assert read.day == original.day
        assert read.hour == original.hour
        assert read.minute == original.minute
        assert read.pollutants_per_particle == original.pollutants_per_particle
        assert len(read.particles) == len(original.particles)

        # Verify each particle
        for i, (orig_p, read_p) in enumerate(zip(original.particles, read.particles)):
            assert read_p.pollutant_mass == pytest.approx(orig_p.pollutant_mass)
            assert read_p.latitude == pytest.approx(orig_p.latitude)
            assert read_p.longitude == pytest.approx(orig_p.longitude)
            assert read_p.altitude == pytest.approx(orig_p.altitude)
            assert read_p.sigmah == pytest.approx(orig_p.sigmah)
            assert read_p.sigmaw == pytest.approx(orig_p.sigmaw)
            assert read_p.sigmav == pytest.approx(orig_p.sigmav)
            assert read_p.age == pytest.approx(orig_p.age)
            assert read_p.distribution == orig_p.distribution
            assert read_p.pollutant == orig_p.pollutant
            assert read_p.meteorgrid == orig_p.meteorgrid
            assert read_p.sort_index == orig_p.sort_index

    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_roundtrip_empty_particles():
    """Verify reading/writing a PARDUMP with zero particles."""
    pardump = model.ParticleDump()
    pardump.year = 2025
    pardump.month = 1
    pardump.day = 1
    pardump.hour = 0
    pardump.minute = 0
    pardump.pollutants_per_particle = 0
    pardump.particles = []

    test_file = "pardump_empty_test"

    try:
        pardump.get_writer().write(test_file)

        read = model.ParticleDump()
        read.get_reader().read(test_file)

        assert read.year == 2025
        assert read.month == 1
        assert read.day == 1
        assert read.hour == 0
        assert read.minute == 0
        assert read.pollutants_per_particle == 0
        assert len(read.particles) == 0

    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


# ---- Year handling tests ----


def test_year_full_digit_roundtrip():
    """Full 4-digit year should survive roundtrip unchanged."""
    pardump = model.ParticleDump()
    pardump.year = 2024
    pardump.month = 3
    pardump.day = 10
    pardump.hour = 8
    pardump.minute = 15
    pardump.pollutants_per_particle = 0
    pardump.particles = []

    test_file = "pardump_year_full_test"

    try:
        pardump.get_writer().write(test_file)

        read = model.ParticleDump()
        read.get_reader().read(test_file)

        assert read.year == 2024

    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_year_two_digit_handling():
    """Verify that the reader correctly restores 2-digit years."""
    import struct

    test_file = "pardump_year_2digit_test"

    try:
        # Manually write a file with a 2-digit year (24 = 2024)
        with open(test_file, 'wb') as f:
            f.write(struct.pack('>i', 28))
            f.write(struct.pack('>7i', 0, 0, 24, 6, 15, 12, 30))
            f.write(struct.pack('>i', 28))

        read = model.ParticleDump()
        read.get_reader().read(test_file)

        assert read.year == 2024
        assert read.month == 6
        assert read.day == 15

    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


# ---- Single particle test ----


def test_single_particle_roundtrip():
    """Roundtrip with exactly one particle and one pollutant."""
    pardump = model.ParticleDump()
    pardump.year = 2019
    pardump.month = 7
    pardump.day = 12
    pardump.hour = 17
    pardump.minute = 0
    pardump.pollutants_per_particle = 1

    p = model.Particle()
    p.pollutant_mass = [1.0e-5]
    p.latitude = 40.0
    p.longitude = -85.0
    p.altitude = 500.0
    p.sigmah = 100.0
    p.sigmaw = 25.0
    p.sigmav = 10.0
    p.age = 1.5
    p.distribution = 0
    p.pollutant = 0
    p.meteorgrid = 1
    p.sort_index = 0

    pardump.particles = [p]
    test_file = "pardump_single_test"

    try:
        pardump.get_writer().write(test_file)

        read = model.ParticleDump()
        read.get_reader().read(test_file)

        assert len(read.particles) == 1
        rp = read.particles[0]
        assert rp.pollutant_mass == pytest.approx([1.0e-5])
        assert rp.latitude == pytest.approx(40.0)
        assert rp.longitude == pytest.approx(-85.0)
        assert rp.altitude == pytest.approx(500.0)
        assert rp.sigmah == pytest.approx(100.0)
        assert rp.sigmaw == pytest.approx(25.0)
        assert rp.sigmav == pytest.approx(10.0)
        assert rp.age == pytest.approx(1.5)

    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


# ---- Public API test ----


def test_read_pardump_api():
    """Verify the top-level hysplitdata.read_pardump() function works."""
    import hysplitdata

    pardump = _make_test_pardump()
    test_file = "pardump_api_test"

    try:
        pardump.get_writer().write(test_file)

        read = hysplitdata.read_pardump(test_file)

        assert isinstance(read, model.ParticleDump)
        assert len(read.particles) == 2

    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
