import uuid
from decimal import Decimal

from app.core.enums import JobState, RegionType
from app.domain.models import Job, MaterialVersion, Project, Region


def test_domain_objects_can_be_constructed() -> None:
    project = Project(name="Test House")
    region = Region(region_type=RegionType.WALL, confidence=Decimal("0.94"))
    material = MaterialVersion(material_rate=Decimal("120.00"), labor_rate=Decimal("45.00"), unit="sqft")
    job = Job(job_type="validation", state=JobState.QUEUED)

    assert project.name == "Test House"
    assert region.region_type == RegionType.WALL
    assert material.material_rate == Decimal("120.00")
    assert job.state == JobState.QUEUED
    assert Project.__table__.c.id.default is not None
    assert isinstance(uuid.uuid4(), uuid.UUID)
