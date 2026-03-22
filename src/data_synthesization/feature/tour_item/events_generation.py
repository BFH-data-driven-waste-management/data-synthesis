from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from math import hypot

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
    current_timestamp: datetime


def generate_day_events(
    day: date,
    vehicles_schedules: list[VehicleSchedule],
    seasons: dict[str, tuple[tuple[int, int], tuple[int, int]]],
    bins_by_area: dict[str, list[int]],
    bins: dict[int, BinRecord],
    vehicle_emptying_coords: tuple[float, float],
    empty_after_volume: int,
    latent_fill_level_simulator: LatentFillLevelSimulator,
    average_speed_meters_per_second: float,
    road_network_detour_factor: float,
    seconds_per_bin_visit: int,
    seconds_per_vehicle_emptying: int,
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
            average_speed_meters_per_second=average_speed_meters_per_second,
            road_network_detour_factor=road_network_detour_factor,
            seconds_per_bin_visit=seconds_per_bin_visit,
            seconds_per_vehicle_emptying=seconds_per_vehicle_emptying,
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
    average_speed_meters_per_second: float,
    road_network_detour_factor: float,
    seconds_per_bin_visit: int,
    seconds_per_vehicle_emptying: int,
) -> None:
    state = _initial_vehicle_day_state(day, vehicle_emptying_coords)

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
            average_speed_meters_per_second=average_speed_meters_per_second,
            road_network_detour_factor=road_network_detour_factor,
            seconds_per_bin_visit=seconds_per_bin_visit,
            seconds_per_vehicle_emptying=seconds_per_vehicle_emptying,
        )

    _append_emptying_and_reset_state(
        day=day,
        vehicle_number=vehicle_schedule.vehicle_number,
        events=events,
        state=state,
        vehicle_emptying_coords=vehicle_emptying_coords,
        seconds_per_vehicle_emptying=seconds_per_vehicle_emptying,
        road_network_detour_factor=road_network_detour_factor,
        average_speed_meters_per_second=average_speed_meters_per_second,
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
    average_speed_meters_per_second: float,
    road_network_detour_factor: float,
    seconds_per_bin_visit: int,
    seconds_per_vehicle_emptying: int,
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
            seconds_per_bin_visit=seconds_per_bin_visit,
            road_network_detour_factor=road_network_detour_factor,
            average_speed_meters_per_second=average_speed_meters_per_second,
        )

        if state.volume_since_emptying >= empty_after_volume:
            _append_emptying_and_reset_state(
                day=day,
                vehicle_number=vehicle_number,
                events=events,
                state=state,
                vehicle_emptying_coords=vehicle_emptying_coords,
                seconds_per_vehicle_emptying=seconds_per_vehicle_emptying,
                road_network_detour_factor=road_network_detour_factor,
                average_speed_meters_per_second=average_speed_meters_per_second,
            )


def _initial_vehicle_day_state(day: date, vehicle_emptying_coords: tuple[float, float]) -> _VehicleDayState:
    return _VehicleDayState(
        volume_since_emptying=0,
        current_x=vehicle_emptying_coords[0],
        current_y=vehicle_emptying_coords[1],
        current_timestamp=datetime.combine(day, time.min, tzinfo=timezone.utc),
    )


def _append_visit_and_update_state(
    day: date,
    vehicle_number: int,
    area: str,
    _bin: BinRecord,
    events: list[BinVisitEvent | VehicleEmptyingEvent],
    state: _VehicleDayState,
    latent_fill_level_simulator: LatentFillLevelSimulator,
    seconds_per_bin_visit: int,
    road_network_detour_factor: float,
    average_speed_meters_per_second: float,
) -> None:

    observation = latent_fill_level_simulator.observe_visit(
        bin_id=_bin.id,
        area=area,
        visit_day=day,
    )

    event_timestamp, received_timestamp = _event_timestamps_for_next_stop(
        current_x=state.current_x,
        current_y=state.current_y,
        current_timestamp=state.current_timestamp,
        target_x=_bin.coord_x,
        target_y=_bin.coord_y,
        seconds_spent=seconds_per_bin_visit,
        road_network_detour_factor=road_network_detour_factor,
        average_speed_meters_per_second=average_speed_meters_per_second,
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
            event_timestamp=event_timestamp,
            received_timestamp=received_timestamp,
        )
    )


    state.volume_since_emptying += _bin.volume * observation.fill_level_continuous
    state.current_x = _bin.coord_x
    state.current_y = _bin.coord_y
    state.current_timestamp = event_timestamp


def _append_emptying_and_reset_state(
    day: date,
    vehicle_number: int,
    events: list[BinVisitEvent | VehicleEmptyingEvent],
    state: _VehicleDayState,
    vehicle_emptying_coords: tuple[float, float],
    seconds_per_vehicle_emptying: int,
    road_network_detour_factor: float,
    average_speed_meters_per_second: float,
) -> None:
    event_timestamp, received_timestamp = _event_timestamps_for_next_stop(
        current_x=state.current_x,
        current_y=state.current_y,
        current_timestamp=state.current_timestamp,
        target_x=vehicle_emptying_coords[0],
        target_y=vehicle_emptying_coords[1],
        seconds_spent=seconds_per_vehicle_emptying,
        road_network_detour_factor=road_network_detour_factor,
        average_speed_meters_per_second=average_speed_meters_per_second,
    )
    events.append(
        VehicleEmptyingEvent(
            day=day,
            vehicle_number=vehicle_number,
            coord_x=vehicle_emptying_coords[0],
            coord_y=vehicle_emptying_coords[1],
            event_timestamp=event_timestamp,
            received_timestamp=received_timestamp,
        )
    )
    state.volume_since_emptying = 0
    state.current_x, state.current_y = vehicle_emptying_coords
    state.current_timestamp = event_timestamp


def _event_timestamps_for_next_stop(
    current_x: float,
    current_y: float,
    current_timestamp: datetime,
    target_x: float,
    target_y: float,
    seconds_spent: int,
    road_network_detour_factor: float,
    average_speed_meters_per_second: float,
) -> tuple[datetime, datetime]:
    travel_seconds = _estimate_travel_seconds(
        start_x=current_x,
        start_y=current_y,
        target_x=target_x,
        target_y=target_y,
        road_network_detour_factor=road_network_detour_factor,
        average_speed_meters_per_second=average_speed_meters_per_second,
    )
    event_timestamp = current_timestamp + timedelta(seconds=travel_seconds + seconds_spent)
    return event_timestamp, event_timestamp + timedelta(seconds=1)


def _estimate_travel_seconds(
    start_x: float,
    start_y: float,
    target_x: float,
    target_y: float,
    road_network_detour_factor: float,
    average_speed_meters_per_second: float,
) -> int:
    direct_distance_meters = hypot(target_x - start_x, target_y - start_y)
    network_distance_meters = direct_distance_meters * road_network_detour_factor
    return max(1, int(network_distance_meters / average_speed_meters_per_second))
