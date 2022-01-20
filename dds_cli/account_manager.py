"""Admin class, adds ."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
import logging

# Installed
import http
import requests
import simplejson


# Own modules
import dds_cli
import dds_cli.auth
import dds_cli.base
import dds_cli.exceptions


####################################################################################################
# START LOGGING CONFIG ###################################################### START LOGGING CONFIG #
####################################################################################################

LOG = logging.getLogger(__name__)


####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


class AccountManager(dds_cli.base.DDSBaseClass):
    """Admin class for adding users, etc."""

    def __init__(
        self, username: str, authenticate: bool = True, method: str = "add", no_prompt: bool = False
    ):
        """Initialize, incl. user authentication."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            username=username, authenticate=authenticate, method=method, no_prompt=no_prompt
        )

        # Only methods "add", "delete" and "revoke" can use the AccountManager class
        if self.method not in ["add", "delete", "revoke", "key"]:
            raise dds_cli.exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    def add_user(self, email, role, project):
        """Invite new user or associate existing users with projects."""
        # Perform request to API
        json = {"email": email, "role": role}
        if project:
            json["project"] = project
        try:
            response = requests.post(
                dds_cli.DDSEndpoint.USER_ADD,
                headers=self.token,
                json=json,
            )

            # Get response
            response_json = response.json()
            LOG.debug(response_json)
        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Format response message
        if not response.ok:
            message = "Could not add user"
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            raise dds_cli.exceptions.DDSCLIException(
                message=f"{message}: {response_json.get('message', 'Unexpected error!')}"
            )

        LOG.info(response_json.get("message", "User successfully added."))

    def delete_user(self, email):
        """Delete users from the system"""
        # Perform request to API
        json = {"email": email}

        try:
            response = requests.delete(
                dds_cli.DDSEndpoint.USER_DELETE,
                headers=self.token,
                json=json,
            )

            # Get response
            response_json = response.json()
            message = response_json["message"]

        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Format response message
        if not response.ok:
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message)
            else:
                raise dds_cli.exceptions.DDSCLIException(message)
        else:
            LOG.info(message)

    def delete_own_account(self):
        """Delete users from the system"""
        # Perform request to API

        try:
            response = requests.delete(
                dds_cli.DDSEndpoint.USER_DELETE_SELF,
                headers=self.token,
                json=None,
            )

            # Get response
            response_json = response.json()
            message = response_json["message"]

        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Format response message
        if not response.ok:
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message)
            else:
                raise dds_cli.exceptions.DDSCLIException(message)
        else:
            LOG.info(message)

    def revoke_project_access(self, project, email):
        """Revoke a user's access to a project"""
        json = {"email": email, "project": project}
        try:
            response = requests.post(
                dds_cli.DDSEndpoint.REVOKE_PROJECT_ACCESS,
                headers=self.token,
                json=json,
            )

            # Get response
            response_json = response.json()
            LOG.debug(response_json)
        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Format response message
        if not response.ok:
            message = "Could not revoke user access"
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            raise dds_cli.exceptions.DDSCLIException(
                message=f"{message}: {response_json.get('message', 'Unexpected error!')}"
            )

        LOG.info(response_json.get("message", "User access successfully revoked."))

    def get_user_info(self):
        """Get a users info"""
        try:
            response = requests.get(
                dds_cli.DDSEndpoint.DISPLAY_USER_INFO,
                headers=self.token,
            )

            # Get response
            response_json = response.json()
            LOG.debug(response_json)
            info = response_json["info"]
        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Format response message
        if not response.ok:
            message = "Could not get user info"
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            raise dds_cli.exceptions.DDSCLIException(
                message=f"{message}: {response_json.get('message', 'Unexpected error!')}"
            )

        LOG.info(
            f"User Name: {info['username']} \nRole: {info['role']} \
            \nName: {info['name']} \
            \nPrimary Email: {info['email_primary']} \
            \nAssociated Emails: {', '.join(str(x) for x in info['emails_all'])}"
        )

    def gen_user_keys(self):
        # generate keys - this is just an example
        public_key = "public_key"
        private_key = "private_key"

        # Save private key to file (and encrypt with password derived key...?)
        # Also just an example, this will be done in a different way
        with open("private_key.txt", "w") as keyfile:
            keyfile.write(private_key)

        # post public key to dds
        try:
            response = requests.post(
                dds_cli.DDSEndpoint.USER_PUBLIC, headers=self.token, json={"public": public_key}
            )
        except Exception as err:
            raise dds_cli.exceptions.APIError

        if not response.ok:
            raise dds_cli.exceptions.APIError

        LOG.info(response.json())

    def reset_user_keys(self):
        # Generate new keys
        public_key = "public_key"
        private_key = "private_key"

        # Save private key temporarily to file (and encrypt with password derived key...?)
        # Also just an example, this will be done in a different way
        with open("private_key_temp.txt", "w") as keyfile:
            keyfile.write(private_key)

        # put public key to dds
        try:
            response = requests.put(
                dds_cli.DDSEndpoint.USER_PUBLIC, headers=self.token, json={"public": public_key}
            )
        except Exception as err:
            raise dds_cli.exceptions.APIError

        if not response.ok:
            raise dds_cli.exceptions.APIError

        LOG.info(response.json())

        # 1. delete old private key file
        # 2. rename private key file

    def renew_access(self, email):
        """ """
        # 1. Get current user project private keys and the user with the email's public key
        # 2. Decrypt with user private key
        # 3. Encrypt with new user public key
        # 4. Send back public_key and project private keys
