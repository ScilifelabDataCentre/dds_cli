# IMPORTS ################################################################################ IMPORTS #
# Standard library

# Installed
import pytest
import requests

# Own modules
import dds_cli
import tests.tools.tools_for_testing

# VARIABLES ############################################################################ VARIABLES #

correct_project = "public_project_id"
incorrect_project = "incorrect_project_id"

valid_token_no_project = tests.tools.tools_for_testing.get_valid_token()
valid_token_invalid_project = tests.tools.tools_for_testing.get_valid_token(
    project=incorrect_project
)
valid_token_valid_project = tests.tools.tools_for_testing.get_valid_token(project=correct_project)

# TESTS #################################################################################### TESTS #


def test_auth_proj_no_token():
    """Token required by endpoint decorator"""

    response = requests.get(dds_cli.DDSEndpoint.AUTH_PROJ)
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "JWT Token not found in HTTP header" in response_json.get("message")


def test_auth_proj_token_wrong_format():
    """Incorrect token format"""

    # Get token from (tested in test_auth_request) authorization endpoint
    response = requests.get(dds_cli.DDSEndpoint.AUTH, auth=("username", "password"))
    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("token")
    assert response_json.get("token") != ""

    # Test auth_proj access with token but without method - wrong formatted token
    with pytest.raises(AttributeError):
        _ = requests.get(dds_cli.DDSEndpoint.AUTH_PROJ, headers=response_json.get("token"))


def test_auth_proj_no_method():
    """No method specified in request - required"""

    response = requests.get(dds_cli.DDSEndpoint.AUTH_PROJ, headers=valid_token_no_project)
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "No method found in request" in response_json.get("message")


def test_auth_proj_no_project():
    """Project ID required to attempt access"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ, headers=valid_token_no_project, params={"method": "ls"}
    )
    assert response.status_code == 500
    response_json = response.json()
    assert response_json.get("message")
    assert "Attempting to validate users project access without project ID" in response_json.get(
        "message"
    )


def test_auth_proj_incorrect_project():
    """Invalid project attempted"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ, headers=valid_token_invalid_project, params={"method": "ls"}
    )
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "The specified project does not exist" in response_json.get("message")
