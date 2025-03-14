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
    def on_mount(self) -> None:
        pass
        #self.query_one(Label).update(f"Auth Status: {self.auth.check()}")

class AuthLogin(ModalScreen):
    def __init__(self, auth: Auth, token_path: str):
        super().__init__()
        self.auth = auth
        self.token_path = token_path

     
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Username", id="username")
        yield Input(placeholder="Password", id="password")
        yield Button("Login", id="login")
        yield Input(placeholder="2FA Code", id="code")
        yield Button("Complete Login", id="complete-login")

    def on_button_pressed(self, event: events.Click) -> None:
        if event.button.id == "login":
            username = self.query_one("#username").value
            password = self.query_one("#password").value
            self.auth = Auth(authenticate=False, 
                            authenticate_gui=True, 
                            token_path=self.token_path,
                            username_gui=username, 
                            password_gui=password)
        elif event.button.id == "complete-login":
            code = self.query_one("#code").value
            self.auth.do_2factor(code)


class AuthLogout(Widget):
    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        with Horizontal(id="auth-logout"):
            yield Button("Refresh", variant="primary")
            yield Button("Logout", variant="warning")

class AuthWidget(Widget):
    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        yield Container(id="auth-widget")

    def on_mount(self) -> None:
        status = self.auth.check()
        if status: 
            self.query_one("#auth-widget").mount(AuthStatus(self.auth))
            self.query_one("#auth-widget").mount(AuthLogout(self.auth))
            
class AuthModal(ModalScreen):
    def __init__(self, auth: Auth, token_path: str):
        super().__init__()
        self.auth = auth
        self.token_path = token_path

    BINDINGS = [
        ("e", "escape", "Escape")
    ]    
        
    def compose(self) -> ComposeResult:
        yield Container(
            AuthWidget(self.auth),
            id="auth-modal"
        ) 
        yield Footer()   

    def on_button_pressed(self, event: events.Click) -> None:
        if event.button.id == "close":
            self.dismiss()

    def action_escape(self) -> None:
        self.dismiss()

