from datetime import date

from data_synthesization.shared.config.config_model.schedule_config import VehicleSchedule, SeasonBounds, Rule, \
    Frequency


def areas_for_vehicle_day(vehicle: VehicleSchedule, day: date, seasons: dict[str, SeasonBounds]) -> list[str]:
    return [
        rule.area
        for rule in vehicle.rules
        if day.isoweekday() in _choose_frequency(rule, day, seasons).weekdays
    ]


def _choose_frequency(rule: Rule, day: date, seasons: dict[str, SeasonBounds]) -> Frequency:
    active_frequency = rule.frequency
    for override in rule.seasonal_overrides:
        season_bounds = seasons.get(override.season)
        if not season_bounds or not _is_in_season(day, season_bounds):
            continue

        if len(override.frequency.weekdays) >= len(rule.frequency.weekdays):
            active_frequency = override.frequency

    return active_frequency


def _is_in_season(day: date, season_bounds: SeasonBounds) -> bool:
    (start_month, start_day), (end_month, end_day) = season_bounds
    current = (day.month, day.day)
    return (start_month, start_day) <= current <= (end_month, end_day)
