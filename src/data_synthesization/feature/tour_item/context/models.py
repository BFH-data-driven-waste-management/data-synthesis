from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EventPeriod:
    start: date
    end: date
    expected_people_per_day: int


@dataclass(frozen=True)
class EventDefinition:
    event_key: str
    name: str
    periods: list[EventPeriod]
    affected_neighbourhoods: list[str]


@dataclass(frozen=True)
class ActiveEventForDay:
    event_key: str
    name: str
    area_code: str
    expected_people_per_day: int


@dataclass(frozen=True)
class DailyWeatherContext:
    temp_mean: float
    temp_max: float
    precipitation: float
    sunshine_duration: float
