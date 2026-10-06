from __future__ import annotations

from typing import Generic, Protocol, TypeVar

from sqlalchemy.orm import Session

from app.domain.models import Project

EntityT = TypeVar("EntityT")


class Repository(Protocol, Generic[EntityT]):
    def get(self, session: Session, entity_id: object) -> EntityT | None:
        ...

    def add(self, session: Session, entity: EntityT) -> EntityT:
        ...


class ProjectRepository(Repository[Project], Protocol):
    pass
