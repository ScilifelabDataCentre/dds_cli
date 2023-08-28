"""Admin class, adds ."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
import logging
import pathlib

# Installed
import rich.markup

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

        info = response.get("info")
        if info:
            LOG.info(
                "Username:          %s \n"
                "Role:              %s \n"
                "Name:              %s \n"
                "Primary Email:     %s \n"
                "Associated Emails: %s \n",
                info["username"],
                info["role"],
                info["name"],
                info["email_primary"],
                ", ".join(str(x) for x in info["emails_all"]),
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
            LOG.warning("Could not fix user '%s' access to the following projects:", email)
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
            LOG.info("There are no Unit Admins or Unit Personnel connected to unit '%s'", unit)
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

    def list_invites(self, invites: bool = None) -> None:
        """List all unit users within a specific unit."""
        response, _ = dds_cli.utils.perform_request(
            endpoint=dds_cli.DDSEndpoint.LIST_INVITED_USERS,
            method="get",
            headers=self.token,
            error_message="Failed getting invites from API",
        )
        title = "Current invites"
        caption = "All invited users where you have access"
        invites = response.get("invites")

        if not invites:
            LOG.info("There are no current invites")
            return

        table = dds_cli.utils.create_table(
            title=title,
            columns=response.get("keys"),
            rows=invites,
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
            "Account exists: [bold]%s[/bold]", "[blue]Yes[/blue]" if exists else "[red]No[/red]"
        )

    def save_emails(self) -> None:
        """Get user emails and save them to a text file."""
        # Get emails from API
        response, _ = dds_cli.utils.perform_request(
            endpoint=dds_cli.DDSEndpoint.USER_EMAILS,
            method="get",
            headers=self.token,
            error_message="Failed getting user emails from the API.",
        )

        # Verify that one of the required pieces of info were returned
        empty = response.get("empty")
        emails = response.get("emails")
        if not empty and not emails:
            raise dds_cli.exceptions.ApiResponseError(
                "No information returned from the API. Could not get user emails."
            )

        if empty:
            LOG.info("There are no user emails to save.")
            return

        # Get list of emails
        emails = response.get("emails")
        LOG.debug("Saving emails to file...")

        # Save emails to file
        email_file: pathlib.Path = pathlib.Path("unit_user_emails.txt")
        with email_file.open(mode="w+", encoding="utf-8") as file:
            file.write("; ".join(emails))

        LOG.info("Saved emails to file: %s", email_file)
