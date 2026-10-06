from enum import StrEnum


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RegionType(StrEnum):
    WALL = "wall"
    WINDOW = "window"
    BALCONY = "balcony"
    PILLAR = "pillar"
    PARAPET = "parapet"
    GATE = "gate"
    ROOF_EDGE = "roof_edge"


class ReviewStatus(StrEnum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class RevisionStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
