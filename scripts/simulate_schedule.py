#!/usr/bin/env python3
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

START_DATE = "2025-04-21"
END_DATE = "2025-05-11"

SCHEDULE_PATH = Path("config/schedule.yaml")

# (start_month, start_day) <= (end_month, end_day)
SeasonBounds = Tuple[Tuple[int, int], Tuple[int, int]]


@dataclass
class Frequency:
    weekdays: List[int]

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Frequency":
        weekdays = d.get("weekdays")
        return Frequency(weekdays=weekdays)


@dataclass
class SeasonalOverride:
    season: str
    frequency: Frequency

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SeasonalOverride":
        return SeasonalOverride(
            season=d["season"],
            frequency=Frequency.from_dict(d["frequency"]),
        )


@dataclass
class Rule:
    area: str
    frequency: Frequency
    seasonal_overrides: List[SeasonalOverride] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Rule":
        return Rule(
            area=d["area"],
            frequency=Frequency.from_dict(d["frequency"]),
            seasonal_overrides=[SeasonalOverride.from_dict(o) for o in d.get("seasonal_overrides", [])],
        )


@dataclass
class Vehicle:
    vehicle_number: str
    rules: List[Rule] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Vehicle":
        return Vehicle(
            vehicle_number=d["vehicle_number"],
            rules=[Rule.from_dict(r) for r in d.get("rules", [])],
        )


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def build_season_lookup(config: Dict[str, Any]) -> Dict[str, SeasonBounds]:
    seasons = config.get("seasons", {})
    return {
        season_name: (
            (season_data["start_month"], season_data["start_day"]),
            (season_data["end_month"], season_data["end_day"]),
        )
        for season_name, season_data in seasons.items()
    }


def is_in_season(day: date, season_bounds: SeasonBounds) -> bool:
    (start_m, start_d), (end_m, end_d) = season_bounds
    current = (day.month, day.day)
    return (start_m, start_d) <= current <= (end_m, end_d)


def is_rule_active_for_day(freq: Frequency, day: date) -> bool:
    return day.isoweekday() in freq.weekdays


def choose_frequency(
    rule: Rule,
    day: date,
    seasons: Dict[str, SeasonBounds],
) -> Frequency:
    active_freq = rule.frequency

    for override in rule.seasonal_overrides:
        season_bounds = seasons.get(override.season)
        if not season_bounds or not is_in_season(day, season_bounds):
            continue

        # always use the denser frequency
        if len(override.frequency.weekdays) >= len(rule.frequency.weekdays):
            active_freq = override.frequency

    return active_freq


def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def main() -> None:
    schedule = yaml.safe_load(SCHEDULE_PATH.read_text(encoding="utf-8"))
    root = schedule["service_schedule"]

    seasons = build_season_lookup(root)
    vehicles = [Vehicle.from_dict(v) for v in root.get("vehicles", [])]

    start = parse_date(START_DATE)
    end = parse_date(END_DATE)

    for day in iter_dates(start, end):
        print(day.isoformat())
        for vehicle in vehicles:
            route = [
                rule.area
                for rule in vehicle.rules
                if is_rule_active_for_day(
                    choose_frequency(rule, day, seasons),
                    day,
                )
            ]
            print(f"  vehicle {vehicle.vehicle_number}: {' -> '.join(route)}")
        print()


if __name__ == "__main__":
    main()
