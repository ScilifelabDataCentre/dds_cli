"""Admin class, adds ."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
import logging

# Installed
import http
import requests
import rich.markup
from rich.table import Table
import simplejson

# Own modules
import dds_cli
import dds_cli.auth
import dds_cli.base
import dds_cli.exceptions
import dds_cli.utils


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
                timeout=dds_cli.DDSEndpoint.TIMEOUT,
            )

            # Get response
            response_json = response.json()
            LOG.debug(response_json)
        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        errors = response_json.get("errors")
        error_messages = dds_cli.utils.parse_project_errors(errors=errors)

        # Format response message
        if not response.ok:
            message = "Could not add user"
            message += ": " + response_json.get("message", "Unexpected error!")
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message=message)

            show_warning = True
            if error_messages:
                message += f"\n{error_messages}"
                show_warning = False

            raise dds_cli.exceptions.DDSCLIException(
                message=message,
                show_emojis=show_warning,
            )

        if error_messages:
            LOG.warning(f"Could not give the user '{email}' access to the following projects:")
            msg = error_messages
        else:
            msg = response_json.get("message", "User successfully added.")

        LOG.info(msg)

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
            dds_cli.auth.Auth.logout(self)

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
                timeout=dds_cli.DDSEndpoint.TIMEOUT,
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
                timeout=dds_cli.DDSEndpoint.TIMEOUT,
            )

            # Get response
            response_json = response.json()
            for field in response_json.get("info", []):
                if isinstance(response_json["info"][field], str):
                    response_json["info"][field] = rich.markup.escape(response_json["info"][field])
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
                timeout=dds_cli.DDSEndpoint.TIMEOUT,
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

            response_message = response_json.get("message", "Unexpected error!")
            if "Insufficient credentials" in response_message:
                response_message = f"You do not have the required permissions to {action} a user."
            raise dds_cli.exceptions.DDSCLIException(message=f"{message}: {response_message}")

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
                timeout=dds_cli.DDSEndpoint.TIMEOUT,
            )
            response_json = response.json()

        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        errors = response_json.get("errors")
        error_messages = dds_cli.utils.parse_project_errors(errors=errors)

        if not response.ok:
            message = f"Failed updating user '{email}' project access"
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            message += ": " + response_json.get("message", "Unexpected error!")
            show_warning = True
            if error_messages:
                message += f"\n{error_messages}"
                show_warning = False

            raise dds_cli.exceptions.DDSCLIException(message=message, show_emojis=show_warning)

        if error_messages:
            LOG.warning(f"Could not fix user '{email}' access to the following projects:")
            msg = error_messages
        else:
            msg = response_json.get(
                "message",
                (
                    f"Project access fixed for user '{email}'. "
                    "They should now have access to all project data."
                ),
            )

    def list_unit_users(self, unit: str = None) -> None:
        """List all unit users within a specific unit."""
        response = dds_cli.utils.request_get(
            endpoint=dds_cli.DDSEndpoint.LIST_UNIT_USERS,
            headers=self.token,
            json={"unit": unit},
            error_message="Failed getting unit users from API",
        )

        users, keys, unit = dds_cli.utils.get_required_in_response(
            keys=["users", "keys", "unit"], response=response
        )

        # Sort users according to name
        users = dds_cli.utils.sort_items(items=users, sort_by="Name")

        # Create table
        table = dds_cli.utils.create_table(
            title=f"Unit Admins and Personnel within {f'unit: {unit}' or 'your unit'}.",
            columns=keys,
            rows=users,
            caption="All users (Unit Personnel and Admins) within your unit.",
        )

        # Print out table
        dds_cli.utils.print_or_page(item=table)
