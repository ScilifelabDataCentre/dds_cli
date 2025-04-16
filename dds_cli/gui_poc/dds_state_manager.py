from textual.reactive import reactive

from dds_cli.auth import Auth

class DDSStateManager:
    """
    
    A base class for state managment.
    
    - BASE STATES: States that are directly derived from the cli funcitons.
    - DERIVED STATES: States that are derived from the base states.
    - COMPUTE METHODS: Functions that compute the derived states based on the base states.

    Reciver pattern: 

    --> Reciever/reader classes should use derived classes to get state content.

    def on_mount(self) -> None:
        self.watch_state(self.auth)

    def watch_state(self, state) -> None:
        self.query_one(Label).update(state)

    * Add base state to "on_mount" method if the state is to be watched".
    * Add watcher method to update content based on the state".

    Sender pattern: 

    --> Sender/writer classes should use base classes to change the state.

    def function(self, new_state) -> None:
        self.app.state.action()
        self.app.derived_state.update(new_state)

    * Add compute method to update state based on API response.
    
    """
    
    # TODO: Make this get the token path correctly
    token_path = "~/.dds_cli_token"
    
    # BASE STATES
    #TODO: should this be var instead?
    auth: reactive[Auth] = reactive(Auth(authenticate=False, token_path=token_path), recompose=True)

    # DERIVED STATES
    auth_status: reactive[bool] = reactive(False, recompose=True)

    # COMPUTE METHODS
    def compute_auth_status(self) -> bool:
        """Compute the auth status based on the auth object."""
        return bool(self.auth.check())

  