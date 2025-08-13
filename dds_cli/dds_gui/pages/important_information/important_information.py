"""Important information widget"""

from typing import Any, List, Dict
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Label

from dds_cli.dds_gui.components.dds_container import DDSContainer, DDSSpacedContainer
from dds_cli.dds_gui.pages.important_information.components.motd_card import MOTDCard
from dds_cli.exceptions import ApiRequestError, ApiResponseError, DDSCLIException, NoMOTDsError
from dds_cli.motd_manager import MotdManager


class ImportantInformation(DDSContainer):
    """Important information widget displaying message of the day. Fetches new MOTDs every hour."""

    # Reactive variable for MOTDs - will trigger recomposition only when the content changes
    motds: reactive[List[Dict[str, str]]] = reactive(None, recompose=True)

    def __init__(self, title: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(title=title, *args, **kwargs)
        self.motd_timer: Timer = None

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer(id="motd-container"):
            if self.motds:
                # Display the latest MOTD first
                for motd in reversed(self.motds):
                    yield MOTDCard(motd["Created"], motd["Message"])
            else:
                yield Label("No important information to display.")

    def on_mount(self) -> None:
        """Initialize the hourly timer for fetching MOTDs when the widget is mounted."""
        # Set up timer to fetch MOTDs every hour (3600 seconds)
        self.motd_timer = self.set_interval(3600, self.fetch_motds)

        # Fetch MOTDs immediately on mount
        self.fetch_motds()

    def on_unmount(self) -> None:
        """Clean up the timer when the widget is unmounted."""
        if self.motd_timer:
            self.motd_timer.stop()

    def fetch_motds(self) -> None:
        """
        Fetch MOTDs from Motd Manager and update the display.
        """
        try:
            # Reactive assignment - will only trigger recomposition if data actually changes
            self.motds = MotdManager.list_all_active_motds(table=False)
        except (ApiResponseError, ApiRequestError, DDSCLIException) as api_err:
            self.notify(f"Failed to fetch MOTDs: {api_err}", severity="error")
        except NoMOTDsError as no_motds_err:
            self.notify(f"No MOTDs available: {no_motds_err}", severity="information")

    def update_motds(self, new_motds: List[Dict[str, str]]) -> None:
        """
        Update the MOTDs using reactive assignment.
        """
        # Simple reactive assignment - Textual handles the rest
        self.motds = new_motds

        # Notify when new MOTDs are available
        self.notify("New important information available", severity="information")
