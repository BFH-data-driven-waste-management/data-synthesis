from dataclasses import dataclass
from datetime import date, datetime

from data_synthesization.shared.domain.enums import FillLevel, VisitAction


@dataclass(frozen=True)
class RealWorldBinVisit:
    day: date
    vehicle_number: int
    area: str
    fill_level: FillLevel
    action: VisitAction
    bin_id: int
    coord_x: float
    coord_y: float
    relative_event_timestamp: datetime
    relative_received_timestamp: datetime


@dataclass(frozen=True)
class RealWorldVehicleEmptying:
    day: date
    vehicle_number: int
    coord_x: float
    coord_y: float
    relative_event_timestamp: datetime
    relative_received_timestamp: datetime
    is_last_of_the_tour: bool
