from _pytest.logging import LogCaptureFixture
from pyfakefs.fake_filesystem import FakeFilesystem
from dds_cli import FileSegment
import pathlib
import logging
import typing
import os
import csv

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


def perform_compress_file(file: pathlib.Path, fs: FakeFilesystem = None):
    for chunk in file_compressor.Compressor.compress_file(file=file):
        assert isinstance(chunk, bytes)
        assert len(chunk) != FileSegment.SEGMENT_SIZE_RAW


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
        perform_compress_file(file=new_file, fs=fs)
        assert (
            "dds_cli.file_compressor",
            logging.DEBUG,
            "Compression finished.",
        ) in caplog.record_tuples


def test_compress_file_img(caplog: LogCaptureFixture):
    """Compress an image."""
    image_file: pathlib.Path = pathlib.Path.cwd() / pathlib.Path("tests/images/test-image_1a.jpg")
    # Compress file
    with caplog.at_level(logging.DEBUG):
        perform_compress_file(file=image_file)
        assert (
            "dds_cli.file_compressor",
            logging.DEBUG,
            "Compression finished.",
        ) in caplog.record_tuples


def test_compress_file_csv(fs: FakeFilesystem, caplog: LogCaptureFixture):
    """Compress a csvfile."""
    # Define path to test
    new_file: pathlib.Path = pathlib.Path("newfile.csv")
    assert not fs.exists(file_path=new_file)

    # Create file
    fs.create_file(file_path=new_file)
    assert fs.exists(file_path=new_file)
    assert fs.stat(entry_path=new_file).st_size == 0

    # Define lines to input
    cell_contents: str = "abcdefghijklmnopqrstuvwxyzåäö0123456789"
    row_contents: typing.List = [cell_contents] * 10
    file_contents: typing.List = [row_contents] * 10000

    # Fill file
    with new_file.open(mode="w") as f:
        writer = csv.writer(f)
        writer.writerows(file_contents)
    assert os.stat(new_file).st_size > FileSegment.SEGMENT_SIZE_RAW

    # Compress file
    with caplog.at_level(logging.DEBUG):
        perform_compress_file(file=new_file)
        assert (
            "dds_cli.file_compressor",
            logging.DEBUG,
            "Compression finished.",
        ) in caplog.record_tuples
