import random
from datetime import datetime, timedelta, timezone
from math import hypot
from uuid import uuid4

from data_synthesization.domain.models import BinVisitRecord, NfcTagMappingRecord, TourRecord, VehicleEmptyingRecord
from data_synthesization.generation.tour_item_generator import BinVisitEvent, VehicleEmptyingEvent

"""
helper function to estimate the travel time between two coordinates based on euclidean distance and average speed with the use of a detour factor.
"""
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

"""
find the nfc tag mapping for a given day and bin. 
(the last mapping which was active before `exact_time`)
"""
def _find_mapping_for_bin_visit_day(
    exact_time: datetime,
    bin_id: int,
    mappings_by_bin: dict[int, list[NfcTagMappingRecord]],
) -> int | None:
    for mapping in mappings_by_bin.get(bin_id, []):
        if mapping.mapped_at <= exact_time and (mapping.unmapped_at is None or exact_time < mapping.unmapped_at):
            return mapping.id
    return None

"""
Note: 
- this function is must be refactored for more the 2 virtual tours (if more than 2 crew members per vehicle are used)
- this function considers all events - including vehicle emptying - to create a random assignment of events to virtual tours.
    - since vehicle emptyings are supposed to be logged by both virtual tours anyways, their assignment in this function is just ignored.
"""
def _build_virtual_tour_assignments(number_of_events: int, rng: random.Random) -> list[int]:
    number_scanned_by_first_virtual_tour = rng.randint(0, number_of_events)
    number_scanned_by_second_virtual_tour = number_of_events - number_scanned_by_first_virtual_tour
    belongs_to_first_virtual_tour = [1] * number_scanned_by_first_virtual_tour + [0] * number_scanned_by_second_virtual_tour
    rng.shuffle(belongs_to_first_virtual_tour)
    return belongs_to_first_virtual_tour

"""
helper function to calculate the next timestamp for a given event.
append the estimated travel time and the time for handling the event (e.g. emptying a bin)
"""
def _event_timestamp_for_next_stop(
    current_x: float,
    current_y: float,
    current_timestamp: datetime,
    event: BinVisitEvent | VehicleEmptyingEvent,
    seconds_per_bin_visit: int,
    seconds_per_vehicle_emptying: int,
    road_network_detour_factor: float,
    average_speed_meters_per_second: float,
) -> datetime:
    travel_seconds = _estimate_travel_seconds(
        start_x=current_x,
        start_y=current_y,
        target_x=event.coord_x,
        target_y=event.coord_y,
        road_network_detour_factor=road_network_detour_factor,
        average_speed_meters_per_second=average_speed_meters_per_second,
    )
    event_seconds = seconds_per_bin_visit if isinstance(event, BinVisitEvent) else seconds_per_vehicle_emptying
    return current_timestamp + timedelta(seconds=travel_seconds + event_seconds)

"""
helper to determine if an event belongs to the current virtual tour.
should only be called for bin_visits.
"""
def _event_assigned_to_current_virtual_tour(
    event_index: int,
    tour_index: int,
    belongs_to_first_virtual_tour: list[int],
    rng: random.Random,
) -> bool:
    assigned_to_first_virtual_tour = belongs_to_first_virtual_tour[event_index] == 1
    event_belongs_not_to_this_virtual_tour = (
        (assigned_to_first_virtual_tour and tour_index == 1)
        or (not assigned_to_first_virtual_tour and tour_index == 0)
    )
    event_belongs_to_both_virtual_tour_mistakenly = rng.random() < 0.01
    return not event_belongs_not_to_this_virtual_tour or event_belongs_to_both_virtual_tour_mistakenly

"""
create actually database record under consideration of the correct (at this time mapped) nfc tag and the correct tour (this vehicle, this day)
"""
def _append_bin_visit_record_if_possible(
    event: BinVisitEvent,
    event_timestamp: datetime,
    tour: TourRecord,
    mappings_by_bin: dict[int, list[NfcTagMappingRecord]],
    bin_visit_records: list[BinVisitRecord],
) -> None:
    nfc_tag_mapping_id = _find_mapping_for_bin_visit_day(
        exact_time=event_timestamp,
        bin_id=event.bin_id,
        mappings_by_bin=mappings_by_bin,
    )
    if nfc_tag_mapping_id is None:
        return

    bin_visit_records.append(
        BinVisitRecord(
            client_event_id=str(uuid4()),
            event_timestamp=event_timestamp,
            received_timestamp=event_timestamp + timedelta(seconds=1),
            connectivity_state="ONLINE",
            fill_level="FULL",
            action="EMPTIED",
            tour_id=tour.id,
            nfc_tag_mapping_id=nfc_tag_mapping_id,
        )
    )
    print(
        f"bin_visit day={event.day.isoformat()} vehicle={event.vehicle_number} "
        f"tour_id={tour.id} timestamp={event_timestamp.isoformat()} "
        f"area={event.area} bin_id={event.bin_id} "
        f"coord_x={event.coord_x:.2f} coord_y={event.coord_y:.2f}"
    )

"""
create actually database record under consideration of the correct tour (this vehicle, this day) and sync-attributes.
"""
def _append_vehicle_emptying_record_if_logged(
    *,
    event: VehicleEmptyingEvent,
    event_timestamp: datetime,
    tour: TourRecord,
    rng: random.Random,
    vehicle_emptying_records: list[VehicleEmptyingRecord],
) -> None:
    event_was_not_logged_by_virtual_tour_mistakenly = rng.random() < 0.05
    if event_was_not_logged_by_virtual_tour_mistakenly:
        return

    vehicle_emptying_records.append(
        VehicleEmptyingRecord(
            client_event_id=str(uuid4()),
            event_timestamp=event_timestamp,
            received_timestamp=event_timestamp + timedelta(seconds=1),
            connectivity_state="ONLINE",
            tour_id=tour.id,
        )
    )
    print(
        f"vehicle_emptying day={event.day.isoformat()} vehicle={event.vehicle_number} "
        f"tour_id={tour.id} timestamp={event_timestamp.isoformat()} "
        f"coord_x={event.coord_x:.2f} coord_y={event.coord_y:.2f}"
    )

"""
maps events of a *single virtual tour* to database records.
for each event the next timestamp is calculated and the event is appended to the correct list of records.
"""
def _map_single_tour_events_to_records(
    tour_index: int,
    tour: TourRecord,
    vehicle_events: list[BinVisitEvent | VehicleEmptyingEvent],
    belongs_to_first_virtual_tour: list[int],
    mappings_by_bin: dict[int, list[NfcTagMappingRecord]],
    rng: random.Random,
    bin_visit_records: list[BinVisitRecord],
    vehicle_emptying_records: list[VehicleEmptyingRecord],
    vehicle_emptying_coords: tuple[float, float],
    average_speed_meters_per_second: float,
    road_network_detour_factor: float,
    seconds_per_bin_visit: int,
    seconds_per_vehicle_emptying: int,
) -> None:
    current_x, current_y = vehicle_emptying_coords
    current_timestamp = tour.started_at.astimezone(timezone.utc)

    for event_index, event in enumerate(vehicle_events):
        event_timestamp = _event_timestamp_for_next_stop(
            current_x=current_x,
            current_y=current_y,
            current_timestamp=current_timestamp,
            event=event,
            seconds_per_bin_visit=seconds_per_bin_visit,
            seconds_per_vehicle_emptying=seconds_per_vehicle_emptying,
            road_network_detour_factor=road_network_detour_factor,
            average_speed_meters_per_second=average_speed_meters_per_second,
        )
        current_timestamp = event_timestamp

        if isinstance(event, BinVisitEvent):
            if _event_assigned_to_current_virtual_tour(
                event_index=event_index,
                tour_index=tour_index,
                belongs_to_first_virtual_tour=belongs_to_first_virtual_tour,
                rng=rng,
            ):
                _append_bin_visit_record_if_possible(
                    event=event,
                    event_timestamp=event_timestamp,
                    tour=tour,
                    mappings_by_bin=mappings_by_bin,
                    bin_visit_records=bin_visit_records,
                )
        else:
            _append_vehicle_emptying_record_if_logged(
                event=event,
                event_timestamp=event_timestamp,
                tour=tour,
                rng=rng,
                vehicle_emptying_records=vehicle_emptying_records,
            )

        current_x = event.coord_x
        current_y = event.coord_y

"""
central function to map synthetic events to database records for a given vehicle.
loops over the virtual tours of the vehicle.
"""
def map_events_to_records_for_vehicle_tours(
    vehicle_events: list[BinVisitEvent | VehicleEmptyingEvent],
    vehicle_tours: list[TourRecord],
    mappings_by_bin: dict[int, list[NfcTagMappingRecord]],
    rng: random.Random,
    vehicle_emptying_coords: tuple[float, float],
    average_speed_meters_per_second: float,
    road_network_detour_factor: float,
    seconds_per_bin_visit: int,
    seconds_per_vehicle_emptying: int,
) -> tuple[list[BinVisitRecord], list[VehicleEmptyingRecord]]:
    bin_visit_records: list[BinVisitRecord] = []
    vehicle_emptying_records: list[VehicleEmptyingRecord] = []

    belongs_to_first_virtual_tour = _build_virtual_tour_assignments(len(vehicle_events), rng)

    for tour_index, tour in enumerate(vehicle_tours):
        _map_single_tour_events_to_records(
            tour_index=tour_index,
            tour=tour,
            vehicle_events=vehicle_events,
            belongs_to_first_virtual_tour=belongs_to_first_virtual_tour,
            mappings_by_bin=mappings_by_bin,
            rng=rng,
            bin_visit_records=bin_visit_records,
            vehicle_emptying_records=vehicle_emptying_records,
            vehicle_emptying_coords=vehicle_emptying_coords,
            average_speed_meters_per_second=average_speed_meters_per_second,
            road_network_detour_factor=road_network_detour_factor,
            seconds_per_bin_visit=seconds_per_bin_visit,
            seconds_per_vehicle_emptying=seconds_per_vehicle_emptying,
        )

    return bin_visit_records, vehicle_emptying_records
