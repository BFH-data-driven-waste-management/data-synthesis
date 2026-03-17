import random
from collections import defaultdict
from datetime import date, timedelta, timezone
from math import hypot
from pathlib import Path
from uuid import uuid4

from data_synthesization.config.config import load_config
from data_synthesization.db.connection import connect
from data_synthesization.db.reader import read_bins, read_tours
from data_synthesization.db.writer import insert_bin_visits, insert_vehicle_emptyings
from data_synthesization.domain.models import BinVisitRecord, TourRecord, VehicleEmptyingRecord
from data_synthesization.generation.tour_item_generator import (
    VEHICLE_EMPTYING_COORDS,
    TourItemVisit,
    VehicleEmptyingEvent,
    generate_day_tour_items,
    load_bins_by_area,
)
from data_synthesization.utils.generation_iterator import iter_generation_days
from data_synthesization.utils.schedule import load_service_schedule

SCHEDULE_PATH = Path("config/schedule.yaml")
BIN_MAPPING_PATH = Path("data/static/bin_neighbourhood_mapping.csv")
AVERAGE_SPEED_METERS_PER_SECOND = 3
ROAD_NETWORK_DETOUR_FACTOR = 2
SECONDS_PER_BIN_VISIT = 120
SECONDS_PER_VEHICLE_EMPTYING = 300


def _estimate_travel_seconds(
    start_x: float,
    start_y: float,
    target_x: float,
    target_y: float,
) -> int:
    direct_distance_meters = hypot(target_x - start_x, target_y - start_y)
    network_distance_meters = direct_distance_meters * ROAD_NETWORK_DETOUR_FACTOR
    return max(1, int(network_distance_meters / AVERAGE_SPEED_METERS_PER_SECOND))


def _group_tours_by_vehicle_and_day(
    tours: list[TourRecord],
) -> dict[tuple[int, date], list[TourRecord]]:
    grouped: dict[tuple[int, date], list[TourRecord]] = defaultdict(list)
    for tour in tours:
        grouped[(tour.vehicle_id, tour.started_at.date())].append(tour)

    for key in grouped:
        grouped[key].sort(key=lambda _tour: _tour.started_at)

    return grouped


def run_generate_tour_items(config_path: str) -> None:
    config = load_config(config_path)
    service_schedule = load_service_schedule(SCHEDULE_PATH)
    bins_by_area_config = load_bins_by_area(BIN_MAPPING_PATH)
    rng = random.Random(config.simulation.seed)

    with connect(config.database.database_source_name) as connection:
        bins = read_bins(connection)
        tours = read_tours(connection)
        tours_by_vehicle_day = _group_tours_by_vehicle_and_day(tours)
        bins_by_id = {_bin.id: _bin for _bin in bins}

        bin_visit_records: list[BinVisitRecord] = []
        vehicle_emptying_records: list[VehicleEmptyingRecord] = []

        for day in iter_generation_days(config):
            events = generate_day_tour_items(
                day=day,
                vehicles=service_schedule.vehicles,
                seasons=service_schedule.seasons,
                bins_by_area=bins_by_area_config,
                bins=bins_by_id,
            )

            events_by_vehicle: dict[int, list[TourItemVisit | VehicleEmptyingEvent]] = defaultdict(list)
            for event in events:
                events_by_vehicle[event.vehicle_number].append(event)

            # map bin visits and vehicle emptyings to the correct tour (day, vehicle)
            for vehicle_number, vehicle_events in events_by_vehicle.items():
                vehicle_tours = tours_by_vehicle_day.get((vehicle_number, day), [])
                print("tours for day", day, "vehicle", vehicle_number, vehicle_tours)

                # randomly spread events over both virtual tours
                number_of_events = len(vehicle_events)
                number_scanned_by_first_virtual_tour  = rng.randint(0, number_of_events)
                number_scanned_by_second_virtual_tour = number_of_events - number_scanned_by_first_virtual_tour

                # array with 1 for first virtual tour, 0 for second virtual tour
                is_first_virtual_tour = [1] * number_scanned_by_first_virtual_tour + [0] * number_scanned_by_second_virtual_tour
                rng.shuffle(is_first_virtual_tour)


                for tour_index, tour in enumerate(vehicle_tours):
                    current_x, current_y = VEHICLE_EMPTYING_COORDS
                    current_timestamp = tour.started_at.astimezone(timezone.utc)

                    for event_index, event in enumerate(vehicle_events):
                        # ensure every event is only logged by one tour
                        travel_seconds = _estimate_travel_seconds(
                            start_x=current_x,
                            start_y=current_y,
                            target_x=event.coord_x,
                            target_y=event.coord_y,
                        )
                        event_seconds = SECONDS_PER_BIN_VISIT if isinstance(event, TourItemVisit) else SECONDS_PER_VEHICLE_EMPTYING
                        current_timestamp += timedelta(seconds=travel_seconds + event_seconds)
                        event_timestamp = current_timestamp

                        if isinstance(event, TourItemVisit):
                            # make sure every bin visit is only logged by one virtual tour
                            event_belongs_not_to_this_virtual_tour = (is_first_virtual_tour[event_index - 1] == 1 and tour_index == 1) or (
                                    is_first_virtual_tour[event_index - 1] == 0 and tour_index == 0)
                            # 1 in 100 bin visits has the chance to be logged by both virtual tours (operator error)
                            event_belongs_to_both_virtual_tour_mistakenly = rng.random() < 0.01

                            if event_belongs_not_to_this_virtual_tour or event_belongs_to_both_virtual_tour_mistakenly:
                                bin_visit_records.append(
                                    BinVisitRecord(
                                        client_event_id=str(uuid4()),
                                        event_timestamp=event_timestamp,
                                        received_timestamp=event_timestamp+timedelta(seconds=1),
                                        connectivity_state="ONLINE",
                                        fill_level="FULL",
                                        action="EMPTIED",
                                        tour_id=tour.id,
                                        nfc_tag_mapping_id=None,
                                    )
                                )
                                print(
                                    f"bin_visit day={event.day.isoformat()} vehicle={event.vehicle_number} "
                                    f"tour_id={tour.id} timestamp={event_timestamp.isoformat()} "
                                    f"area={event.area} bin_id={event.bin_id} "
                                    f"coord_x={event.coord_x:.2f} coord_y={event.coord_y:.2f}"
                                )
                        else:
                            # every 1 in 20 vehicle emptyings is logged by only one virtual tour (one operator forgets)
                            event_was_not_logged_by_virtual_tour_mistakenly = rng.random() < 0.05

                            if not event_was_not_logged_by_virtual_tour_mistakenly:
                                vehicle_emptying_records.append(
                                    VehicleEmptyingRecord(
                                        client_event_id=str(uuid4()),
                                        event_timestamp=event_timestamp,
                                        received_timestamp=event_timestamp+timedelta(seconds=1),
                                        connectivity_state="ONLINE",
                                        tour_id=tour.id,
                                    )
                                )
                                print(
                                    f"vehicle_emptying day={event.day.isoformat()} vehicle={event.vehicle_number} "
                                    f"tour_id={tour.id} timestamp={event_timestamp.isoformat()} "
                                    f"coord_x={event.coord_x:.2f} coord_y={event.coord_y:.2f}"
                                )

                        current_x = event.coord_x
                        current_y = event.coord_y
            break
        insert_bin_visits(connection, bin_visit_records)
        insert_vehicle_emptyings(connection, vehicle_emptying_records)
        connection.commit()

    print(f"Generated bin_visit rows: {len(bin_visit_records)}")
    print(f"Generated vehicle_emptying rows: {len(vehicle_emptying_records)}")
