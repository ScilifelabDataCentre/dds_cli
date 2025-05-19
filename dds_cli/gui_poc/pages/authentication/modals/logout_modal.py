from dds_cli.gui_poc.components.dds_modal import DDSModalConfirmation
from typing import Any

from dds_cli.gui_poc.types.dds_severity_types import DDSSeverity

class LogoutModal(DDSModalConfirmation):
    """A widget for the logout modal."""

    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(title="Logout", message="Are you sure you want to logout?", confirm_button_text="Logout", confirm_severity=DDSSeverity.WARNING, confirm_action=self.logout, *args, **kwargs)
        self.token_path = token_path
        #self.auth = Auth(token_path=self.token_path, authenticate=False)

    def logout(self) -> None:
        """Logout the user."""
        self.app.auth.logout() #Do the logout action
        self.app.compute_auth_status() #Compute the auth status
        self.app.notify("Successfully logged out.")


