from dataclasses import dataclass
from datetime import date

from data_synthesization.feature.tour_item.schedule.choose_active_areas import areas_for_vehicle_day
from data_synthesization.feature.tour_item.schedule.route_to_nearest_bin import nearest_bin_order
from data_synthesization.feature.tour_item.types import BinVisitEvent, VehicleEmptyingEvent
from data_synthesization.feature.tour_item.fill_level.latent_fill_level_simulator import LatentFillLevelSimulator
from data_synthesization.shared.config.config_model.schedule_config import VehicleSchedule
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
    latent_fill_level_simulator: LatentFillLevelSimulator,
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
            latent_fill_level_simulator=latent_fill_level_simulator,
        )

    return events


def _append_vehicle_day_events(
    day: date,
    vehicle_schedule: VehicleSchedule,
    areas: list[str],
    bins_by_area: dict[str, list[int]],
    bins: dict[int, BinRecord],
    events: list[BinVisitEvent | VehicleEmptyingEvent],
    vehicle_emptying_coords: tuple[float, float],
    empty_after_volume: int,
    latent_fill_level_simulator: LatentFillLevelSimulator,
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
            latent_fill_level_simulator=latent_fill_level_simulator,
        )

    _append_emptying_and_reset_state(
        day=day,
        vehicle_number=vehicle_schedule.vehicle_number,
        events=events,
        state=state,
        vehicle_emptying_coords=vehicle_emptying_coords,
    )


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
    latent_fill_level_simulator: LatentFillLevelSimulator,
) -> None:
    ordered_bins = nearest_bin_order(
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
            latent_fill_level_simulator=latent_fill_level_simulator,
        )

        if state.volume_since_emptying >= empty_after_volume:
            _append_emptying_and_reset_state(
                day=day,
                vehicle_number=vehicle_number,
                events=events,
                state=state,
                vehicle_emptying_coords=vehicle_emptying_coords,
            )


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
    latent_fill_level_simulator: LatentFillLevelSimulator,
) -> None:

    observation = latent_fill_level_simulator.observe_visit(
        bin_id=_bin.id,
        area=area,
        visit_day=day,
    )

    events.append(
        BinVisitEvent(
            day=day,
            vehicle_number=vehicle_number,
            area=area,
            fill_level=observation.fill_level,
            action=observation.action,
            bin_id=_bin.id,
            coord_x=_bin.coord_x,
            coord_y=_bin.coord_y,
        )
    )


    state.volume_since_emptying += _bin.volume * observation.fill_level_continuous
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