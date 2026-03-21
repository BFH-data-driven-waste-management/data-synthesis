import csv
from dataclasses import dataclass
from datetime import date
from math import hypot
from pathlib import Path

from data_synthesization.shared.domain.models import BinRecord
from data_synthesization.generation.latent_filllevel_simulator import LatentFillLevelSimulator
from data_synthesization.utils.schedule import VehicleSchedule, areas_for_vehicle_day


@dataclass(frozen=True)
class BinVisitEvent:
    day: date
    vehicle_number: int
    area: str
    bin_id: int
    coord_x: float
    coord_y: float


@dataclass(frozen=True)
class VehicleEmptyingEvent:
    day: date
    vehicle_number: int
    coord_x: float
    coord_y: float


@dataclass
class _VehicleDayState:
    volume_since_emptying: float
    current_x: float
    current_y: float


def load_bins_by_area(mapping_path: str | Path) -> dict[str, list[int]]:
    bins_by_area: dict[str, list[int]] = {}
    with Path(mapping_path).open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            area = str(row["name"])
            bins_by_area.setdefault(area, []).append(int(row["bin_id"]))
    return bins_by_area


"""
after each bin drive to the nearest bin in the same area.
=> implicitly ignoring vehicle emptyings during the same area
"""
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

"""
helper for initial state of a vehicle each day
"""
def _initial_vehicle_day_state(vehicle_emptying_coords: tuple[float, float]) -> _VehicleDayState:
    return _VehicleDayState(
        volume_since_emptying=0,
        current_x=vehicle_emptying_coords[0],
        current_y=vehicle_emptying_coords[1],
    )

"""
helper for building a bin_visit event
"""
def _build_bin_visit_event(day: date, vehicle_number: int, area: str, _bin: BinRecord) -> BinVisitEvent:
    return BinVisitEvent(
        day=day,
        vehicle_number=vehicle_number,
        area=area,
        bin_id=_bin.id,
        coord_x=_bin.coord_x,
        coord_y=_bin.coord_y,
    )

"""
helper for building a vehicle_emptying event
"""
def _build_vehicle_emptying_event(
    day: date,
    vehicle_number: int,
    vehicle_emptying_coords: tuple[float, float],
) -> VehicleEmptyingEvent:
    return VehicleEmptyingEvent(
        day=day,
        vehicle_number=vehicle_number,
        coord_x=vehicle_emptying_coords[0],
        coord_y=vehicle_emptying_coords[1],
    )

"""
Append a bin_visit event and update the state of the vehicle.
- update the volume since last vehicle_emptying 
- update the current position of the vehicle
"""
def _append_visit_and_update_state(
    day: date,
    vehicle_number: int,
    area: str,
    _bin: BinRecord,
    visits: list[BinVisitEvent],
    events: list[BinVisitEvent | VehicleEmptyingEvent],
    state: _VehicleDayState,
    latent_filllevel_simulator: LatentFillLevelSimulator,
) -> None:
    visit = _build_bin_visit_event(day=day, vehicle_number=vehicle_number, area=area, _bin=_bin)
    visits.append(visit)
    events.append(visit)

    latent_collection_ratio = latent_filllevel_simulator.latent_collection_ratio_for_visit(
        bin_id=_bin.id,
        area=area,
        visit_day=day,
    )
    state.volume_since_emptying += _bin.volume * latent_collection_ratio
    state.current_x = _bin.coord_x
    state.current_y = _bin.coord_y

"""
Append a vehicle_emptying event and reset the state of the vehicle.
- reset the volume since last vehicle_emptying 
- reset the current position of the vehicle to the emptying position "VEHICLE_EMPTYING_COORDS"""
def _append_emptying_and_reset_state(
    day: date,
    vehicle_number: int,
    events: list[BinVisitEvent | VehicleEmptyingEvent],
    state: _VehicleDayState,
    vehicle_emptying_coords: tuple[float, float],
) -> None:
    events.append(
        _build_vehicle_emptying_event(
            day=day,
            vehicle_number=vehicle_number,
            vehicle_emptying_coords=vehicle_emptying_coords,
        )
    )
    state.volume_since_emptying = 0
    state.current_x, state.current_y = vehicle_emptying_coords


"""
Append all events of a given vehicle and day for a given area to events lists.
"""
def _append_area_events(
    day: date,
    vehicle_number: int,
    area: str,
    bins_by_area: dict[str, list[int]],
    bins: dict[int, BinRecord],
    visits: list[BinVisitEvent],
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
            visits=visits,
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

"""
Append all events of a given vehicle and day. Ends with a vehicle_emptying event.
"""
def _append_vehicle_day_events(
    day: date,
    vehicle_schedule: VehicleSchedule,
    areas: list[str],
    bins_by_area: dict[str, list[int]],
    bins: dict[int, BinRecord],
    visits: list[BinVisitEvent],
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
            visits=visits,
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

"""
central function to generate tour items (bin_visits and vehicle_emptyings) for a given:
- day
- vehicle schedule (from config)
- seasons (from config)
- bins-to-areas mapping (from config)
- bins by area (database)

these are synthetic helper objects (e.g. direct mapping to bin instead of nfc-tags)

implements current routing algorithm.
"""
def generate_day_tour_items(
    day: date,
    vehicles_schedules: list[VehicleSchedule],
    seasons: dict[str, tuple[tuple[int, int], tuple[int, int]]],
    bins_by_area: dict[str, list[int]],
    bins: dict[int, BinRecord],
    vehicle_emptying_coords: tuple[float, float],
    empty_after_volume: int,
    latent_filllevel_simulator: LatentFillLevelSimulator,
) -> list[BinVisitEvent | VehicleEmptyingEvent]:
    visits: list[BinVisitEvent] = []
    events: list[BinVisitEvent | VehicleEmptyingEvent] = []

    for vehicle_schedule in vehicles_schedules:
        areas = areas_for_vehicle_day(vehicle_schedule, day, seasons)
        _append_vehicle_day_events(
            day=day,
            vehicle_schedule=vehicle_schedule,
            areas=areas,
            bins_by_area=bins_by_area,
            bins=bins,
            visits=visits,
            events=events,
            vehicle_emptying_coords=vehicle_emptying_coords,
            empty_after_volume=empty_after_volume,
            latent_filllevel_simulator=latent_filllevel_simulator,
        )

    return events
