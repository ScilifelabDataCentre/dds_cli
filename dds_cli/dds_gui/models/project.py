"""Dataclasses for the project."""
from dataclasses import dataclass


@dataclass
class Project:
    """A project."""

    project_id: str
    access: bool

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create a Project instance from dictionary data."""
        return cls(
            project_id=data["Project ID"],
            access=data["Access"],
        )

@dataclass
class ProjectList:
    """A list of projects."""

    projects: dict[str, Project]

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectList":
        """Create a ProjectList instance from dictionary data."""
        return cls(projects={project["Project ID"]: Project.from_dict(project) for project in data})
