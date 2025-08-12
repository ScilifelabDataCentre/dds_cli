"""Important information widget"""

from typing import Any, List, Dict
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.timer import Timer

from dds_cli.dds_gui.components.dds_container import DDSContainer, DDSSpacedContainer
from dds_cli.dds_gui.pages.important_information.components.motd_card import MOTDCard

MOTDS = [
    {
        "title": "2025-08-07 09:38 ",
        "message": "Extra maintenance window planned for Thursday August 14th at 10-12. The reason for this is that we have fixed an issue with the project status flow. More information will be available in the changelogs after the new version release. If you have any questions, contact delivery@scilifelab.se. We applogize for any inconvenience caused by this extra maintenance window.",
    },
    {
        "title": "2025-02-07 11:13",
        "message": "Important! Data download on Dardel: For data downloads on Dardel, please log into the dedicated file transfer node: dardel-ftn01.pdc.kth.se. Do NOT submit data-transfer jobs to the queueing system, run them directly on that node.",
    },
]


class ImportantInformation(DDSContainer):
    """Important information widget displaying message of the day. Fetches new MOTDs every hour."""

    # Reactive variable for MOTDs - will trigger recomposition only when the content changes
    motds: reactive[List[Dict[str, str]]] = reactive(MOTDS, recompose=True)

    def __init__(self, title: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(title=title, *args, **kwargs)
        self.motd_timer: Timer = None

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer(id="motd-container"):
            for motd in self.motds:
                yield MOTDCard(motd["title"], motd["message"])

    def on_mount(self) -> None:
        """Initialize the hourly timer for fetching MOTDs when the widget is mounted."""
        # Set up timer to fetch MOTDs every hour (3600 seconds)
        self.motd_timer = self.set_interval(60, self.fetch_motds)

        # Optionally fetch MOTDs immediately on mount
        # self.fetch_motds()

    def on_unmount(self) -> None:
        """Clean up the timer when the widget is unmounted."""
        if self.motd_timer:
            self.motd_timer.stop()

    async def fetch_motds(self) -> None:
        """
        Fetch MOTDs from API and update the display.

        This method will replace the static MOTDS with an API call.
        For now, it serves as a placeholder that could refresh the static data.
        """
        # TODO: Replace this with actual API call
        # Example API call structure:
        # try:
        #     response = await api_client.get_motds()
        #     new_motds = response.json()
        #     # Reactive assignment - will only trigger recomposition if data actually changes
        #     self.motds = new_motds
        # except Exception as e:
        #     self.app.notify(f"Failed to fetch MOTDs: {e}", severity="error")

        # For now, just assign the static data - reactivity will prevent unnecessary updates
        self.motds = MOTDS

    def update_motds(self, new_motds: List[Dict[str, str]]) -> None:
        """
        Update the MOTDs using reactive assignment.

        This method is now simplified - the reactive system handles the UI updates
        automatically and only triggers recomposition when the data actually changes.
        """
        # Simple reactive assignment - Textual handles the rest
        self.motds = new_motds

        # Notify when new MOTDs are available
        self.app.notify("New important information available", severity="warning")
