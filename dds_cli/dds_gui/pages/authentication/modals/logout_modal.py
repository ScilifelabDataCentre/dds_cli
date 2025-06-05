"""DDS Logout Modal"""

from typing import Any

from dds_cli.dds_gui.components.dds_modal import DDSModalConfirmation
from dds_cli.dds_gui.types.dds_severity_types import DDSSeverity


class LogoutModal(DDSModalConfirmation):
    """A widget for the logout modal."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(
            title="Logout",
            message="Are you sure you want to logout?",
            confirm_button_text="Logout",
            confirm_severity=DDSSeverity.WARNING,
            confirm_action=self.logout,
            *args,
            **kwargs,
        )

    def logout(self) -> None:
        """Logout the user."""
        self.app.auth.logout()  # Do the logout action
        self.app.set_auth_status(False)
        self.app.notify("Successfully logged out.")
        self.close_modal()
