"""DDS Tree View Widget"""

from dataclasses import dataclass
from typing import Any, List

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from dds_cli.dds_gui.models.project import ProjectContentData


@dataclass
class DDSTreeNode:
    """A node in the tree.
    Args:
        name: The name of the node.
        children: A list of children nodes.
    """

    name: str
    children: List["DDSTreeNode"]


class TreeView(Widget):
    """A tree view widget.
    Args:
        tree_data: The data to be displayed in the tree view.
    """

    def __init__(self, tree_data: ProjectContentData, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tree_data = tree_data

    DEFAULT_CSS = """
    ScrollView {
        scrollbar-size: 1 1;
        scrollbar-color: $primary 70%;
    }
    """

    def compose(self) -> ComposeResult:
        tree: Tree[str] = Tree(self.tree_data.name)  # Create tree with root node
        tree.root.expand()  # Expand the root node to show all children

        self.add_children(self.tree_data, tree.root)

        yield tree

    def add_children(self, node: ProjectContentData, parent: TreeNode) -> None:
        """Add children to the parent node.
        Args:
            node: The node to add.
            parent: The parent node.
        """
        for child in node.children:
            if child.children:
                sub_tree = parent.add(
                    f"📁 {child.name}", expand=False
                )  # Don't expand the sub tree by default
                self.add_children(child, sub_tree)
            else:
                parent.add_leaf(f"📄 {child.name}")
