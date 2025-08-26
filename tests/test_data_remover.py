from _pytest.logging import LogCaptureFixture
from pyfakefs.fake_filesystem import FakeFilesystem
from requests_mock.mocker import Mocker
import pytest
import pathlib
import logging

from dds_cli import data_remover
from dds_cli import DDSEndpoint
from dds_cli.exceptions import APIError


def test_delete_tempfile_cannot_delete(fs: FakeFilesystem, caplog: LogCaptureFixture):
    """Test that the file cannot be deleted."""
    # Define path to test
    non_existent_file: pathlib.Path = pathlib.Path("nonexistentfile.txt")
    assert not fs.exists(file_path=non_existent_file)

    # Attempt to delete
    with caplog.at_level(logging.WARNING):
        data_remover.DataRemover.delete_tempfile(file=non_existent_file)
        # Substring matching should ensure more reliable cross-platform behavior
        # instead of exact tuple matching that may break on different path separators
        assert any(
            "No such file or directory" in msg and non_existent_file.name in msg
            for msg in caplog.messages
        )
        assert any(
            "File deletion may have failed. Usage of space may increase." in msg
            for msg in caplog.messages
        )


def test_delete_tempfile_ok(fs: FakeFilesystem, caplog: LogCaptureFixture):
    """An existent file should be possible to delete."""
    # Define path to test
    new_file: pathlib.Path = pathlib.Path("new_file.txt")
    assert not fs.exists(file_path=new_file)

    # Create file
    fs.create_file(new_file)
    assert fs.exists(file_path=new_file)

    # Delete file
    with caplog.at_level(logging.WARNING):
        data_remover.DataRemover.delete_tempfile(file=new_file)
        assert not fs.exists(file_path=new_file)
        assert not any(
            "No such file or directory" in msg and new_file.name in msg for msg in caplog.messages
        )
        assert not any(
            "File deletion may have failed. Usage of space may increase." in msg
            for msg in caplog.messages
        )


def test_delete_all_ok(capfd: LogCaptureFixture):
    """Delete all files. - ok"""

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.delete(
            DDSEndpoint.REMOVE_PROJ_CONT,
            status_code=200,
            json={"message": "All files removed.", "removed": True},
        )

        with data_remover.DataRemover(authenticate=False, project="project_1") as dr:
            dr.token = {"Authorization": "Bearer FAKE_TOKEN"}  # required
            dr.remove_all()

            out, err = capfd.readouterr()
            assert "All files removed." in out
            assert not err


def test_delete_all_malformated_response():
    """Malformated response"""

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.delete(DDSEndpoint.REMOVE_PROJ_CONT, status_code=200, json={})

        with data_remover.DataRemover(authenticate=False, project="project_1") as dr:
            dr.token = {"Authorization": "Bearer FAKE_TOKEN"}  # required

            with pytest.raises(APIError) as err:
                dr.remove_all()
                assert "Malformatted response detected when attempting to remove all files" in str(
                    err.value
                )
