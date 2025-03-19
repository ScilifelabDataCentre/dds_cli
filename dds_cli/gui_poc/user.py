from textual.app import ComposeResult
from textual.widgets import Widget, Label
from dds_cli.account_manager import AccountManager

class UserInfo(Widget):
    def __init__(self):
        super().__init__()
        self.user = AccountManager()

    def compose(self) -> ComposeResult:
        yield Label(self.user.get_user_info())
        
        
        
        