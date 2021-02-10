import immutabledict


class CompressionMagic:
    """Compression format signatures"""

    BZIP2 = b"BZh"
    LZIP = b"LZIP"
    RAR4 = b"Rar!\x1a\x07\x00"
    RAR5 = b"Rar!\x1a\x07\x01\x00"
    # SEVENZIP = b"7z¼¯'"
    GZIP = b"\x1F\x8B"
    ZSTANDARD = b"(\xb5/\xfd"


class Compressor:
    """Handles operations relating to file compression."""

    def __init__(self, algorithm="zstandard"):
        self.algorithm = algorithm
        self.FMT_MAGIC = immutabledict.immutabledict({
            b"\x913HF": "hap",
            b"`\xea": "arj",
            b"_\'\xa8\x89": "jar",
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
            b"(\xb5/\xfd": "zst"
        })
        self.MAX_MAGIC_LEN = max(len(x) for x in self.FMT_MAGIC)

    def is_compressed(self, file):
        """Checks if a file is compressed or not."""

        try:
            with file.open(mode="rb") as f:
                # file_start = f.read(MAX_MAGIC_LEN)

                for signature, _ in
