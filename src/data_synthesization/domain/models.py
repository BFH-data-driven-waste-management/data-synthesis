from dataclasses import dataclass
from datetime import datetime

from data_synthesization.domain.enums import ConnectivityState, FillLevel, VisitAction


@dataclass(frozen=True)
class BinRecord:
    id: int
    volume: int
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
    id: int | None
    uid: str
    bin_id: int
    mapped_at: datetime
    unmapped_at: datetime | None


@dataclass(frozen=True)
class TourRecord:
    id: int | None
    vehicle_id: int
    started_at: datetime
    ended_at: datetime | None

@dataclass(frozen=True)
class BinVisitRecord:
    client_event_id: str
    event_timestamp: datetime
    received_timestamp: datetime
    connectivity_state: ConnectivityState
    fill_level: FillLevel
    action: VisitAction
    tour_id: int
    nfc_tag_mapping_id: int | None


@dataclass(frozen=True)
class VehicleEmptyingRecord:
    client_event_id: str
    event_timestamp: datetime
    received_timestamp: datetime
    connectivity_state: ConnectivityState
    tour_id: int
