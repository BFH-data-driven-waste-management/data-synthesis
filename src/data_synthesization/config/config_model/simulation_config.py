from dataclasses import dataclass
from datetime import date
from datetime import datetime


@dataclass(frozen=True)
class SimulationConfig:
    start_date: datetime
    end_date: datetime
    tour_generation_end_date: date
    seed: int
