from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BinVisitEvent:
    day: date
    vehicle_number: int
    area: str
    bin_id: int
    coord_x: float
    coord_y: float


@dataclass(frozen=True)
class VehicleEmptyingEvent:
    day: date
    vehicle_number: int
    coord_x: float
    coord_y: float
