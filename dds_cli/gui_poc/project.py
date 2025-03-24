from textual import events
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, ContentSwitcher, DataTable, Label, LoadingIndicator

from dds_cli.auth import Auth
from dds_cli.gui_poc.utils import DDSSidebar
from dds_cli.data_lister import DataLister


class ProjectList(Widget):
    def __init__(self, data_lister: DataLister):
        super().__init__() 
        self.data_lister = data_lister

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="project-list"):
            yield Button("Get project list", id="get-project-list")
            yield DataTable(id="project-table")
            #yield Label(str(self.get_project_list()))


    async def on_button_pressed(self, event: events.Click) -> None:
        if event.button.id == "get-project-list":
            await self.get_project_list()
            
    async def get_project_list(self):            
        #self.query_one("#project-list").mount(LoadingIndicator())
        #project_list = await DataLister().gui_list_projects()
        #self.query_one(LoadingIndicator).remove()
        project_list = self.data_lister.gui_list_projects()
        project_info = project_list['project_info']
        self.query_one("#project-list").mount(Label(f"Usage size: {project_list['total_usage']} and total size: {project_list['total_size']}"))
        table = self.query_one("#project-table")
        table.add_columns("Project ID")
        for project in project_info:
            table.add_row(project["Project ID"])


class Project(Widget):
    def __init__(self, token_path: str):
        super().__init__() 
        self.data_lister = DataLister()

    def compose(self) -> ComposeResult:
        yield DDSSidebar([
            "list",
            "info"
        ], title="Project")
        with ContentSwitcher(initial="list", id="project"):
            with Container(id="list"):
                yield ProjectList(self.data_lister)
