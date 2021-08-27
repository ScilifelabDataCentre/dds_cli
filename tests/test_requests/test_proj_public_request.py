# IMPORTS ################################################################################ IMPORTS #
# Standard library

# Installed
import pytest
import requests

# Own modules
import dds_cli
import tests.tools.tools_for_testing

# VARIABLES ############################################################################ VARIABLES #


# TESTS #################################################################################### TESTS #


def test_proj_public_no_token():
    """Attempting to get the public key without a project id should not work"""

    response = requests.get(dds_cli.DDSEndpoint.PROJ_PUBLIC)
    assert response.status_code == 400
    response_json = response.json()
    assert "JWT Token not found" in response_json.get("message")


def test_proj_public_no_project():
    """Attempting to get public key for none project should be caught in the
    project_access_required decorator"""

    token = tests.tools.tools_for_testing.get_valid_token(project=None)
    response = requests.get(dds_cli.DDSEndpoint.PROJ_PUBLIC, headers=token)
    assert response.status_code == 500
    response_json = response.json()
    assert "Project ID not found." in response_json.get("message")


def test_proj_public_not_yet_verified():
    """If the project access has not been granted, the public key should not be provided."""

    token = tests.tools.tools_for_testing.get_valid_token(project="correct")
    response = requests.get(dds_cli.DDSEndpoint.PROJ_PUBLIC, headers=token)
    assert response.status_code == 500
    response_json = response.json()
    assert "not yet verified" in response_json.get("message")


def test_project_public_researcher_get():
    """User should get access to public key"""

    token = tests.tools.tools_for_testing.get_valid_token_project_included_get()
    response = requests.get(dds_cli.DDSEndpoint.PROJ_PUBLIC, headers=token)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("public")


def test_project_public_facility_put():
    """User should get access to public key"""

    token = tests.tools.tools_for_testing.get_valid_token_project_included_put()
    response = requests.get(dds_cli.DDSEndpoint.PROJ_PUBLIC, headers=token)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("public")
