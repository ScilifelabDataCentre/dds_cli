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
    def from_dict(cls, data: list | dict) -> "ProjectList":
        """Create a ProjectList instance from dictionary data.
        
        Filters out invalid projects that don't have required "Project ID" and "Access" keys.
        
        Args:
            data: List of project dictionaries
            
        Returns:
            ProjectList instance with valid projects only
        """
        if not isinstance(data, list):
            return cls(projects={})
        
        valid_projects = {}
        for project in data:
            # Only include projects with valid "Project ID" and "Access" keys
            if (
                isinstance(project, dict)
                and "Project ID" in project
                and "Access" in project
                and isinstance(project.get("Project ID"), str)
                and project["Project ID"].strip()  # Non-empty Project ID
            ):
                try:
                    valid_projects[project["Project ID"]] = Project.from_dict(project)
                except (KeyError, TypeError):
                    # Skip projects that fail to parse
                    continue
        
        return cls(projects=valid_projects)
