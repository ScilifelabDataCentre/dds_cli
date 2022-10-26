from pyfakefs.fake_filesystem import FakeFilesystem
from requests_mock.mocker import Mocker
from unittest import mock
from dds_cli.base import DDSBaseClass
from dds_cli import DDSEndpoint
from dds_cli.data_putter import DataPutter
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
    filehandler = LocalFileHandler(user_input=(("parentdir",), None), project="someproject", temporary_destination="temporarydestination", remote_destination="remote_destination")
    assert filehandler.data == ""