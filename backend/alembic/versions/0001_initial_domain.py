"""Create the Phase 1 domain schema.

Revision ID: 0001_initial_domain
Revises:
"""
from alembic import op

from app.core.database import Base
from app.domain import models  # noqa: F401

revision = "0001_initial_domain"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
