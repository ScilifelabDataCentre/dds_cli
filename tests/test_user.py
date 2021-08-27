# Standard library

# Installed
import pytest

# Own modules
from dds_cli import user
from dds_cli import exceptions

# Tests
def test_user_missing_user_options():
    """Exception should be raised due to missing user credentials."""

    with pytest.raises(exceptions.MissingCredentialsException) as miserr:
        _ = user.User()
        print(miserr)

    assert "missing" in str(miserr.value)


def test_user_missing_username():
    """Exception should be raised due to missing username"""

    with pytest.raises(exceptions.MissingCredentialsException) as miserr:
        _ = user.User(password="test")

    assert "missing" in str(miserr.value)


def test_user_missing_password():
    """Exception should  be raised due to missing password"""

    with pytest.raises(exceptions.MissingCredentialsException) as miserr:
        _ = user.User(username="test")

    assert "missing" in str(miserr.value)


def test_user_incorrect_username():
    """Exception should be raised due to incorrect username"""

    with pytest.raises(exceptions.AuthenticationError) as autherr:
        _ = user.User(username="test", password="password")

    assert "Incorrect" in str(autherr.value)


def test_user_incorrect_password():
    """Exceptions should be raised due to incorrect password"""

    with pytest.raises(exceptions.AuthenticationError) as autherr:
        _ = user.User(username="username", password="incorrect_password")

    assert "Incorrect" in str(autherr.value)


def test_user_correct_credentials():
    """User object should be created with correct credentials"""

    username = "username"

    test_user = user.User(username=username, password="password")
    assert test_user
    assert test_user.username == username
    assert test_user.password is None
    assert test_user.project is None
    assert test_user.token and test_user.token != ""
