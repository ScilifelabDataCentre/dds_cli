import pathlib
from pyfakefs.fake_filesystem import FakeFilesystem
from dds_cli.file_handler_local import LocalFileHandler


def test_localfilehandler_with_destination(fs: FakeFilesystem):
    """Test that the destination flag works."""
    # Create directories
    fs.create_dir("parentdir")
    fs.create_dir("parentdir/somedir")
    fs.create_dir("parentdir/somedir/subdir")

    # Verify exists
    assert fs.exists(file_path="parentdir")
    assert fs.exists(file_path="parentdir/somedir")
    assert fs.exists(file_path="parentdir/somedir/subdir")

    # Create files
    fs.create_file("parentdir/fileinparentdir.file")
    fs.create_file("parentdir/somedir/fileinsomedir.file")
    fs.create_file("parentdir/somedir/subdir/fileinsubdir.file")

    # Verify files exist
    assert fs.exists(file_path="parentdir/fileinparentdir.file")
    assert fs.exists(file_path="parentdir/somedir/fileinsomedir.file")
    assert fs.exists(file_path="parentdir/somedir/subdir/fileinsubdir.file")

    # Verify that fails with incorrect paths
    assert not fs.exists(file_path="anotherdir")
    assert not fs.exists(file_path="parentdir/somefile.file")

    # Call LocalFileHandler
    filehandler = LocalFileHandler(
        user_input=((pathlib.Path("parentdir"),), None),
        project="someproject",
        temporary_destination="temporarydestination",
        remote_destination="remote_destination",
    )
    expected_data_1 = {
        "remote_destination/parentdir/fileinparentdir.file": {
            "path_raw": pathlib.Path("/parentdir/fileinparentdir.file"),
            "subpath": pathlib.Path("remote_destination/parentdir/"),
            "size_raw": 0,
            "compressed": False,
            "path_processed": filehandler.create_encrypted_name(
                raw_file=pathlib.Path("parentdir/fileinparentdir.file"),
                subpath=pathlib.Path("remote_destination/parentdir"),
                no_compression=False,
            ),
            "size_processed": 0,
            "overwrite": False,
            "checksum": "",
        },
        "remote_destination/parentdir/somedir/fileinsomedir.file": {
            "path_raw": pathlib.Path("/parentdir/somedir/fileinsomedir.file"),
            "subpath": pathlib.Path("remote_destination/parentdir/somedir/"),
            "size_raw": 0,
            "compressed": False,
            "path_processed": filehandler.create_encrypted_name(
                raw_file=pathlib.Path("parentdir/somedir/fileinsomedir.file"),
                subpath=pathlib.Path("remote_destination/parentdir/somedir"),
                no_compression=False,
            ),
            "size_processed": 0,
            "overwrite": False,
            "checksum": "",
        },
        "remote_destination/parentdir/somedir/subdir/fileinsubdir.file": {
            "path_raw": pathlib.Path("/parentdir/somedir/subdir/fileinsubdir.file"),
            "subpath": pathlib.Path("remote_destination/parentdir/somedir/subdir/"),
            "size_raw": 0,
            "compressed": False,
            "path_processed": filehandler.create_encrypted_name(
                raw_file=pathlib.Path("parentdir/somedir/subdir/fileinsubdir.file"),
                subpath=pathlib.Path("remote_destination/parentdir/somedir/subdir"),
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
