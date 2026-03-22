from dataclasses import dataclass
from datetime import date
from math import hypot

from data_synthesization.feature.tour_item.types import BinVisitEvent, VehicleEmptyingEvent
from data_synthesization.feature.tour_item.latent_filllevel_simulator import LatentFillLevelSimulator
from data_synthesization.shared.config.config_model.schedule_config import VehicleSchedule, SeasonBounds, Rule, \
    Frequency
from data_synthesization.shared.domain.models import BinRecord


@dataclass
class _VehicleDayState:
    volume_since_emptying: float
    current_x: float
    current_y: float


def generate_day_events(
    day: date,
    vehicles_schedules: list[VehicleSchedule],
    seasons: dict[str, tuple[tuple[int, int], tuple[int, int]]],
    bins_by_area: dict[str, list[int]],
    bins: dict[int, BinRecord],
    vehicle_emptying_coords: tuple[float, float],
    empty_after_volume: int,
    latent_filllevel_simulator: LatentFillLevelSimulator,
) -> list[BinVisitEvent | VehicleEmptyingEvent]:
    events: list[BinVisitEvent | VehicleEmptyingEvent] = []

    for vehicle_schedule in vehicles_schedules:
        areas = areas_for_vehicle_day(vehicle_schedule, day, seasons)
        _append_vehicle_day_events(
            day=day,
            vehicle_schedule=vehicle_schedule,
            areas=areas,
            bins_by_area=bins_by_area,
            bins=bins,
            events=events,
            vehicle_emptying_coords=vehicle_emptying_coords,
            empty_after_volume=empty_after_volume,
            latent_filllevel_simulator=latent_filllevel_simulator,
        )

    return events


def _nearest_bin_order(
    bin_ids_by_area_config: list[int],
    bins: dict[int, BinRecord],
    start_x: float,
    start_y: float,
) -> list[int]:
    remaining = [bin_id for bin_id in bin_ids_by_area_config if bin_id in bins]

    current_x, current_y = start_x, start_y
    ordered: list[int] = []

    while remaining:
        next_bin = min(
            remaining,
            key=lambda bin_id: hypot(
                bins[bin_id].coord_x - current_x,
                bins[bin_id].coord_y - current_y,
            ),
        )
        ordered.append(next_bin)
        current_x = bins[next_bin].coord_x
        current_y = bins[next_bin].coord_y
        remaining.remove(next_bin)

    return ordered


def _initial_vehicle_day_state(vehicle_emptying_coords: tuple[float, float]) -> _VehicleDayState:
    return _VehicleDayState(
        volume_since_emptying=0,
        current_x=vehicle_emptying_coords[0],
        current_y=vehicle_emptying_coords[1],
    )


def _append_visit_and_update_state(
    day: date,
    vehicle_number: int,
    area: str,
    _bin: BinRecord,
    events: list[BinVisitEvent | VehicleEmptyingEvent],
    state: _VehicleDayState,
    latent_filllevel_simulator: LatentFillLevelSimulator,
) -> None:
    events.append(
        BinVisitEvent(
            day=day,
            vehicle_number=vehicle_number,
            area=area,
            bin_id=_bin.id,
            coord_x=_bin.coord_x,
            coord_y=_bin.coord_y,
        )
    )

    latent_collection_ratio = latent_filllevel_simulator.latent_collection_ratio_for_visit(
        bin_id=_bin.id,
        area=area,
        visit_day=day,
    )
    state.volume_since_emptying += _bin.volume * latent_collection_ratio
    state.current_x = _bin.coord_x
    state.current_y = _bin.coord_y


def _append_emptying_and_reset_state(
    day: date,
    vehicle_number: int,
    events: list[BinVisitEvent | VehicleEmptyingEvent],
    state: _VehicleDayState,
    vehicle_emptying_coords: tuple[float, float],
) -> None:
    events.append(
        VehicleEmptyingEvent(
            day=day,
            vehicle_number=vehicle_number,
            coord_x=vehicle_emptying_coords[0],
            coord_y=vehicle_emptying_coords[1],
        )
    )
    state.volume_since_emptying = 0
    state.current_x, state.current_y = vehicle_emptying_coords


def _append_area_events(
    day: date,
    vehicle_number: int,
    area: str,
    bins_by_area: dict[str, list[int]],
    bins: dict[int, BinRecord],
    events: list[BinVisitEvent | VehicleEmptyingEvent],
    state: _VehicleDayState,
    vehicle_emptying_coords: tuple[float, float],
    empty_after_volume: int,
    latent_filllevel_simulator: LatentFillLevelSimulator,
) -> None:
    ordered_bins = _nearest_bin_order(
        bins_by_area.get(area, []),
        bins,
        start_x=state.current_x,
        start_y=state.current_y,
    )

    for bin_id in ordered_bins:
        _bin = bins[bin_id]
        _append_visit_and_update_state(
            day=day,
            vehicle_number=vehicle_number,
            area=area,
            _bin=_bin,
            events=events,
            state=state,
            latent_filllevel_simulator=latent_filllevel_simulator,
        )

        if state.volume_since_emptying >= empty_after_volume:
            _append_emptying_and_reset_state(
                day=day,
                vehicle_number=vehicle_number,
                events=events,
                state=state,
                vehicle_emptying_coords=vehicle_emptying_coords,
            )


def _append_vehicle_day_events(
    day: date,
    vehicle_schedule: VehicleSchedule,
    areas: list[str],
    bins_by_area: dict[str, list[int]],
    bins: dict[int, BinRecord],
    events: list[BinVisitEvent | VehicleEmptyingEvent],
    vehicle_emptying_coords: tuple[float, float],
    empty_after_volume: int,
    latent_filllevel_simulator: LatentFillLevelSimulator,
) -> None:
    state = _initial_vehicle_day_state(vehicle_emptying_coords)

    for area in areas:
        _append_area_events(
            day=day,
            vehicle_number=vehicle_schedule.vehicle_number,
            area=area,
            bins_by_area=bins_by_area,
            bins=bins,
            events=events,
            state=state,
            vehicle_emptying_coords=vehicle_emptying_coords,
            empty_after_volume=empty_after_volume,
            latent_filllevel_simulator=latent_filllevel_simulator,
        )

    _append_emptying_and_reset_state(
        day=day,
        vehicle_number=vehicle_schedule.vehicle_number,
        events=events,
        state=state,
        vehicle_emptying_coords=vehicle_emptying_coords,
    )


def areas_for_vehicle_day(vehicle: VehicleSchedule, day: date, seasons: dict[str, SeasonBounds]) -> list[str]:
    return [
        rule.area
        for rule in vehicle.rules
        if day.isoweekday() in choose_frequency(rule, day, seasons).weekdays
    ]


def choose_frequency(rule: Rule, day: date, seasons: dict[str, SeasonBounds]) -> Frequency:
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
