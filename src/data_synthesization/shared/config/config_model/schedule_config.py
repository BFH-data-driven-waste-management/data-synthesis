from dataclasses import dataclass, field
from typing import Any

SeasonBounds = tuple[tuple[int, int], tuple[int, int]]


@dataclass(frozen=True)
class Frequency:
    weekdays: list[int]

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Frequency":
        return Frequency(weekdays=[int(day) for day in data.get("weekdays", [])])


@dataclass(frozen=True)
class SeasonalOverride:
    season: str
    frequency: Frequency

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SeasonalOverride":
        return SeasonalOverride(
            season=str(data["season"]),
            frequency=Frequency.from_dict(data["frequency"]),
        )


@dataclass(frozen=True)
class Rule:
    area: str
    frequency: Frequency
    seasonal_overrides: list[SeasonalOverride] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Rule":
        return Rule(
            area=str(data["area"]),
            frequency=Frequency.from_dict(data["frequency"]),
            seasonal_overrides=[SeasonalOverride.from_dict(item) for item in data.get("seasonal_overrides", [])],
        )


@dataclass(frozen=True)
class VehicleSchedule:
    vehicle_number: int
    rules: list[Rule] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "VehicleSchedule":
        return VehicleSchedule(
            vehicle_number=int(data["vehicle_number"]),
            rules=[Rule.from_dict(item) for item in data.get("rules", [])],
        )


@dataclass(frozen=True)
class ServiceSchedule:
    seasons: dict[str, SeasonBounds]
    vehicles: list[VehicleSchedule]
