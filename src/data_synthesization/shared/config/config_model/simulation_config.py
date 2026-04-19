from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time


@dataclass(frozen=True)
class TourTimingConfig:
    reference_start_time_europe_zurich: time
    start_time_delta_min_minutes: int
    start_time_delta_max_minutes: int
    second_phone_offset_min_seconds: int
    second_phone_offset_max_seconds: int
    next_day_midnight_ending_share: float


@dataclass(frozen=True)
class SimulationConfig:
    start_date: datetime
    end_date: datetime
    tour_generation_end_date: date
    seed: int
    tour_timing: TourTimingConfig
