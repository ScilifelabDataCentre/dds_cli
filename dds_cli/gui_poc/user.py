from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.widget import Widget
from textual.widgets import ContentSwitcher, DataTable
from dds_cli.account_manager import AccountManager
from dds_cli.gui_poc.utils import DDSSidebar


help_text = """
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

class UserInfo(Widget):
    def __init__(self, user_info: dict):
        super().__init__()
        self.user_info = user_info
        
    def compose(self) -> ComposeResult:
        with Container(id="user-info"):
            yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_column("Key")
        table.add_column("Value")
        for key, value in self.user_info.items():
            table.add_row(key, value)


class User(Widget):
    def __init__(self):
        super().__init__()
        self.user = AccountManager()
        self.id = "user"

    def compose(self) -> ComposeResult:
        yield DDSSidebar([
            "info"

        ], help_text)
        with ContentSwitcher(initial="info", id="user"):
            with Container(id="info"):
                yield UserInfo(self.user.get_user_info())

    def on_button_pressed(self, event: events.Click) -> None:
        if event.button.id == "info":
            self.query_one(ContentSwitcher).current = "info"


        
        
        
        