"""Dataclasses describing the project model."""

from dataclasses import dataclass
from typing import List


@dataclass
class Project:
    """A project."""

    project_content: List["ProjectContentData"]

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create a Project instance from dictionary data."""
        project_content = []

        for _, item_data in data.items():
            project_content.append(
                ProjectContentData.from_dict(item_data, project_name="Project Content")
            )
        return cls(
            project_content=project_content,
        )


@dataclass
class ProjectContentData:
    """A project content."""

    name: str
    children: List["ProjectContentData"]

    @classmethod
    def from_dict(cls, data: dict, project_name: str = "Project") -> "ProjectContentData":
        """Create a ProjectContent instance from dictionary data.

        Creates a root node with the project name, and the data becomes children.

        Args:
            data: Tree data (either single node or mapping of nodes)
            project_name: Name for the root project node
        """

        def _parse_node(node_data: dict) -> "ProjectContentData":
            """Parse a single node recursively."""
            if isinstance(node_data, dict) and "name" in node_data and "children" in node_data:
                name = node_data["name"]
                raw_children = node_data.get("children") or {}

                child_nodes: List[ProjectContentData] = []
                if isinstance(raw_children, dict):
                    for _child_name, child_dict in raw_children.items():
                        child_nodes.append(_parse_node(child_dict))
                elif isinstance(raw_children, list):
                    for child_dict in raw_children:
                        child_nodes.append(_parse_node(child_dict))

                return cls(name=name, children=child_nodes)
            return cls(name="", children=[])

        # Create the project root node
        content_children: List[ProjectContentData] = []

        # Case 1: Single node dict with name and children
        if isinstance(data, dict) and "name" in data and "children" in data:
            content_children.append(_parse_node(data))

        # Case 2: Top-level mapping of names -> node dicts
        elif isinstance(data, dict):
            for _name, node_dict in data.items():
                content_children.append(_parse_node(node_dict))

        # Return project root with content as children
        return cls(name=project_name, children=content_children)
