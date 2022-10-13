import chunk
from _pytest.logging import LogCaptureFixture
from pyfakefs.fake_filesystem import FakeFilesystem
import pathlib
import logging

from dds_cli import file_compressor

def test_compress_file_nonexistent(fs: FakeFilesystem, caplog: LogCaptureFixture):
    """Try to compress a file that doesn't exist."""
    # Define path to test
    non_existent_file: pathlib.Path = pathlib.Path("nonexistentfile.txt")
    assert not fs.exists(file_path=non_existent_file)

    # Capture logging
    with caplog.at_level(logging.DEBUG):
        for chunk in file_compressor.Compressor.compress_file(file=non_existent_file):
            assert not chunk
        assert (
            "dds_cli.file_compressor",
            logging.WARNING,
            f"[Errno 2] No such file or directory in the fake filesystem: 'nonexistentfile.txt'"
        ) in caplog.record_tuples
        assert (
            "dds_cli.file_compressor",
            logging.DEBUG,
            "Compression finished."
        ) not in caplog.record_tuples

