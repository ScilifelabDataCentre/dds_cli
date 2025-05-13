from dataclasses import dataclass
from typing import Any

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Tree
from textual.widgets.tree import TreeNode


@dataclass
class DDSTreeNode:
    """A node in the tree."""
    name: str
    children: list["DDSTreeNode"]


class DDSTreeView(Widget):
    """A tree view widget."""

    def __init__(self, tree_data: DDSTreeNode, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tree_data = tree_data

    def compose(self) -> ComposeResult:
        tree: Tree[str] = Tree(self.tree_data.name)  # Create tree with root node
        tree.root.expand()  # Expand the root node to show all children

        self.add_children(self.tree_data, tree.root)

        yield tree

    def add_children(self, node: DDSTreeNode, parent: TreeNode) -> None:
        """Add children to the parent node."""
        for child in node.children:
            if child.children:
                sub_tree = parent.add(
                    f"📁 {child.name}", expand=False
                )  # Don't expand the sub tree by default
                self.add_children(child, sub_tree)
            else:
                parent.add_leaf(f"📄 {child.name}")
