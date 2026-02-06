import pathlib
from pyfakefs.fake_filesystem import FakeFilesystem
from unittest.mock import MagicMock, patch
import pytest
import hashlib

from dds_cli.file_handler_local import LocalFileHandler


# ---------- Helper Functions ----------


def create_test_file(fs, dir_path: str, file_name: str, contents: bytes):
    """Create directory and file in fake filesystem."""
    fs.create_dir(pathlib.Path(dir_path))
    file_path = pathlib.Path(dir_path) / file_name
    fs.create_file(file_path, contents=contents)
    assert fs.exists(dir_path)
    assert fs.exists(file_path)
    return file_path


# ---------- Tests ----------


def test_localfilehandler_with_destination(fs: FakeFilesystem):
    """Test that the destination flag works."""
    # Create directories
    fs.create_dir(pathlib.Path("parentdir"))
    fs.create_dir(pathlib.Path("parentdir") / "somedir")
    fs.create_dir(pathlib.Path("parentdir") / "somedir" / "subdir")

    # Verify exists
    assert fs.exists(file_path=pathlib.Path("parentdir"))
    assert fs.exists(file_path=pathlib.Path("parentdir") / "somedir")
    assert fs.exists(file_path=pathlib.Path("parentdir") / "somedir" / "subdir")

    # Create files
    fs.create_file(pathlib.Path("parentdir") / "fileinparentdir.file")
    fs.create_file(pathlib.Path("parentdir") / "somedir" / "fileinsomedir.file")
    fs.create_file(pathlib.Path("parentdir") / "somedir" / "subdir" / "fileinsubdir.file")

    # Verify files exist
    assert fs.exists(file_path=pathlib.Path("parentdir") / "fileinparentdir.file")
    assert fs.exists(file_path=pathlib.Path("parentdir") / "somedir" / "fileinsomedir.file")
    assert fs.exists(
        file_path=pathlib.Path("parentdir") / "somedir" / "subdir" / "fileinsubdir.file"
    )

    # Verify that fails with incorrect paths
    assert not fs.exists(file_path=pathlib.Path("anotherdir"))
    assert not fs.exists(file_path=pathlib.Path("parentdir") / "somefile.file")

    # Call LocalFileHandler
    filehandler = LocalFileHandler(
        user_input=((pathlib.Path("parentdir"),), None),
        project="someproject",
        temporary_destination="temporarydestination",
        remote_destination="remote_destination",
    )
    expected_data_1 = {
        (pathlib.Path("remote_destination") / "parentdir" / "fileinparentdir.file").as_posix(): {
            "path_raw": pathlib.Path.cwd() / "parentdir" / "fileinparentdir.file",
            "subpath": pathlib.Path("remote_destination") / "parentdir",
            "size_raw": 0,
            "compressed": False,
            "path_processed": filehandler.create_encrypted_name(
                raw_file=pathlib.Path("parentdir") / "fileinparentdir.file",
                subpath=pathlib.Path("remote_destination") / "parentdir",
                no_compression=False,
            ),
            "size_processed": 0,
            "overwrite": False,
            "checksum": "",
        },
        (
            pathlib.Path("remote_destination") / "parentdir" / "somedir" / "fileinsomedir.file"
        ).as_posix(): {
            "path_raw": pathlib.Path.cwd() / "parentdir" / "somedir" / "fileinsomedir.file",
            "subpath": pathlib.Path("remote_destination") / "parentdir" / "somedir",
            "size_raw": 0,
            "compressed": False,
            "path_processed": filehandler.create_encrypted_name(
                raw_file=pathlib.Path("parentdir") / "somedir" / "fileinsomedir.file",
                subpath=pathlib.Path("remote_destination") / "parentdir" / "somedir",
                no_compression=False,
            ),
            "size_processed": 0,
            "overwrite": False,
            "checksum": "",
        },
        (
            pathlib.Path("remote_destination")
            / "parentdir"
            / "somedir"
            / "subdir"
            / "fileinsubdir.file"
        ).as_posix(): {
            "path_raw": pathlib.Path.cwd()
            / "parentdir"
            / "somedir"
            / "subdir"
            / "fileinsubdir.file",
            "subpath": pathlib.Path("remote_destination") / "parentdir" / "somedir" / "subdir",
            "size_raw": 0,
            "compressed": False,
            "path_processed": filehandler.create_encrypted_name(
                raw_file=pathlib.Path("parentdir") / "somedir" / "subdir" / "fileinsubdir.file",
                subpath=pathlib.Path("remote_destination") / "parentdir" / "somedir" / "subdir",
                no_compression=False,
            ),
            "size_processed": 0,
            "overwrite": False,
            "checksum": "",
        },
    }

    # Verify correctness
    # file is what will be put into the database as the file name
    for file, info in expected_data_1.items():
        actual_data = filehandler.data.get(file)
        assert actual_data
        for x in info:
            assert actual_data[x] == info[x]


### Test static methods

# ---------- Tests for read_file ----------


def test_read_file_success(fs: FakeFilesystem):
    """File is read in chunks correctly."""

    # 10 bytes
    test_file = create_test_file(fs, "parentdir", "testfile.bin", b"abcdefghij")

    chunks = list(LocalFileHandler.read_file(test_file, chunk_size=4))
    assert chunks == [b"abcd", b"efgh", b"ij"]


def test_read_file_empty(fs: FakeFilesystem):
    """Empty file yields no chunks."""

    test_file = create_test_file(fs, "parentdir", "emptyfile.bin", b"")

    chunks = list(LocalFileHandler.read_file(test_file, chunk_size=4))
    assert chunks == []


def test_read_file_oserror():
    """OSError triggers warning and yields nothing."""

    fake_file = pathlib.Path("/nonexistent/file.bin")

    with patch("dds_cli.file_handler_local.LOG") as mock_log:
        chunks = list(LocalFileHandler.read_file(fake_file, chunk_size=4))

        assert chunks == []
        mock_log.warning.assert_called_once()


# ---------- Tests for stream_from_file ----------


def test_stream_from_file_compressed(fs: FakeFilesystem):
    """When compressed=True, stream_from_file yields raw chunks."""

    test_file = create_test_file(fs, "parentdir", "compressed.bin", b"hello world")

    # Build fake handler with minimal data dict
    filehandler = LocalFileHandler(
        user_input=((test_file,), None),
        project="someproject",
        temporary_destination="temporarydestination",
        remote_destination="remote_destination",
    )
    filehandler.data = {
        "file1": {
            "path_raw": test_file,
            "compressed": True,
            "checksum": "",
        }
    }

    chunks = list(filehandler.stream_from_file("file1"))
    assert b"".join(chunks) == b"hello world"

    # Checksum should be correct
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert filehandler.data["file1"]["checksum"] == expected


def test_stream_from_file_uncompressed(fs: FakeFilesystem):
    """When compressed=False, it should first read file for checksum then compress."""

    test_file = create_test_file(fs, "parentdir", "uncompressed.bin", b"abc123")

    # Build fake handler with minimal data dict
    filehandler = LocalFileHandler(
        user_input=((test_file,), None),
        project="someproject",
        temporary_destination="temporarydestination",
        remote_destination="remote_destination",
    )
    filehandler.data = {
        "file1": {
            "path_raw": test_file,
            "compressed": False,
            "checksum": "",
        }
    }

    fake_chunks = [b"zzz", b"yyy"]
    with patch("dds_cli.file_handler_local.fc.Compressor.compress_file", return_value=fake_chunks):
        chunks = list(filehandler.stream_from_file("file1"))

    assert chunks == fake_chunks

    # Checksum must match original file (pre-compression)
    expected = hashlib.sha256(b"abc123").hexdigest()
    assert filehandler.data["file1"]["checksum"] == expected
