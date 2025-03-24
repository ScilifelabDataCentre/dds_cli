from dds_cli.account_manager import AccountManager
from dds_cli.auth import Auth
from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Button, Label, Input
from textual import events  
from textual.widget import Widget


class AuthStatus(Widget):
    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        with Container(id="auth-status"):
            yield Label(self.get_status())

    def get_status(self) -> str:
        return self.auth.check() or "Not authenticated"

class LoginStep(Widget):
    def __init__(self, auth: Auth, token_path: str):
        super().__init__()
        self.auth = auth
        self.token_path = token_path
    
    def compose(self) -> ComposeResult:
        with Container(id="login-step"):
            yield Input(placeholder="Username", id="username")
            yield Input(placeholder="Password", id="password", password=True)
            yield Button("Login", id="login", variant="primary")
        
class TwoFactorStep(Widget):    
    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        with Container(id="two-factor-step"):   
                yield Input(placeholder="2FA Code", id="code")
                yield Button("Complete Login", id="complete-login", variant="primary")

class AuthLogin(Widget):
    def __init__(self, token_path: str):
        super().__init__()
        self.auth = None
        self.token_path = token_path

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="auth-login"):
            yield Label("Authenticate yourself towards SciLifeLab Data Delivery System.", id="auth-login-message")
            yield LoginStep(self.auth, self.token_path)
    
    def on_button_pressed(self, event: events.Click) -> None:
        if event.button.id == "login":
            username = self.query_one("#username").value
            password = self.query_one("#password").value

            self.auth = Auth(authenticate=False, 
                         authenticate_gui=True, 
                         token_path=self.token_path,
                         username_gui=username, 
                         password_gui=password)

            if self.auth: 
                self.query_one("#login-step").remove()
                self.query_one("#auth-login").mount(TwoFactorStep(self.auth))
                self.notify("Two factor code sent to email.")
                         
        if event.button.id == "complete-login":
            code = self.query_one("#code").value
            self.auth.do_2factor(code)
            self.query_one("#complete-login").remove()
            self.notify("Successfully logged in.")
          


class AuthLogout(Widget):
    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        with Vertical(id="auth-logout"):
            yield Container(Label("Are you sure you want to logout? If not, press close."), id="auth-logout-message")
            with Container(id="auth-logout-buttons"):
                yield Button("Logout", variant="warning", id="logout")

    def on_button_pressed(self, event: events.Click) -> None:
        if event.button.id == "logout":
            logout = self.auth.logout()
            self.query_one("#auth-logout-buttons").disabled = True
            if logout:
                self.notify("Successfully logged out.")
            else:
                self.notify("Already logged out.")


