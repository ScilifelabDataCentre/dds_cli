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
        self,
        authenticate: bool = True,
        method: str = "add",
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Initialize, incl. user authentication."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            authenticate=authenticate,
            method=method,
            no_prompt=no_prompt,
            token_path=token_path,
        )

        # Only methods "add", "delete" and "revoke" can use the AccountManager class
        if self.method not in ["add", "delete", "revoke"]:
            raise dds_cli.exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    def add_user(self, email, role, project, unit=None, no_mail=False):
        """Invite new user or associate existing users with projects."""
        # Perform request to API
        json = {"email": email, "role": role, "send_email": not no_mail, "unit": unit}

        try:
            response = requests.post(
                dds_cli.DDSEndpoint.USER_ADD,
                headers=self.token,
                params={"project": project},
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

        dds_cli.utils.console.print(response_json.get("message", "User successfully added."))

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
        """Delete users from the system."""
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
            dds_cli.auth.Auth.logout()

        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Format response message
        if not response.ok:
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message)

            raise dds_cli.exceptions.DDSCLIException(message)

        LOG.info(message)

    def revoke_project_access(self, project, email):
        """Revoke a user's access to a project."""
        json = {"email": email}
        try:
            response = requests.post(
                dds_cli.DDSEndpoint.REVOKE_PROJECT_ACCESS,
                headers=self.token,
                params={"project": project},
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

        dds_cli.utils.console.print(
            response_json.get("message", "User access successfully revoked.")
        )

    def get_user_info(self):
        """Get a users info."""
        try:
            response = requests.get(
                dds_cli.DDSEndpoint.DISPLAY_USER_INFO,
                headers=self.token,
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
            message = "Could not get user info"
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            raise dds_cli.exceptions.DDSCLIException(
                message=f"{message}: {response_json.get('message', 'Unexpected error!')}"
            )

        info = response_json.get("info")
        if info:
            LOG.info(
                f"User Name: {info['username']} \nRole: {info['role']} \
                \nName: {info['name']} \
                \nPrimary Email: {info['email_primary']} \
                \nAssociated Emails: {', '.join(str(x) for x in info['emails_all'])}"
            )

    def user_activation(self, email, action):
        """Deactivate/Reactivate users"""
        json = {"email": email, "action": action}
        try:
            response = requests.post(
                dds_cli.DDSEndpoint.USER_ACTIVATION,
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
            message = f"Could not {action} user"
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            raise dds_cli.exceptions.DDSCLIException(
                message=f"{message}: {response_json.get('message', 'Unexpected error!')}"
            )

        LOG.info(response_json.get("message", f"User successfully {action}d."))

    def fix_project_access(self, email, project):
        """Fix project access for specific user."""
        json = {"email": email}
        try:
            response = requests.post(
                dds_cli.DDSEndpoint.PROJ_ACCESS,
                headers=self.token,
                params={"project": project},
                json=json,
            )
            response_json = response.json()

        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        if not response.ok:
            message = f"Failed updating user '{email}' project access"
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            raise dds_cli.exceptions.DDSCLIException(
                message=f"{message}: {response_json.get('message', 'Unexpected error!')}"
            )

        LOG.info(
            response_json.get(
                "message",
                (
                    f"Project access fixed for user '{email}'. "
                    "They should now have access to all project data."
                ),
            )
        )
