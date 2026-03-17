from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

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


def load_service_schedule(schedule_path: str | Path) -> ServiceSchedule:
    raw = yaml.safe_load(Path(schedule_path).read_text(encoding="utf-8"))
    root = raw["service_schedule"]

    seasons = {
        str(season_name): (
            (int(season_data["start_month"]), int(season_data["start_day"])),
            (int(season_data["end_month"]), int(season_data["end_day"])),
        )
        for season_name, season_data in root.get("seasons", {}).items()
    }
    vehicles = [VehicleSchedule.from_dict(item) for item in root.get("vehicles", [])]
    return ServiceSchedule(seasons=seasons, vehicles=vehicles)


def is_in_season(day: date, season_bounds: SeasonBounds) -> bool:
    (start_month, start_day), (end_month, end_day) = season_bounds
    current = (day.month, day.day)
    return (start_month, start_day) <= current <= (end_month, end_day)


def choose_frequency(rule: Rule, day: date, seasons: dict[str, SeasonBounds]) -> Frequency:
    active_frequency = rule.frequency
    for override in rule.seasonal_overrides:
        season_bounds = seasons.get(override.season)
        if not season_bounds or not is_in_season(day, season_bounds):
            continue

        if len(override.frequency.weekdays) >= len(rule.frequency.weekdays):
            active_frequency = override.frequency

    return active_frequency


def areas_for_vehicle_day(vehicle: VehicleSchedule, day: date, seasons: dict[str, SeasonBounds]) -> list[str]:
    return [
        rule.area
        for rule in vehicle.rules
        if day.isoweekday() in choose_frequency(rule, day, seasons).weekdays
    ]
