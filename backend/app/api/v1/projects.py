from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.contracts import ProjectCreate, ProjectRead
from app.services.project_service import create_project

router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=ProjectRead)
def create_project_endpoint(payload: ProjectCreate, session: Session = Depends(get_db)) -> ProjectRead:
    return ProjectRead.model_validate(create_project(session, payload.name, payload.description))