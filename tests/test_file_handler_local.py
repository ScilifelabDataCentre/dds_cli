from pathlib import Path
from pyfakefs.fake_filesystem import FakeFilesystem
from dds_cli.file_handler_local import LocalFileHandler


def test_localfilehandler_with_destination(fs: FakeFilesystem):
    """Test that the destination flag works."""
    # Create directories
    fs.create_dir(Path("parentdir"))
    fs.create_dir(Path("parentdir") / "somedir")
    fs.create_dir(Path("parentdir") / "somedir" / "subdir")

    # Verify exists
    assert fs.exists(file_path=Path("parentdir"))
    assert fs.exists(file_path=Path("parentdir") / "somedir")
    assert fs.exists(file_path=Path("parentdir") / "somedir" / "subdir")

    # Create files
    fs.create_file(Path("parentdir") / "fileinparentdir.file")
    fs.create_file(Path("parentdir") / "somedir" / "fileinsomedir.file")
    fs.create_file(Path("parentdir") / "somedir" / "subdir" / "fileinsubdir.file")

    # Verify files exist
    assert fs.exists(file_path=Path("parentdir") / "fileinparentdir.file")
    assert fs.exists(file_path=Path("parentdir") / "somedir" / "fileinsomedir.file")
    assert fs.exists(file_path=Path("parentdir") / "somedir" / "subdir" / "fileinsubdir.file")

    # Verify that fails with incorrect paths
    assert not fs.exists(file_path=Path("anotherdir"))
    assert not fs.exists(file_path=Path("parentdir") / "somefile.file")

    # Call LocalFileHandler
    filehandler = LocalFileHandler(
        user_input=((Path("parentdir"),), None),
        project="someproject",
        temporary_destination="temporarydestination",
        remote_destination="remote_destination",
    )
    expected_data_1 = {
        (Path("remote_destination") / "parentdir" / "fileinparentdir.file").as_posix(): {
            "path_raw": Path.cwd() / "parentdir" / "fileinparentdir.file",
            "subpath": Path("remote_destination") / "parentdir",
            "size_raw": 0,
            "compressed": False,
            "path_processed": filehandler.create_encrypted_name(
                raw_file=Path("parentdir") / "fileinparentdir.file",
                subpath=Path("remote_destination") / "parentdir",
                no_compression=False,
            ),
            "size_processed": 0,
            "overwrite": False,
            "checksum": "",
        },
        (Path("remote_destination") / "parentdir" / "somedir" / "fileinsomedir.file").as_posix(): {
            "path_raw": Path.cwd() / "parentdir" / "somedir" / "fileinsomedir.file",
            "subpath": Path("remote_destination") / "parentdir" / "somedir",
            "size_raw": 0,
            "compressed": False,
            "path_processed": filehandler.create_encrypted_name(
                raw_file=Path("parentdir") / "somedir" / "fileinsomedir.file",
                subpath=Path("remote_destination") / "parentdir" / "somedir",
                no_compression=False,
            ),
            "size_processed": 0,
            "overwrite": False,
            "checksum": "",
        },
        (
            Path("remote_destination") / "parentdir" / "somedir" / "subdir" / "fileinsubdir.file"
        ).as_posix(): {
            "path_raw": Path.cwd() / "parentdir" / "somedir" / "subdir" / "fileinsubdir.file",
            "subpath": Path("remote_destination") / "parentdir" / "somedir" / "subdir",
            "size_raw": 0,
            "compressed": False,
            "path_processed": filehandler.create_encrypted_name(
                raw_file=Path("parentdir") / "somedir" / "subdir" / "fileinsubdir.file",
                subpath=Path("remote_destination") / "parentdir" / "somedir" / "subdir",
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
