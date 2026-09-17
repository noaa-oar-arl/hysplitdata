# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# model.py
#
# Declares classes representing a particle dump (PARDUMP) and its particles.
# A reader and writer for a particle dump file are included.
# ---------------------------------------------------------------------------

import datetime
import logging
import struct
import pytz

from hysplitdata import util


logger = logging.getLogger(__name__)


class Particle:
    """Represents a single particle from a PARDUMP file.
    """

    def __init__(self):
        self.pollutant_mass = []    # list[float] — mass per pollutant
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude = 0.0
        self.sigmah = 0.0           # horizontal dispersion sigma (m)
        self.sigmaw = 0.0           # w-component turbulence sigma (m/s)
        self.sigmav = 0.0           # v-component turbulence sigma (m/s)
        self.age = 0.0              # float
        self.distribution = 0       # int
        self.pollutant = 0          # int
        self.meteorgrid = 1         # int (default 1)
        self.sort_index = 0         # int

    def dump(self, stream):
        """Write debug output of particle fields to stream."""
        stream.write("  pollutant_mass = {}\n".format(self.pollutant_mass))
        stream.write("  latitude = {}\n".format(self.latitude))
        stream.write("  longitude = {}\n".format(self.longitude))
        stream.write("  altitude = {}\n".format(self.altitude))
        stream.write("  sigmah = {}\n".format(self.sigmah))
        stream.write("  sigmaw = {}\n".format(self.sigmaw))
        stream.write("  sigmav = {}\n".format(self.sigmav))
        stream.write("  age = {}\n".format(self.age))
        stream.write("  distribution = {}\n".format(self.distribution))
        stream.write("  pollutant = {}\n".format(self.pollutant))
        stream.write("  meteorgrid = {}\n".format(self.meteorgrid))
        stream.write("  sort_index = {}\n".format(self.sort_index))


class ParticleDump:
    """Top-level container for particle dump data.
    """

    def __init__(self):
        self.year = 0
        self.month = 0
        self.day = 0
        self.hour = 0
        self.minute = 0
        self.particles = []
        self.pollutants_per_particle = 0

    @property
    def datetime(self):
        """Return a timezone-aware datetime for the event time."""
        return util.make_datetime(
            self.year, self.month, self.day,
            self.hour, self.minute, 0, 0, pytz.utc
        )

    def get_reader(self):
        return ParticleDumpFileReader(self)

    def get_writer(self):
        return ParticleDumpFileWriter(self)

    def dump(self, stream):
        """Write debug output to stream."""
        stream.write("----- begin ParticleDump\n")
        stream.write("year = {}\n".format(self.year))
        stream.write("month = {}\n".format(self.month))
        stream.write("day = {}\n".format(self.day))
        stream.write("hour = {}\n".format(self.hour))
        stream.write("minute = {}\n".format(self.minute))
        stream.write("pollutants_per_particle = {}\n".format(
            self.pollutants_per_particle))
        stream.write("num_particles = {}\n".format(len(self.particles)))

        for i, p in enumerate(self.particles):
            stream.write("particle[{}]:\n".format(i))
            p.dump(stream)

        stream.write("----- end ParticleDump\n")


class _FortranRecordReader:
    """Reads FORTRAN unformatted binary records (big-endian).

    Each record is bracketed by a 4-byte big-endian int header (payload size
    in bytes), the payload data, and a 4-byte big-endian int footer (same
    value as the header).
    """

    def __init__(self, f):
        self._f = f

    def _read_record(self, expected_size=None):
        """Read one FORTRAN record and return the payload as bytes.

        Args:
            expected_size: If set, validates the record header matches.

        Returns:
            bytes of the payload.
        """
        header_bytes = self._f.read(4)
        if len(header_bytes) < 4:
            raise EOFError("unexpected end of file reading record header")
        header = struct.unpack('>i', header_bytes)[0]

        if expected_size is not None and header != expected_size:
            raise ValueError(
                "expected record size {}, got {}".format(expected_size, header))

        payload = self._f.read(header)
        if len(payload) < header:
            raise EOFError(
                "expected {} bytes of record data, got {}".format(
                    header, len(payload)))

        footer_bytes = self._f.read(4)
        if len(footer_bytes) < 4:
            raise EOFError("unexpected end of file reading record footer")
        footer = struct.unpack('>i', footer_bytes)[0]

        if footer != header:
            raise ValueError(
                "record marker mismatch: header={}, footer={}".format(
                    header, footer))

        return payload


class ParticleDumpFileReader:
    """Reads a PARDUMP file in FORTRAN unformatted binary format."""

    def __init__(self, particle_dump):
        self.particle_dump = particle_dump

    def read(self, filename):
        """Read a PARDUMP file from disk.

        Args:
            filename: Path to the PARDUMP/PARINIT file.

        Returns:
            ParticleDump object populated with data from the file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is invalid (record marker mismatch).
            EOFError: If the file is truncated.
        """
        pardump = self.particle_dump
        pardump.particles = []

        try:
            f = open(filename, 'rb')
        except FileNotFoundError:
            raise FileNotFoundError(
                f"PARDUMP file not found: {filename}"
            )

        with f:
            reader = _FortranRecordReader(f)

            # Record #1 — Global Header (payload: 28 bytes = 7 × INT*4)
            payload = reader._read_record(expected_size=28)
            (num_particles, pollutants_per_particle,
             year, month, day, hour, minute) = struct.unpack('>7i', payload)

            # Year handling: C++ writer stores full 4-digit year,
            # but we must also tolerate 2-digit years from other sources.
            pardump.year = year if year > 100 else util.restore_year(year)
            pardump.month = month
            pardump.day = day
            pardump.hour = hour
            pardump.minute = minute
            pardump.pollutants_per_particle = pollutants_per_particle

            logger.debug(
                "read PARDUMP header: %d particles, %d pollutants/particle, "
                "year=%d month=%d day=%d hour=%d minute=%d",
                num_particles, pollutants_per_particle,
                pardump.year, month, day, hour, minute)

            # Records #2–N — Per-Particle Data
            for _ in range(num_particles):
                particle = Particle()
                self._read_particle(reader, particle, pollutants_per_particle)
                pardump.particles.append(particle)

        return pardump

    def _read_particle(self, reader, particle, pollutants_per_particle):
        """Read one particle's three sub-records."""

        # Sub-record (a): Pollutant Masses (4 × N bytes)
        payload = reader._read_record(expected_size=4 * pollutants_per_particle)
        fmt = '>{}f'.format(pollutants_per_particle)
        particle.pollutant_mass = list(struct.unpack(fmt, payload))

        # Sub-record (b): Spatial & Dispersion Properties (24 bytes = 6 × REAL*4)
        payload = reader._read_record(expected_size=24)
        (particle.latitude, particle.longitude, particle.altitude,
         particle.sigmah, particle.sigmaw, particle.sigmav) = struct.unpack(
             '>6f', payload)

        # Sub-record (c): Classification & Indexing (20 bytes = 1×REAL*4 + 4×INT*4)
        # NOTE: age is a float in C++ (particle.hh), NOT an int.
        payload = reader._read_record(expected_size=20)
        particle.age, particle.distribution, particle.pollutant, \
            particle.meteorgrid, particle.sort_index = struct.unpack('>f4i', payload)


class FileWriterDecorator:
    """Helper for writing big-endian FORTRAN unformatted binary records."""

    def __init__(self, obj):
        self.__f = obj

    def write(self, b: bytes):
        self.__f.write(b)

    def write_int4(self, v: int):
        self.__f.write(struct.pack('>i', v))

    def write_real4(self, v: float):
        self.__f.write(struct.pack('>f', v))

    def write_real4_array(self, values):
        for v in values:
            self.write_real4(v)

    def write_record_marker(self, v: int):
        self.write_int4(v)


class ParticleDumpFileWriter:
    """Writes a PARDUMP file in FORTRAN unformatted binary format."""

    def __init__(self, particle_dump):
        self.particle_dump = particle_dump

    def write(self, filename):
        pardump = self.particle_dump
        num_particles = len(pardump.particles)
        pollutants_per_particle = pardump.pollutants_per_particle

        with open(filename, 'wb') as f0:
            f = FileWriterDecorator(f0)

            # Record #1 — Global Header (payload: 28 bytes = 7 × INT*4)
            # NOTE: Write full 4-digit year, matching C++ writer at
            # persistencemanager.cc:301.
            f.write_record_marker(28)
            f.write_int4(num_particles)
            f.write_int4(pollutants_per_particle)
            f.write_int4(pardump.year)
            f.write_int4(pardump.month)
            f.write_int4(pardump.day)
            f.write_int4(pardump.hour)
            f.write_int4(pardump.minute)
            f.write_record_marker(28)

            # Records #2–N — Per-Particle Data
            for particle in pardump.particles:

                # Sub-record (a): Pollutant Masses (4 × N bytes)
                size = 4 * pollutants_per_particle
                f.write_record_marker(size)
                f.write_real4_array(particle.pollutant_mass)
                f.write_record_marker(size)

                # Sub-record (b): Spatial & Dispersion Properties (24 bytes)
                f.write_record_marker(24)
                f.write_real4(particle.latitude)
                f.write_real4(particle.longitude)
                f.write_real4(particle.altitude)
                f.write_real4(particle.sigmah)
                f.write_real4(particle.sigmaw)
                f.write_real4(particle.sigmav)
                f.write_record_marker(24)

                # Sub-record (c): Classification & Indexing (20 bytes)
                # age is float, remaining fields are int
                f.write_record_marker(20)
                f.write_real4(particle.age)
                f.write_int4(particle.distribution)
                f.write_int4(particle.pollutant)
                f.write_int4(particle.meteorgrid)
                f.write_int4(particle.sort_index)
                f.write_record_marker(20)

        return self.particle_dump
