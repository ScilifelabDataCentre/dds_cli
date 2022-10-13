from _pytest.logging import LogCaptureFixture
from pyfakefs.fake_filesystem import FakeFilesystem
from dds_cli import FileSegment
import pathlib
import logging
import typing
import os 

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
            f"[Errno 2] No such file or directory in the fake filesystem: 'nonexistentfile.txt'",
        ) in caplog.record_tuples
        assert (
            "dds_cli.file_compressor",
            logging.DEBUG,
            "Compression finished.",
        ) not in caplog.record_tuples

def test_compress_file_txt(fs: FakeFilesystem, caplog: LogCaptureFixture):
    """Compress a textfile."""
    # Define path to test
    new_file: pathlib.Path = pathlib.Path("newfile.txt")
    assert not fs.exists(file_path=new_file)

    # Create file
    fs.create_file(file_path=new_file)
    assert fs.exists(file_path=new_file)
    assert fs.stat(entry_path=new_file).st_size == 0

    # Define lines to input
    line_contents: str = "abcdefghijklmnopqrstuvwxyzåäö"
    lines: typing.List = [line_contents] * 10000
    
    # Add contents to file
    with open(new_file, mode="w") as f:
        f.writelines(lines)
    assert os.stat(new_file).st_size > FileSegment.SEGMENT_SIZE_RAW
    
    # Compress file
    with caplog.at_level(logging.DEBUG):
        for chunk in file_compressor.Compressor.compress_file(file=new_file):
            assert isinstance(chunk, bytes)
            assert len(chunk) != FileSegment.SEGMENT_SIZE_RAW
        assert (
            "dds_cli.file_compressor",
            logging.DEBUG,
            "Compression finished.",
        ) in caplog.record_tuples