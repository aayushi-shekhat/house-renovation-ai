from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db", response_model=None)
def database_health(session: Session = Depends(get_db)) -> dict[str, str] | JSONResponse:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable", "detail": str(exc).splitlines()[0]},
        )
    return {"status": "ok", "database": "reachable"}
