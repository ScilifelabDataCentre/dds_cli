# IMPORTS ################################################################################ IMPORTS #
# Standard library

# Installed
import http
import requests

# Own modules
import dds_cli
from dds_cli import user

# VARIABLES ############################################################################ VARIABLES #


# TESTS #################################################################################### TESTS #


def test_proj_public_no_token():
    """Attempting to get the public key without a token should not work"""

    response = requests.get(dds_cli.DDSEndpoint.PROJ_PUBLIC)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json()
    assert "Missing or incorrect credentials" in response_json.get("message")


def test_proj_public_no_project():
    """Attempting to get public key without a project should not work"""

    token = user.User(username="username", password="password").token
    response = requests.get(dds_cli.DDSEndpoint.PROJ_PUBLIC, headers=token)
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json()
    assert "without project ID" in response_json.get("message")


def test_proj_public_insufficient_credentials():
    """If the project access has not been granted, the public key should not be provided."""

    token = user.User(username="admin", password="password").token
    response = requests.get(
        dds_cli.DDSEndpoint.PROJ_PUBLIC, params={"project": "public_project_id"}, headers=token
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    response_json = response.json()
    assert "not have permission" in response_json.get("message")


def test_project_public_researcher_get():
    """User should get access to public key"""

    token = user.User(username="username", password="password").token
    response = requests.get(
        dds_cli.DDSEndpoint.PROJ_PUBLIC, params={"project": "public_project_id"}, headers=token
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json()
    assert response_json.get("public")


def test_project_public_facility_put():
    """User should get access to public key"""

    token = user.User(username="facility", password="password").token
    response = requests.get(
        dds_cli.DDSEndpoint.PROJ_PUBLIC, params={"project": "public_project_id"}, headers=token
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json()
    assert response_json.get("public")
