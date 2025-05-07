"""DDS Data Table"""

from typing import Any, Iterable
from textual.widgets import DataTable

class DDSDataTable(DataTable):
    """A data table widget."""
    def __init__(self, header: list[str], data: list[list[Any]], *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        
        #self.zebra_stripes = True
        
        self.add_columns(*header)
        for row in data:
            self.add_row(row)
    
    DEFAULT_CSS = """
    DDSDataTable {
        & > .datatable--header {
            text-style: bold;
            background: $primary;
            color: $foreground;
        }
        & > .datatable--header-hover {
            background: $secondary 30%;
        }
    }
    """     
