"""Admin class, adds ."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
from email import header
import logging

# Installed
import rich.markup
from rich.table import Table

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

        # try:
        response_json, _ = dds_cli.utils.perform_request(
            dds_cli.DDSEndpoint.USER_ADD,
            method="post",
            headers=self.token,
            params={"project": project},
            json=json,
            error_message="Failed to add user",
        )

        msg = response_json.get("message", "User successfully added.")
        LOG.info(msg)

    def delete_user(self, email, is_invite: bool = False):
        """Delete users from the system"""
        # Perform request to API
        json = {"email": email, "is_invite": is_invite}

        response_json, _ = dds_cli.utils.perform_request(
            dds_cli.DDSEndpoint.USER_DELETE,
            method="delete",
            headers=self.token,
            json=json,
            error_message="Failed to delete user",
        )

        # Get response message
        message = response_json["message"]

        LOG.info(message)

    def delete_own_account(self):
        """Delete users from the system."""
        # Perform request to API
        response_json, _ = dds_cli.utils.perform_request(
            dds_cli.DDSEndpoint.USER_DELETE_SELF,
            method="delete",
            headers=self.token,
            error_message="Failed to request deletion of account",
        )

        # Get response message
        message = response_json["message"]
        dds_cli.auth.Auth.logout(self)

        LOG.info(message)

    def revoke_project_access(self, project, email):
        """Revoke a user's access to a project."""
        json = {"email": email}
        response_json, _ = dds_cli.utils.perform_request(
            dds_cli.DDSEndpoint.REVOKE_PROJECT_ACCESS,
            method="post",
            headers=self.token,
            params={"project": project},
            json=json,
            error_message="Could not revoke user access",
        )

        message = response_json.get("message", "User access successfully revoked.")
        LOG.info(message)

    def get_user_info(self):
        """Get a users info."""
        response, _ = dds_cli.utils.perform_request(
            dds_cli.DDSEndpoint.DISPLAY_USER_INFO,
            headers=self.token,
            method="get",
            error_message="Failed to get user information",
            timeout=dds_cli.DDSEndpoint.TIMEOUT,
        )

        for field in response.get("info", []):
            if isinstance(response["info"][field], str):
                response["info"][field] = rich.markup.escape(response["info"][field])
        LOG.debug(response)

        info = response.get("info")
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
        response_json, _ = dds_cli.utils.perform_request(
            dds_cli.DDSEndpoint.USER_ACTIVATION,
            method="post",
            headers=self.token,
            json=json,
            error_message=f"Failed to {action} user",
        )

        message = response_json.get("message", f"User successfully {action}d.")
        LOG.info(message)

    def fix_project_access(self, email, project):
        """Fix project access for specific user."""
        json = {"email": email}
        response_json, project_errors = dds_cli.utils.perform_request(
            dds_cli.DDSEndpoint.PROJ_ACCESS,
            method="post",
            headers=self.token,
            params={"project": project},
            json=json,
            error_message=f"Failed to fix project access for user '{email}'",
        )

        if project_errors:
            LOG.warning(f"Could not fix user '{email}' access to the following projects:")
            msg = project_errors
        else:
            msg = response_json.get(
                "message",
                (
                    f"Project access fixed for user '{email}'. "
                    "They should now have access to all project data."
                ),
            )

        dds_cli.utils.console.print(msg)

    def list_users(self, unit: str = None) -> None:
        """List all unit users within a specific unit."""
        response, _ = dds_cli.utils.perform_request(
            endpoint=dds_cli.DDSEndpoint.LIST_USERS,
            method="get",
            headers=self.token,
            json={"unit": unit},
            error_message="Failed getting unit users from API",
        )

        if response.get("empty"):
            LOG.info(f"There are no Unit Admins or Unit Personnel connected to unit '{unit}'")
            return

        users, keys = dds_cli.utils.get_required_in_response(
            keys=["users", "keys"], response=response
        )

        # Sort users according to name
        users = dds_cli.utils.sort_items(items=users, sort_by="Name")

        # Specific info if unit returned
        unit = response.get("unit")
        if unit:
            title = f"Unit Admins and Personnel within {f'unit: {unit}' or 'your unit'}."
            caption = "All users (Unit Personnel and Admins) within your unit."
        else:
            title = "All accounts in the DDS."
            caption = "All accounts in the DDS (all roles)."

        table = dds_cli.utils.create_table(
            title=title,
            columns=keys,
            rows=users,
            caption=caption,
        )

        # Print out table
        dds_cli.utils.print_or_page(item=table)

    def find_user(self, user_to_find: str) -> None:
        """List all users with accounts in the DDS."""
        response, _ = dds_cli.utils.perform_request(
            endpoint=dds_cli.DDSEndpoint.USER_FIND,
            method="get",
            headers=self.token,
            json={"username": user_to_find},
            error_message="Failed getting users from API",
        )

        exists = response.get("exists")
        if exists is None:
            raise dds_cli.exceptions.ApiResponseError(
                message="No information returned from API. Could not determine if user account exists."
            )

        LOG.info(
            f"Account exists: {'[blue][bold]Yes[/bold][/blue]' if exists else '[red][bold]No[/bold][/red]'}"
        )
