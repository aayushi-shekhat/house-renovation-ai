from app.core.database import Base
from app.domain.models import (
    Asset,
    DesignRevision,
    Estimate,
    EstimateLine,
    Image,
    Job,
    Material,
    MaterialAssignment,
    MaterialVersion,
    Measurement,
    MeasurementRevision,
    Project,
    Region,
    RegionSet,
    Render,
    Report,
)


def test_all_phase_one_models_are_registered() -> None:
    expected = {
        Asset, DesignRevision, Estimate, EstimateLine, Image, Job, Material,
        MaterialAssignment, MaterialVersion, Measurement, MeasurementRevision,
        Project, Region, RegionSet, Render, Report,
    }
    assert expected == set(Base.registry.mappers and [mapper.class_ for mapper in Base.registry.mappers])
    assert len(Base.metadata.tables) == 16
