# Standard library

# Installed
import pytest
import requests

# Own modules
import dds_cli

# Variables
correct_project = "public_project_id"
incorrect_project = "incorrect_project_id"

# Tests

# Auth
def test_auth_check_statuscode_400_missing_info():
    """
    Test that the auth endpoint returns:
    Status code: 400
    Message: Indicates missing user info.
    """

    # No params, no auth
    response = requests.get(dds_cli.DDSEndpoint.AUTH)
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "Missing" in response_json.get("message")


def test_auth_incorrect_username_check_statuscode_400_incorrect_info():
    """Test that the auth endpoint returns
    Status code: 400
    Message: Incorrect username and/or password.
    """

    response = requests.get(dds_cli.DDSEndpoint.AUTH, auth=("incorrect_username", "password"))
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "Incorrect username and/or password." == response_json.get("message")


def test_auth_incorrect_username_and_password_check_statuscode_400_incorrect_info():
    """Test that the auth endpoint returns
    Status code: 400
    Message: Incorrect username and/or password.
    """

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH, auth=("incorrect_username", "incorrect_password")
    )
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "Incorrect username and/or password." == response_json.get("message")


def test_auth_incorrect_password_check_statuscode_400_incorrect_info():
    """Test that the auth endpoint returns
    Status code: 400
    Message: Incorrect username and/or password.
    """

    response = requests.get(dds_cli.DDSEndpoint.AUTH, auth=("username", "incorrect_password"))
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "Incorrect username and/or password." == response_json.get("message")


def test_auth_correctauth_check_statuscode_400_correct_info():
    """Test that the auth endpoint returns
    Status code: 400
    Message: Incorrect username and/or password.
    """

    response = requests.get(dds_cli.DDSEndpoint.AUTH, auth=("username", "password"))
    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("token")
    assert response_json.get("token") != ""


#
