from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from data_synthesization.feature.tour_item.schedule.choose_active_areas import areas_for_vehicle_day
from data_synthesization.feature.tour_item.schedule.estimate_travel_time import event_timestamps_for_next_stop
from data_synthesization.feature.tour_item.schedule.route_to_nearest_bin import nearest_bin_order
from data_synthesization.feature.tour_item.types import RealWorldBinVisit, RealWorldVehicleEmptying
from data_synthesization.feature.tour_item.fill_level.latent_fill_level_simulator import LatentFillLevelSimulator
from data_synthesization.shared.config.config_model.schedule_config import VehicleSchedule, SeasonBounds
from data_synthesization.shared.domain.models import BinRecord, NfcTagMappingRecord


@dataclass
class _VehicleDayState:
    volume_since_emptying: float
    current_x: float
    current_y: float
    relative_timestamp: datetime


@dataclass(frozen=True)
class EventGenerationContext:
    seasons: dict[str, SeasonBounds]
    bins_by_area: dict[str, list[int]]
    bins: dict[int, BinRecord]
    vehicle_emptying_coords: tuple[float, float]
    empty_after_volume: int
    latent_fill_level_simulator: LatentFillLevelSimulator
    average_speed_meters_per_second: float
    road_network_detour_factor: float
    seconds_per_bin_visit: int
    seconds_per_vehicle_emptying: int

"""
generation of the real world events for a day.
data model specific aspects such as two operators who both log vehicle_emptying but only one of them logs bin_visits are not considered here.
"""
def generate_day_events(
    day: date,
    vehicles_schedules: list[VehicleSchedule],
    context: EventGenerationContext,
) -> list[RealWorldBinVisit | RealWorldVehicleEmptying]:
    events: list[RealWorldBinVisit | RealWorldVehicleEmptying] = []

    for vehicle_schedule in vehicles_schedules:
        areas = areas_for_vehicle_day(vehicle_schedule, day, context.seasons)
        state = _initial_vehicle_day_state(day, context.vehicle_emptying_coords)

        for area in areas:
            ordered_bins = nearest_bin_order(
                context.bins_by_area.get(area, []),
                context.bins,
                start_x=state.current_x,
                start_y=state.current_y,
            )

            for bin_id in ordered_bins:
                _bin = context.bins[bin_id]
                _append_visit_and_update_state(
                    day=day,
                    vehicle_number=vehicle_schedule.vehicle_number,
                    area=area,
                    _bin=_bin,
                    context=context,
                    events=events,
                    state=state,
                )

                if state.volume_since_emptying >= context.empty_after_volume:
                    _append_emptying_and_reset_state(day=day, vehicle_number=vehicle_schedule.vehicle_number,
                                                     events=events, state=state, context=context)

        # empty vehicle after each tour
        _append_emptying_and_reset_state(
            day=day,
            vehicle_number=vehicle_schedule.vehicle_number,
            events=events,
            state=state,
            context=context,
            is_last_of_the_tour=True
        )

    return events


def _initial_vehicle_day_state(day: date, vehicle_emptying_coords: tuple[float, float]) -> _VehicleDayState:
    return _VehicleDayState(
        volume_since_emptying=0,
        current_x=vehicle_emptying_coords[0],
        current_y=vehicle_emptying_coords[1],
        relative_timestamp=datetime.combine(day, time.min),
    )


def _append_visit_and_update_state(
    day: date,
    vehicle_number: int,
    area: str,
    _bin: BinRecord,
    context: EventGenerationContext,
    events: list[RealWorldBinVisit | RealWorldVehicleEmptying],
    state: _VehicleDayState,
) -> None:

    observation = context.latent_fill_level_simulator.observe_visit(
        bin_id=_bin.id,
        area=area,
        visit_day=day,
    )

    event_timestamp, received_timestamp = event_timestamps_for_next_stop(
        current_x=state.current_x,
        current_y=state.current_y,
        current_timestamp=state.relative_timestamp,
        target_x=_bin.coord_x,
        target_y=_bin.coord_y,
        seconds_spent=context.seconds_per_bin_visit,
        road_network_detour_factor=context.road_network_detour_factor,
        average_speed_meters_per_second=context.average_speed_meters_per_second,
    )

    events.append(
        RealWorldBinVisit(
            day=day,
            vehicle_number=vehicle_number,
            area=area,
            fill_level=observation.fill_level,
            action=observation.action,
            bin_id=_bin.id,
            coord_x=_bin.coord_x,
            coord_y=_bin.coord_y,
            relative_event_timestamp=event_timestamp,
            relative_received_timestamp=received_timestamp,
        )
    )

    state.volume_since_emptying += _bin.volume * observation.fill_level_continuous
    state.current_x = _bin.coord_x
    state.current_y = _bin.coord_y
    state.relative_timestamp = event_timestamp


def _append_emptying_and_reset_state(day: date, vehicle_number: int,
                                     events: list[RealWorldBinVisit | RealWorldVehicleEmptying],
                                     state: _VehicleDayState, context: EventGenerationContext,
                                     is_last_of_the_tour=False) -> None:
    event_timestamp, received_timestamp = event_timestamps_for_next_stop(
        current_x=state.current_x,
        current_y=state.current_y,
        current_timestamp=state.relative_timestamp,
        target_x=context.vehicle_emptying_coords[0],
        target_y=context.vehicle_emptying_coords[1],
        seconds_spent=context.seconds_per_vehicle_emptying,
        road_network_detour_factor=context.road_network_detour_factor,
        average_speed_meters_per_second=context.average_speed_meters_per_second,
    )
    events.append(
        RealWorldVehicleEmptying(
            day=day,
            vehicle_number=vehicle_number,
            coord_x=context.vehicle_emptying_coords[0],
            coord_y=context.vehicle_emptying_coords[1],
            relative_event_timestamp=event_timestamp,
            relative_received_timestamp=received_timestamp,
            is_last_of_the_tour=is_last_of_the_tour,
        )
    )
    state.volume_since_emptying = 0
    state.current_x, state.current_y = context.vehicle_emptying_coords
    state.relative_timestamp = event_timestamp
