"""User widgets."""

from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import ContentSwitcher, DataTable
from dds_cli.account_manager import AccountManager
from dds_cli.gui_poc.utils import DDSSidebar


HELP_TEXT = """
# Help

This is the help text for the different screens. This is written in markdown.

## Markdown example 

This is a markdown example.

### More examples 

- Item 1
- Item 2
- Item 3

| Syntax      | Description |
| ----------- | ----------- |
| Header      | Title       |
| Paragraph   | Text        |

[Link](https://www.google.com)

```json
{
  "firstName": "John",
  "lastName": "Smith",
  "age": 25
}
```
"""


class UserInfoTable(DataTable):
    """User info table widget."""

    def __init__(self, user: AccountManager):
        super().__init__()
        self.user = user
        self.user_info = None

    def on_mount(self) -> None:
        try:
            self.user_info = self.user.get_user_info()
        except Exception as e:
            self.user_info = {"Not authenticated": "Please login to DDS."}

        if self.user_info:
            self.add_column("Key")
            self.add_column("Value")
            for key, value in self.user_info.items():
                self.add_row(key, value)


class UserInfo(Widget):
    """User info widget."""

    DEFAULT_CSS = """
    #user-info {
    align: center middle;
    margin: 1;
}
    """

    def __init__(self, user: AccountManager):
        super().__init__()
        self.user = user

    def compose(self) -> ComposeResult:
        with Container(id="user-info"):
            yield UserInfoTable(self.user)


class User(Widget):
    """User widget."""

    DEFAULT_CSS = """
    #user {
    align: center middle;
    width: 100%; 
}
    """

    def __init__(self):
        super().__init__()
        self.id = "user"

    user = reactive(None, recompose=True)

    def compose(self) -> ComposeResult:
        yield DDSSidebar(["info"], HELP_TEXT)
        with ContentSwitcher(initial="info", id="user"):
            with Container(id="info"):
                yield UserInfo(self.user)

    def on_button_pressed(self, event: events.Click) -> None:
        """Handles button presses."""
        if event.button.id == "info":
            self.query_one(ContentSwitcher).current = "info"
