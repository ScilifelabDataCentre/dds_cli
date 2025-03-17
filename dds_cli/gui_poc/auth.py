from prompt_toolkit.layout import VerticalAlign
from textual.binding import Binding
from dds_cli.auth import Auth
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Label, Input
from textual import events  
from textual.widget import Widget   

class AuthStatus(Widget):
    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        with Container(id="auth-status"):
            yield Label(self.auth.check())


class LoginStep(Widget):
    def __init__(self, auth: Auth, token_path: str):
        super().__init__()
        self.auth = auth
        self.token_path = token_path
    
    def compose(self) -> ComposeResult:
        with Container(id="login-step"):
            yield Input(placeholder="Username", id="username")
            yield Input(placeholder="Password", id="password")
            yield Button("Login", id="login", variant="primary")
        
class TwoFactorStep(Widget):    
    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        with Container(id="two-factor-step"):   
                yield Input(placeholder="2FA Code", id="code")
                yield Button("Complete Login", id="complete-login")

class AuthLogin(Widget):
    def __init__(self, token_path: str):
        super().__init__()
        self.auth = None
        self.token_path = token_path

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="auth-login"):
            yield LoginStep(self.auth, self.token_path)
    
    def on_button_pressed(self, event: events.Click) -> None:
        if event.button.id == "login":
            username = self.query_one("#username").value
            password = self.query_one("#password").value

            self.auth = "Login" #Auth(authenticate=False, 
                         #   authenticate_gui=True, 
                         #   token_path=self.token_path,
                         #   username_gui=username, 
                         #   password_gui=password)

            if self.auth: 
                self.query_one("#auth-login").mount(TwoFactorStep(self.auth))
                         
        if event.button.id == "complete-login":
            code = self.query_one("#code").value
            self.auth.do_2factor(code)


class AuthLogout(Widget):
    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        with Vertical(id="auth-logout"):
            yield Container(Label("Are you sure you want to logout? If not, press close."), id="auth-logout-message")
            with Container(id="auth-logout-buttons"):
                yield Button("Logout", variant="warning")


