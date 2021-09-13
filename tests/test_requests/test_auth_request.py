# IMPORTS ################################################################################ IMPORTS #
# Standard library
import http

# Installed
import requests
import jwt

# Own modules
import dds_cli


# TESTS #################################################################################### TESTS #


def test_auth_check_statuscode_401_missing_info():
    """
    Test that the auth endpoint returns:
    Status code: 401/UNAUTHORIZED
    Message: Missing or incorrect credentials
    """

    # No params, no auth
    response = requests.get(dds_cli.DDSEndpoint.TOKEN)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json()
    assert response_json.get("message")
    assert "Missing or incorrect credentials" in response_json.get("message")


def test_auth_incorrect_username_check_statuscode_401_incorrect_info():
    """Test that the auth endpoint returns
    Status code: 401/UNAUTHORIZED
    Message: Missing or incorrect credentials
    """

    response = requests.get(dds_cli.DDSEndpoint.TOKEN, auth=("incorrect_username", "password"))
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json()
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_incorrect_username_and_password_check_statuscode_400_incorrect_info():
    """Test that the auth endpoint returns
    Status code: 401/UNAUTHORIZED
    Message: Missing or incorrect credentials
    """

    response = requests.get(dds_cli.DDSEndpoint.TOKEN, auth=("incorrect_username", "incorrect_password"))
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json()
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_incorrect_password_check_statuscode_400_incorrect_info():
    """Test that the auth endpoint returns
    Status code: 401/UNAUTHORIZED
    Message: Missing or incorrect credentials
    """

    response = requests.get(dds_cli.DDSEndpoint.TOKEN, auth=("username", "incorrect_password"))
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json()
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_correctauth_check_statuscode_200_correct_info():
    """Test that the auth endpoint returns
    Status code: 200/OK
    Token: including the authenticated username
    """

    response = requests.get(dds_cli.DDSEndpoint.TOKEN, auth=("username", "password"))
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json()
    assert response_json.get("token")
    decoded_token = jwt.decode(response_json.get("token"), options={"verify_signature": False})
    assert "username" == decoded_token.get("user")
