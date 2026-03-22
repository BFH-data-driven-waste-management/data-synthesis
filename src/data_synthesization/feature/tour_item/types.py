from dataclasses import dataclass
from datetime import date, datetime

from data_synthesization.shared.domain.enums import FillLevel, VisitAction


@dataclass(frozen=True)
class BinVisitEvent:
    day: date
    vehicle_number: int
    area: str
    fill_level: FillLevel
    action: VisitAction
    bin_id: int
    coord_x: float
    coord_y: float
    event_timestamp: datetime
    received_timestamp: datetime


@dataclass(frozen=True)
class VehicleEmptyingEvent:
    day: date
    vehicle_number: int
    coord_x: float
    coord_y: float
    event_timestamp: datetime
    received_timestamp: datetime
