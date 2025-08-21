from _pytest.logging import LogCaptureFixture
from pyfakefs.fake_filesystem import FakeFilesystem
from dds_cli import FileSegment, file_handler_local
import pathlib
import logging
import typing
import os
import csv
import hashlib

from dds_cli import file_compressor
from dds_cli import file_encryptor


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


def test_compress_and_decompress_file_txt(fs: FakeFilesystem, caplog: LogCaptureFixture):
    """Compress and decompress a textfile."""
    # Define path to test
    test_dir = pathlib.Path("test_dir_txt")
    fs.create_dir(test_dir)
    new_file: pathlib.Path = test_dir / "newfile.txt"
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

    # Generate checksum for original file
    checksum_new_file = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=new_file):
        checksum_new_file.update(chunk)

    with caplog.at_level(logging.DEBUG):
        # Compress file and save to new file
        compressed_file: pathlib.Path = test_dir / "compressed.txt"
        with compressed_file.open(mode="wb+") as compfile:
            for chunk in file_compressor.Compressor.compress_file(file=new_file):
                assert isinstance(chunk, bytes)
                assert len(chunk) != FileSegment.SEGMENT_SIZE_RAW
                compfile.write(chunk)

        # Verify that compressed file exists and that the sizes differ
        assert fs.exists(file_path=compressed_file)
        assert fs.stat(entry_path=new_file).st_size != fs.stat(entry_path=compressed_file).st_size

        # Verify log output
        assert (
            "dds_cli.file_compressor",
            logging.DEBUG,
            "Compression of 'test_dir_txt/newfile.txt' finished.",
        ) in caplog.record_tuples

        # Decompress file
        decompressed_file: pathlib.Path = test_dir / "decompressed.txt"
        chunks = file_handler_local.LocalFileHandler.read_file(file=compressed_file)
        saved, message = file_compressor.Compressor.decompress_filechunks(
            chunks=chunks, outfile=decompressed_file, files_directory=test_dir
        )
        assert saved and message == ""

    # Verify original and decompressed checksums
    verified, message = file_encryptor.Encryptor.verify_checksum(
        file=decompressed_file, correct_checksum=checksum_new_file.hexdigest()
    )
    assert verified and message == "File integrity verified."


def test_compress_file_img(caplog: LogCaptureFixture):
    """Compress an image.

    Not decompression since I can't get it to work when one file is fake and one is real.
    """
    image_file: pathlib.Path = pathlib.Path.cwd() / pathlib.Path("tests/images/test-image_1a.jpg")
    # Compress file
    with caplog.at_level(logging.DEBUG):
        for chunk in file_compressor.Compressor.compress_file(file=image_file):
            assert isinstance(chunk, bytes)
            assert len(chunk) != FileSegment.SEGMENT_SIZE_RAW
        assert (
            "dds_cli.file_compressor",
            logging.DEBUG,
            f"Compression of '{image_file}' finished.",
        ) in caplog.record_tuples


def test_compress_and_decompress_file_csv(fs: FakeFilesystem, caplog: LogCaptureFixture):
    """Compress and decompress a csvfile."""
    # Define path to test
    test_dir = pathlib.Path("test_dir_csv")
    fs.create_dir(test_dir)
    new_file: pathlib.Path = test_dir / "newfile.csv"
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

    # Generate checksum for original file
    checksum_new_file = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=new_file):
        checksum_new_file.update(chunk)

    # Compress file
    with caplog.at_level(logging.DEBUG):
        # Compress file and save to new file
        compressed_file: pathlib.Path = test_dir / "compressed.txt"
        with compressed_file.open(mode="wb+") as compfile:
            for chunk in file_compressor.Compressor.compress_file(file=new_file):
                assert isinstance(chunk, bytes)
                assert len(chunk) != FileSegment.SEGMENT_SIZE_RAW
                compfile.write(chunk)

        # Verify that compressed file exists and that the sizes differ
        assert fs.exists(file_path=compressed_file)
        assert fs.stat(entry_path=new_file).st_size != fs.stat(entry_path=compressed_file).st_size

        assert (
            "dds_cli.file_compressor",
            logging.DEBUG,
            "Compression of 'test_dir_csv/newfile.csv' finished.",
        ) in caplog.record_tuples

        # Decompress file
        decompressed_file: pathlib.Path = test_dir / "decompressed.csv"
        chunks = file_handler_local.LocalFileHandler.read_file(file=compressed_file)
        saved, message = file_compressor.Compressor.decompress_filechunks(
            chunks=chunks, outfile=decompressed_file, files_directory=test_dir
        )
        assert saved and message == ""

    # Verify original and decompressed checksums
    verified, message = file_encryptor.Encryptor.verify_checksum(
        file=decompressed_file, correct_checksum=checksum_new_file.hexdigest()
    )
    assert verified and message == "File integrity verified."
