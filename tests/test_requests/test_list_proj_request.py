# IMPORTS ################################################################################ IMPORTS #
# Standard library

# Installed
import requests
import http

# Own modules
import dds_cli
from dds_cli import user

# TESTS #################################################################################### TESTS #


def test_list_proj_no_token():
    """Token required"""

    response = requests.get(dds_cli.DDSEndpoint.LIST_PROJ)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json()
    assert response_json.get("message")
    assert "Missing or incorrect credentials" in response_json.get("message")


def test_list_proj_access_granted_ls():
    """Researcher should be able to list"""

    token = user.User(username="username", password="password").token
    response = requests.get(dds_cli.DDSEndpoint.LIST_PROJ, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json()
    list_of_projects = response_json.get("project_info")
    assert "public_project_id" == list_of_projects[0].get("Project ID")
