# IMPORTS ################################################################################ IMPORTS #
# Standard library

# Installed
import pytest

# Own modules
from dds_cli import data_lister
from dds_cli import exceptions

# TESTS #################################################################################### TESTS #


# DataLister.__init__
def test_datalister_init_missing_credentials():
    """No user credentials should result in raised missing credentials exception"""

    with pytest.raises(exceptions.MissingCredentialsException) as misserr:
        _ = data_lister.DataLister()

    assert "options are missing" in str(misserr.value)
    assert "username" in str(misserr.value)


def test_datalister_init_missing_password(monkeypatch):
    """No password should raise exception"""

    monkeypatch.setattr("getpass.getpass", lambda: None)
    with pytest.raises(exceptions.MissingCredentialsException) as misserr:
        _ = data_lister.DataLister(username="username")

    assert "options are missing" in str(misserr.value)
    assert "password" in str(misserr.value)


def test_datalister_init_invalid_method(monkeypatch):
    """Any other method than 'ls' should raise invalid method exception"""

    monkeypatch.setattr("getpass.getpass", lambda: str("password"))
    with pytest.raises(exceptions.InvalidMethodError) as metherr:
        _ = data_lister.DataLister(method="put", username="username")

    assert "unauthorized method" in str(metherr.value)


def test_datalister_init_valid(monkeypatch):
    """Object should have all attributes and execute without raised exceptions."""

    monkeypatch.setattr("getpass.getpass", lambda: str("password"))
    datalister_object = data_lister.DataLister(username="username")
    assert isinstance(datalister_object, data_lister.DataLister)
    assert datalister_object.method == "ls"
    assert datalister_object.project is None
    assert datalister_object.token and datalister_object.token != ""
    assert not hasattr(datalister_object, "username")
    assert not hasattr(datalister_object, "password")
    assert not hasattr(datalister_object, "keys")
    assert not hasattr(datalister_object, "status")
    assert not hasattr(datalister_object, "filehandler")


# DataLister.list_projects
def test_datalister_listprojects(monkeypatch):

    monkeypatch.setattr("getpass.getpass", lambda: str("password"))
    datalister_object = data_lister.DataLister(username="username")

    datalister_object.list_projects()
