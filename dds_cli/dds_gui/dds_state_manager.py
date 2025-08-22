"""DDS State Manager"""

from dataclasses import dataclass

from textual.reactive import reactive

from dds_cli.auth import Auth
from dds_cli.dds_gui.components.dds_tree_view import DDSTreeNode
from dds_cli.dds_gui.components.dds_status_chip import DDSStatus


@dataclass
class ProjectInformation:
    """A dataclass for the project information."""

    name: str
    description: str
    status: DDSStatus
    created_by: str
    last_updated: str
    size: str
    support_contact: str


MOCK_DATA = {
    "project_1": {
        "project_id": "123",
        "project_information": ProjectInformation(
            name="Project 1",
            description="Project 1 description",
            status=DDSStatus.AVAILABLE,
            created_by="John Doe",
            last_updated="2021-01-01",
            size="100MB",
            support_contact="john.doe@example.com",
        ),
        "project_files": DDSTreeNode(
            name="Project Content for project 1",
            children=[
                DDSTreeNode(
                    name="Project Content 1",
                    children=[
                        DDSTreeNode(name="Project Content 1.1", children=[]),
                        DDSTreeNode(name="Project Content 1.2", children=[]),
                        DDSTreeNode(
                            name="Project Content 1.3",
                            children=[
                                DDSTreeNode(name="Project Content 1.3.1", children=[]),
                                DDSTreeNode(name="Project Content 1.3.2", children=[]),
                                DDSTreeNode(name="Project Content 1.3.3", children=[]),
                            ],
                        ),
                    ],
                ),
                DDSTreeNode(
                    name="Project Content 2",
                    children=[
                        DDSTreeNode(name="Project Content 2.1", children=[]),
                        DDSTreeNode(name="Project Content 2.2", children=[]),
                        DDSTreeNode(name="Project Content 2.3", children=[]),
                    ],
                ),
            ],
        ),
    },
    "project_2": {
        "project_id": "456",
        "project_information": ProjectInformation(
            name="Project 2",
            description="Project 2 description",
            status=DDSStatus.IN_PROGRESS,
            created_by="Jane Doe",
            last_updated="2021-01-01",
            size="200MB",
            support_contact="jane.doe@example.com",
        ),
        "project_files": DDSTreeNode(
            name="Project Content for project 2",
            children=[
                DDSTreeNode(
                    name="Project Content 4",
                    children=[
                        DDSTreeNode(name="Project Content 4.1", children=[]),
                        DDSTreeNode(name="Project Content 4.2", children=[]),
                        DDSTreeNode(name="Project Content 4.3", children=[]),
                    ],
                ),
                DDSTreeNode(
                    name="Project Content 5",
                    children=[
                        DDSTreeNode(name="Project Content 5.1", children=[]),
                        DDSTreeNode(name="Project Content 5.2", children=[]),
                        DDSTreeNode(name="Project Content 5.3", children=[]),
                    ],
                ),
            ],
        ),
    },
}


class DDSStateManager:
    """

    A base class for state management.

    - BASE STATES: States that are directly derived from the CLI functions.
    - DERIVED STATES: States that are derived from the base states.
    - COMPUTE METHODS: Functions that compute the derived states based on the base states.

    Receiver pattern:

    --> Receiver/reader classes should use derived classes to get state content.

    def on_mount(self) -> None:
        self.watch_state(self.auth)

    def watch_state(self, state) -> None:
        self.query_one(Label).update(state)

    * Add base state to "on_mount" method if the state is to be watched.
    * Add watcher method to update content based on the state.

    Sender pattern:

    --> Sender/writer classes should use base classes to change the state.

    def function(self, new_state) -> None:
        self.app.state.action()
        self.app.derived_state.update(new_state)

    * Add compute method to update state based on API response.

    """

    # TODO: Make this get the token path correctly
    token_path = "~/.dds_cli_token"
    # ------------------------------------------------------------
    # BASE STATES
    # ------------------------------------------------------------

    # AUTH STATE
    # Initialize the auth object as an reactive state when starting the application.
    auth: reactive[Auth] = reactive(Auth(authenticate=False, token_path=token_path), recompose=True)

    # PROJECT STATE
    # projects_id: reactive[List[str]] = reactive(list(MOCK_DATA.keys()), recompose=True)
    # selected_project_id: reactive[str] = reactive(None, recompose=True)

    # ------------------------------------------------------------
    # DERIVED STATES
    # ------------------------------------------------------------

    # AUTH STATUS
    # Derive the auth status from the auth object.
    # Initialize the auth status as False when starting the application.
    # Derived through the compute_auth_status method.
    auth_status: reactive[bool] = reactive(False, recompose=True)

    # PROJECT CONTENT
    # Derive the project content from the selected project.
    # Initialize the project content as None when starting the application.
    # Derived through the compute_project_content method.
    # project_content: reactive[DDSTreeNode] = reactive(None, recompose=True)

    # PROJECT INFORMATION
    # Derive the project information from the selected project.
    # Initialize the project information as None when starting the application.
    # Derived through the compute_project_information method.
    # project_information: reactive[ProjectInformation] = reactive(None, recompose=True)

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    # def compute_auth_status(self) -> bool:
    #    """Compute the auth status based on the auth object."""
    #    return bool(self.auth.check())

    # def compute_project_content(self) -> Optional[DDSTreeNode]:
    #     """Compute the project content based on the selected project."""
    #     if self.selected_project_id:
    #         return MOCK_DATA[self.selected_project_id]["project_files"]
    #     return None

    # def compute_project_information(self) -> Optional[ProjectInformation]:
    #     """Compute the project information based on the selected project."""
    #     if self.selected_project_id:
    #         return MOCK_DATA[self.selected_project_id]["project_information"]
    #     return None

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    # def set_selected_project_id(self, project_id: Optional[str]) -> None:
    #     """Set the selected project id."""
    #     self.selected_project_id = project_id

    def set_auth_status(self, new_auth_status: bool) -> None:
        """Set the auth status."""
        self.auth_status = new_auth_status
