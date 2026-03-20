import random
from collections import defaultdict
from datetime import date, datetime, time, timezone
from pathlib import Path

from data_synthesization.config.config import load_config
from data_synthesization.db.connection import connect
from data_synthesization.db.reader import read_bin_activities, read_bins, read_nfc_tag_mappings, read_tours
from data_synthesization.db.writer import insert_bin_visits, insert_vehicle_emptyings
from data_synthesization.domain.models import BinActivityRecord, BinRecord, BinVisitRecord, NfcTagMappingRecord, TourRecord, VehicleEmptyingRecord
from data_synthesization.generation.tour_item_generator import (
    BinVisitEvent,
    VehicleEmptyingEvent,
    generate_day_tour_items,
    load_bins_by_area,
)
from data_synthesization.utils.tour_and_nfc_mapper import map_events_to_records_for_vehicle_tours
from data_synthesization.utils.generation_iterator import iter_generation_days
from data_synthesization.utils.schedule import ServiceSchedule, load_service_schedule

SCHEDULE_PATH = Path("config/schedule.yaml")
BIN_MAPPING_PATH = Path("data/static/bin_neighbourhood_mapping.csv")


def _group_tours_by_vehicle_and_day(
    tours: list[TourRecord],
) -> dict[tuple[int, date], list[TourRecord]]:
    grouped: dict[tuple[int, date], list[TourRecord]] = defaultdict(list)
    for tour in tours:
        grouped[(tour.vehicle_id, tour.started_at.date())].append(tour)

    for key in grouped:
        grouped[key].sort(key=lambda _tour: _tour.started_at)

    return grouped


"""
Returns True if the given bin is active on the given day, based on the provided bin activities.
Uses 2am as the start of the day since the nfc-tag-generator uses this time as the start of the day.
"""
def _is_bin_active_on_day(
    day: date,
    bin_id: int,
    activities_by_bin: dict[int, list[tuple[datetime, bool]]],
) -> bool:
    day_start = datetime.combine(day, time(hour=2, minute=0, second=0, microsecond=0, tzinfo=timezone.utc))

    last_active_state = False
    for activity_timestamp, active in activities_by_bin.get(bin_id, []):
        if activity_timestamp > day_start:
            break
        last_active_state = active

    return last_active_state

"""
helper function to group nfc mappings by bin and sort them by mapped_at (installation time)
"""
def _group_nfc_mappings_by_bin(
    nfc_tag_mappings: list[NfcTagMappingRecord],
) -> dict[int, list[NfcTagMappingRecord]]:
    mappings_by_bin: dict[int, list[NfcTagMappingRecord]] = defaultdict(list)

    for mapping in nfc_tag_mappings:
        mappings_by_bin[mapping.bin_id].append(mapping)

    for bin_id in mappings_by_bin:
        mappings_by_bin[bin_id].sort(key=lambda mapping: mapping.mapped_at)

    return mappings_by_bin


def _build_activities_by_bin(bin_activities: list[BinActivityRecord]) -> dict[int, list[tuple[datetime, bool]]]:
    activities_by_bin: dict[int, list[tuple[datetime, bool]]] = defaultdict(list)
    for activity in bin_activities:
        activity_timestamp = activity.activity_timestamp.astimezone(timezone.utc)
        activities_by_bin[activity.bin_id].append((activity_timestamp, activity.active))
    return activities_by_bin

"""
helper function to group events by vehicle number.
"""
def _group_events_by_vehicle(
    events: list[BinVisitEvent | VehicleEmptyingEvent],
) -> dict[int, list[BinVisitEvent | VehicleEmptyingEvent]]:
    events_by_vehicle: dict[int, list[BinVisitEvent | VehicleEmptyingEvent]] = defaultdict(list)
    for event in events:
        events_by_vehicle[event.vehicle_number].append(event)
    return events_by_vehicle


"""
Filters the dict of bins to only include those that are active on the given day, based on the provided bin activities.
"""
def _active_bins_for_day(
    day: date,
    bins_by_id: dict[int, BinRecord],
    activities_by_bin: dict[int, list[tuple[datetime, bool]]],
) -> dict[int, BinRecord]:
    return {
        bin_id: bin_record
        for bin_id, bin_record in bins_by_id.items()
        if _is_bin_active_on_day(day, bin_id, activities_by_bin)
    }


"""
Generates a list of BinVisitEvent and VehicleEmptyingEvent for a given day, service schedule and bins-to-areas mapping.

Synthetic objects which ignore the actual database schema (e.g. mapping via nfc-tag).
"""
def _generate_day_events(
    day: date,
    service_schedule: ServiceSchedule,
    bins_by_area_config: dict[str, list[int]],
    bins_by_id: dict[int, BinRecord],
    activities_by_bin: dict[int, list[tuple[datetime, bool]]],
    vehicle_emptying_coords: tuple[float, float],
    empty_after_volume: int,
) -> list[BinVisitEvent | VehicleEmptyingEvent]:
    active_bins_by_id = _active_bins_for_day(
        day=day,
        bins_by_id=bins_by_id,
        activities_by_bin=activities_by_bin,
    )
    return generate_day_tour_items(
        day=day,
        vehicles_schedules=service_schedule.vehicles,
        seasons=service_schedule.seasons,
        bins_by_area=bins_by_area_config,
        bins=active_bins_by_id,
        vehicle_emptying_coords=vehicle_emptying_coords,
        empty_after_volume=empty_after_volume,
    )

"""
For each vehicle, bin_visit and vehicle_emptying records are generated based on the given day, events and tours
"""
def _generate_records_for_day(
    day: date,
    events: list[BinVisitEvent | VehicleEmptyingEvent],
    tours_by_vehicle_day: dict[tuple[int, date], list[TourRecord]],
    nfc_mappings_by_bin: dict[int, list[NfcTagMappingRecord]],
    rng: random.Random,
    vehicle_emptying_coords: tuple[float, float],
    average_speed_meters_per_second: float,
    road_network_detour_factor: float,
    seconds_per_bin_visit: int,
    seconds_per_vehicle_emptying: int,
) -> tuple[list[BinVisitRecord], list[VehicleEmptyingRecord]]:
    day_bin_visits: list[BinVisitRecord] = []
    day_vehicle_emptyings: list[VehicleEmptyingRecord] = []

    for vehicle_number, vehicle_events in _group_events_by_vehicle(events).items():
        vehicle_tours = tours_by_vehicle_day.get((vehicle_number, day), [])

        # expand relation from vehicle_events to actual database relation (nfc_tag_mapping => bin, tour => vehicle)
        bin_visits, vehicle_emptyings = map_events_to_records_for_vehicle_tours(
            vehicle_events=vehicle_events,
            vehicle_tours=vehicle_tours,
            mappings_by_bin=nfc_mappings_by_bin,
            rng=rng,
            vehicle_emptying_coords=vehicle_emptying_coords,
            average_speed_meters_per_second=average_speed_meters_per_second,
            road_network_detour_factor=road_network_detour_factor,
            seconds_per_bin_visit=seconds_per_bin_visit,
            seconds_per_vehicle_emptying=seconds_per_vehicle_emptying,
        )
        day_bin_visits.extend(bin_visits)
        day_vehicle_emptyings.extend(vehicle_emptyings)

    return day_bin_visits, day_vehicle_emptyings


def run_generate_tour_items(config_path: str) -> None:
    config = load_config(config_path)
    service_schedule = load_service_schedule(SCHEDULE_PATH)
    bins_by_area_config = load_bins_by_area(BIN_MAPPING_PATH)
    rng = random.Random(config.simulation.seed)

    with connect(config.database.database_source_name) as connection:
        # read data from database
        bins = read_bins(connection)
        bin_activities = read_bin_activities(connection)
        tours = read_tours(connection)
        nfc_tag_mappings = read_nfc_tag_mappings(connection)

        # group data by day, bin or vehicle
        tours_by_vehicle_day = _group_tours_by_vehicle_and_day(tours)
        nfc_mappings_by_bin = _group_nfc_mappings_by_bin(nfc_tag_mappings)
        activities_by_bin = _build_activities_by_bin(bin_activities)
        bins_by_id = {_bin.id: _bin for _bin in bins}

        bin_visit_records: list[BinVisitRecord] = []
        vehicle_emptying_records: list[VehicleEmptyingRecord] = []

        for day in iter_generation_days(config):
            # generate synthetic helper objects
            day_events = _generate_day_events(
                day=day,
                service_schedule=service_schedule,
                bins_by_area_config=bins_by_area_config,
                bins_by_id=bins_by_id,
                activities_by_bin=activities_by_bin,
                vehicle_emptying_coords=config.tour_item_generation.vehicle_emptying_coords,
                empty_after_volume=config.tour_item_generation.empty_after_volume,
            )
            # generate database rows (considerings e.g. mapping via nfc-tag and mapping to virtual tour)
            day_bin_visits, day_vehicle_emptyings = _generate_records_for_day(
                day=day,
                events=day_events,
                tours_by_vehicle_day=tours_by_vehicle_day,
                nfc_mappings_by_bin=nfc_mappings_by_bin,
                rng=rng,
                vehicle_emptying_coords=config.tour_item_generation.vehicle_emptying_coords,
                average_speed_meters_per_second=config.tour_and_nfc_mapping.average_speed_meters_per_second,
                road_network_detour_factor=config.tour_and_nfc_mapping.road_network_detour_factor,
                seconds_per_bin_visit=config.tour_and_nfc_mapping.seconds_per_bin_visit,
                seconds_per_vehicle_emptying=config.tour_and_nfc_mapping.seconds_per_vehicle_emptying,
            )
            bin_visit_records.extend(day_bin_visits)
            vehicle_emptying_records.extend(day_vehicle_emptyings)
            break

        insert_bin_visits(connection, bin_visit_records)
        insert_vehicle_emptyings(connection, vehicle_emptying_records)
        connection.commit()

    print(f"Generated bin_visit rows: {len(bin_visit_records)}")
    print(f"Generated vehicle_emptying rows: {len(vehicle_emptying_records)}")
