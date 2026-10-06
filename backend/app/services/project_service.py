from sqlalchemy.orm import Session

from app.domain.models import Project


def create_project(session: Session, name: str, description: str | None = None) -> Project:
    project = Project(name=name, description=description)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project
