import immutabledict
import pathlib
import dataclasses
import traceback
import sys
from cli_code import FileSegment
import zstandard as zstd
import logging

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class CompressionMagic:
    """Compression format signatures"""

    BZIP2 = b"BZh"
    LZIP = b"LZIP"
    RAR4 = b"Rar!\x1a\x07\x00"
    RAR5 = b"Rar!\x1a\x07\x01\x00"
    GZIP = b"\x1F\x8B"
    ZSTANDARD = b"(\xb5/\xfd"


@dataclasses.dataclass
class Compressor:
    """Handles operations relating to file compression."""

    algorithm: str = "zstandard"
    fmt_magic: dict = dataclasses.field(init=False)
    max_magic_len: int = dataclasses.field(init=False)

    def __post_init__(self):
        self.fmt_magic = {
            b"\x913HF": "hap",
            b"`\xea": "arj",
            b"_'\xa8\x89": "jar",
            b"ZOO ": "zoo",
            b"PK\x03\x04": "zip",
            b"\x1F\x8B": "gzip",
            b"UFA\xc6\xd2\xc1": "ufa",
            b"StuffIt ": "sit",
            b"Rar!\x1a\x07\x00": "rar v4.x",
            b"Rar!\x1a\x07\x01\x00": "rar v5",
            b"MAr0\x00": "mar",
            b"DMS!": "dms",
            b"CRUSH v": "cru",
            b"BZh": "bz2",
            b"-lh": "lha",
            b"(This fi": "hqx",
            b"!\x12": "ain",
            b"\x1a\x0b": "pak",
            b"(\xb5/\xfd": "zst",
        }
        self.max_magic_len = max(len(x) for x in self.fmt_magic)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def is_compressed(self, file):
        """Checks if a file is compressed or not."""

        compressed, error = (False, "")
        try:
            with file.open(mode="rb") as f:
                file_start = f.read(self.max_magic_len)
                if file_start.startswith(tuple(x for x in self.fmt_magic)):
                    compressed = True
        except OSError as err:
            error = str(err)

        return compressed, error

    @staticmethod
    def compress_file(
        file: pathlib.Path,
        chunk_size: int = FileSegment.SEGMENT_SIZE_RAW,
    ) -> (bytes):
        """Compresses file by reading it chunk by chunk."""

        with file.open(mode="rb") as infile:

            # Initiate a Zstandard compressor
            cctzx = zstd.ZstdCompressor(write_checksum=True, level=4)

            # Compress file chunk by chunk while reading
            with cctzx.stream_reader(infile) as compressor:
                for chunk in iter(lambda: compressor.read(chunk_size), b""):
                    yield chunk
