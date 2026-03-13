from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SimulationConfig:
    start_date: datetime
    end_date: datetime
    seed: int
