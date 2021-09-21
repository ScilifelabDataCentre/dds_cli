# IMPORTS ################################################################################ IMPORTS #

# Standard library
import pathlib

# Installed
import pytest

# Own modules
from dds_cli import base
from dds_cli import exceptions

# GLOBAL VARIABLES ############################################################## GLOBAL VARIABLES #

CONFIG_PATH = pathlib.Path("./tests/config")


# TESTS #################################################################################### TESTS #


# Only credentials
def test_ddsbaseclass_no_method(monkeypatch):
    """No method should raise an error indicating an invalid method."""

    with pytest.raises(exceptions.InvalidMethodError):
        _ = base.DDSBaseClass()


def test_ddsbaseclass_method_ls_and_missing_username(monkeypatch):
    """Missing username should raise exception"""

    with pytest.raises(exceptions.MissingCredentialsException) as mis_err:
        _ = base.DDSBaseClass(method="ls")

    assert "missing" in str(mis_err.value)
    assert "username" in str(mis_err.value)


def test_ddsbaseclass_method_ls_and_missing_password(monkeypatch):
    """Missing password should raise exception indicating too little user info."""

    monkeypatch.setattr("getpass.getpass", lambda: None)
    with pytest.raises(exceptions.MissingCredentialsException) as mis_err:
        _ = base.DDSBaseClass(method="ls", username="test")

    assert "missing" in str(mis_err.value)


def test_ddsbaseclass_method_ls_and_incorrect_username(monkeypatch):
    """Incorrect username with password should result in AuthenticationError"""

    monkeypatch.setattr("getpass.getpass", lambda: str("password"))
    with pytest.raises(exceptions.AuthenticationError) as autherr:
        _ = base.DDSBaseClass(method="ls", username="test")

    assert "incorrect" in str(autherr.value)


def test_ddsbaseclass_method_ls_and_incorrect_password(monkeypatch):
    """Incorrect password should result in AuthenticationError"""

    monkeypatch.setattr("getpass.getpass", lambda: str("incorrect_password"))
    with pytest.raises(exceptions.AuthenticationError) as autherr:
        _ = base.DDSBaseClass(method="ls", username="username")

    assert "incorrect" in str(autherr.value)


def test_ddsbaseclass_method_ls_and_correct_info(monkeypatch):
    """Correct info should result in a DDSBaseClass Object"""

    monkeypatch.setattr("getpass.getpass", lambda: str("password"))
    baseclass_object = base.DDSBaseClass(method="ls", username="username")
    assert isinstance(baseclass_object, base.DDSBaseClass)
    assert baseclass_object.method == "ls"
    assert baseclass_object.project is None
    assert baseclass_object.token and baseclass_object.token != ""
    assert not hasattr(baseclass_object, "username")
    assert not hasattr(baseclass_object, "password")
    assert not hasattr(baseclass_object, "keys")
    assert not hasattr(baseclass_object, "status")
    assert not hasattr(baseclass_object, "filehandler")


# Including config
def test_ddsbaseclass_method_ls_and_incorrect_in_config():
    """Config file consists of incorrect info"""

    configfile = CONFIG_PATH / pathlib.Path("with_fields_config.json")
    with pytest.raises(exceptions.AuthenticationError) as autherr:
        _ = base.DDSBaseClass(method="ls", config=configfile)

    assert "incorrect" in str(autherr.value)


def test_ddsbaseclass_method_ls_and_incorrect_in_config_and_username(monkeypatch):
    """Username should overwrite username in config and password should be asked for"""

    configfile = CONFIG_PATH / pathlib.Path("with_fields_config.json")
    monkeypatch.setattr("getpass.getpass", lambda: str("incorrect_password"))
    with pytest.raises(exceptions.AuthenticationError) as autherr:
        _ = base.DDSBaseClass(method="ls", config=configfile)

    assert "incorrect" in str(autherr.value)


def test_ddsbaseclass_method_ls_and_incorrect_in_config_and_username_password(monkeypatch):
    """Username and password"""

    configfile = CONFIG_PATH / pathlib.Path("with_fields_config.json")
    monkeypatch.setattr("getpass.getpass", lambda: str("password"))
    baseclass_object = base.DDSBaseClass(method="ls", config=configfile, username="username")

    assert isinstance(baseclass_object, base.DDSBaseClass)
    assert baseclass_object.method == "ls"
    assert baseclass_object.project is None
    assert baseclass_object.token and baseclass_object.token != ""
    assert not hasattr(baseclass_object, "username")
    assert not hasattr(baseclass_object, "password")
    assert not hasattr(baseclass_object, "keys")
    assert not hasattr(baseclass_object, "status")
    assert not hasattr(baseclass_object, "filehandler")
