from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BinRecord:
    id: int
    coord_x: float
    coord_y: float
    created_at: datetime


@dataclass(frozen=True)
class BinActivityRecord:
    bin_id: int
    active: bool
    activity_timestamp: datetime


@dataclass(frozen=True)
class NfcTagMappingRecord:
    uid: str
    bin_id: int
    mapped_at: datetime
    unmapped_at: datetime | None


@dataclass(frozen=True)
class TourRecord:
    vehicle_id: int
    started_at: datetime
    ended_at: datetime | None
