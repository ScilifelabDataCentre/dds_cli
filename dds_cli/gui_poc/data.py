"""Data widgets."""

from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, ContentSwitcher, DirectoryTree, Input, TabPane, TabbedContent

from dds_cli.gui_poc.utils import DDSSidebar


class InputWithButton(Container):
    """Input widget with a button."""

    def __init__(self, label: str, id: str):
        super().__init__()
        self.label = label
        self.id = id

    value = reactive(None, recompose=True)

    def compose(self) -> ComposeResult:
        yield Input(value=self.value, id="input-with-button-input", placeholder="Path to file")
        yield Button(self.label, id=self.id, variant="primary")


class PathInputMode(Container):
    """Path input mode widget."""

    def compose(self) -> ComposeResult:
        with Vertical(id="path-input-mode"):
            yield InputWithButton("Done", id="file-selector-mode-button")


class FileSelectorMode(Container):
    """File selector mode widget."""

    def compose(self) -> ComposeResult:
        with Vertical(id="file-selector"):
            yield InputWithButton("Done", id="file-selector-mode-button")
            yield DirectoryTree(path="./")

    def on_button_pressed(self, event: events.Click) -> None:
        """Handles button presses."""
        pass

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handles file selection."""
        event.stop()
        self.query_one(InputWithButton).value = str(event.path)

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Handles directory selection."""
        event.stop()
        self.query_one(InputWithButton).value = str(event.path)


class FileSelector(Widget):
    """File selector widget. Tabbed content with two modes: file selector and classic input."""

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        with TabbedContent(id="file-selector-tabs"):
            with TabPane(title="File Selector Mode"):
                yield FileSelectorMode()
            with TabPane(title="Classic Input Mode"):
                yield PathInputMode()


class Data(Widget):
    """Data widget. Sidebar with a tabbed content for file selector and classic input."""

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        yield DDSSidebar(
            [
                "file-select",
            ],
            title="Data",
        )
        with ContentSwitcher(initial="file-select", id="data"):
            with Container(id="file-select"):
                yield FileSelector()

    def on_button_pressed(self, event: events.Click) -> None:
        """Handles button presses."""
        if event.button.id == "file-select":
            self.query_one(ContentSwitcher).current = "file-select"
