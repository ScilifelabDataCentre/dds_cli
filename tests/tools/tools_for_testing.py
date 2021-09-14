# IMPORTS ################################################################################ IMPORTS #

# Standard library
import requests

# Installed

# Own modules
import dds_cli

# VARIABLES ############################################################################ VARIABLES #

projects = {
    "correct": "public_project_id",
    "incorrect": "incorrect_project_id",
    "access_denied": "unused_project_id",
}

# FUNCTIONS ############################################################################ FUNCTIONS #


def get_valid_token(project=None, facility=False):
    """Requests user access to DDS"""

    auth_info = ("username", "password")
    if facility:
        auth_info = ("facility", "password")
    # Get token from (tested in test_auth_request) authorization endpoint
    response = requests.get(
        dds_cli.DDSEndpoint.AUTH,
        auth=auth_info,
        params={"project": projects.get(project)} if project else project,
    )
    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("token")
    assert response_json.get("token") != ""

    return {"x-access-token": response_json.get("token")}


def get_valid_token_project_included_get():
    """Requests user access to DDS followed by project access"""

    token = get_valid_token(project="correct")
    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ,
        headers=token,
        params={"method": "get"},
    )

    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("token")
    assert response_json.get("token") != ""

    return {"x-access-token": response_json.get("token")}


def get_valid_token_project_included_put():
    """Requests user access to DDS followed by project access"""

    token = get_valid_token(project="correct", facility=True)
    response = requests.get(
        dds_cli.DDSEndpoint.AUTH_PROJ,
        headers=token,
        params={"method": "put"},
    )

    assert response.status_code == 200
    response_json = response.json()
    assert response_json.get("token")
    assert response_json.get("token") != ""

    return {"x-access-token": response_json.get("token")}
