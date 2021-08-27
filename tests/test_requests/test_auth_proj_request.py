# IMPORTS ################################################################################ IMPORTS #
# Standard library

# Installed
import pytest
import requests

# Own modules
import dds_cli
import tests.tools.tools_for_testing

# VARIABLES ############################################################################ VARIABLES #

# username
valid_token_no_project = tests.tools.tools_for_testing.get_valid_token()
valid_token_invalid_project = tests.tools.tools_for_testing.get_valid_token(project="incorrect")
valid_token_valid_project_no_access = tests.tools.tools_for_testing.get_valid_token(
    project="access_denied"
)
valid_token_valid_project = tests.tools.tools_for_testing.get_valid_token(project="correct")

# facility
valid_token_valid_project_facility = tests.tools.tools_for_testing.get_valid_token(
    project="correct", facility=True
)

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


def test_auth_proj_correct_project_put_researcher():
    """Researcher (current user) should not have upload permissions"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ, headers=valid_token_valid_project, params={"method": "put"}
    )
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "User does not have permission to `put`" in response_json.get("message")


def test_auth_proj_correct_project_rm_researcher():
    """Researcher (current user) should not have upload permissions"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ, headers=valid_token_valid_project, params={"method": "rm"}
    )
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "User does not have permission to `rm`" in response_json.get("message")


def test_auth_proj_no_access_to_project():
    """Researcher should not be granted access to project"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ,
        headers=valid_token_valid_project_no_access,
        params={"method": "ls"},
    )
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "Project access denied" in response_json.get("message")


def test_auth_proj_access_granted_ls():
    """Researcher should be able to list"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ, headers=valid_token_valid_project, params={"method": "ls"}
    )
    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("dds-access-granted")
    assert response_json.get("token")


def test_auth_proj_access_granted_get():
    """Researcher should be able to list"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ, headers=valid_token_valid_project, params={"method": "get"}
    )
    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("dds-access-granted")
    assert response_json.get("token")


def test_auth_proj_access_not_granted_get_facility():
    """Facility user should not be able to get"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ,
        headers=valid_token_valid_project_facility,
        params={"method": "get"},
    )
    assert response.status_code == 400
    response_json = response.json()
    assert response_json.get("message")
    assert "User does not have permission to `get`" in response_json.get("message")


def test_auth_proj_access_granted_facility_ls():
    """Facility user should not be able to ls"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ,
        headers=valid_token_valid_project_facility,
        params={"method": "ls"},
    )
    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("dds-access-granted")
    assert response_json.get("token")


def test_auth_proj_access_granted_facility_put():
    """Facility user should not be able to put"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ,
        headers=valid_token_valid_project_facility,
        params={"method": "put"},
    )
    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("dds-access-granted")
    assert response_json.get("token")


def test_auth_proj_access_granted_facility_rm():
    """Facility user should not be able to rm"""

    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ,
        headers=valid_token_valid_project_facility,
        params={"method": "rm"},
    )
    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("dds-access-granted")
    assert response_json.get("token")
