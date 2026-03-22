import random
from datetime import datetime, timedelta, timezone
from math import hypot
from uuid import uuid4

from data_synthesization.feature.tour_item.types import BinVisitEvent, VehicleEmptyingEvent
from data_synthesization.generation.latent_filllevel_simulator import LatentFillLevelSimulator
from data_synthesization.shared.domain.enums import ConnectivityState
from data_synthesization.shared.domain.models import BinVisitRecord, NfcTagMappingRecord, TourRecord, VehicleEmptyingRecord


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
    latent_filllevel_simulator: LatentFillLevelSimulator,
) -> tuple[list[BinVisitRecord], list[VehicleEmptyingRecord], dict[int, datetime]]:
    bin_visit_records: list[BinVisitRecord] = []
    vehicle_emptying_records: list[VehicleEmptyingRecord] = []

    belongs_to_first_virtual_tour = _build_virtual_tour_assignments(len(vehicle_events), rng)
    last_vehicle_emptying_per_tour: dict[int, datetime] = {}

    for tour_index, tour in enumerate(vehicle_tours):
        last_vehicle_emptying_at = _map_single_tour_events_to_records(
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
            latent_filllevel_simulator=latent_filllevel_simulator,
        )
        last_vehicle_emptying_per_tour[tour.id] = last_vehicle_emptying_at

    return bin_visit_records, vehicle_emptying_records, last_vehicle_emptying_per_tour


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


def _find_mapping_for_bin_visit_day(
    exact_time: datetime,
    bin_id: int,
    mappings_by_bin: dict[int, list[NfcTagMappingRecord]],
) -> int | None:
    for mapping in mappings_by_bin.get(bin_id, []):
        if mapping.mapped_at <= exact_time and (mapping.unmapped_at is None or exact_time < mapping.unmapped_at):
            return mapping.id
    return None


def _build_virtual_tour_assignments(number_of_events: int, rng: random.Random) -> list[int]:
    number_scanned_by_first_virtual_tour = rng.randint(0, number_of_events)
    number_scanned_by_second_virtual_tour = number_of_events - number_scanned_by_first_virtual_tour
    belongs_to_first_virtual_tour = [1] * number_scanned_by_first_virtual_tour + [0] * number_scanned_by_second_virtual_tour
    rng.shuffle(belongs_to_first_virtual_tour)
    return belongs_to_first_virtual_tour


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


def _append_bin_visit_record_if_possible(
    event: BinVisitEvent,
    event_timestamp: datetime,
    tour: TourRecord,
    mappings_by_bin: dict[int, list[NfcTagMappingRecord]],
    bin_visit_records: list[BinVisitRecord],
    latent_filllevel_simulator: LatentFillLevelSimulator,
) -> None:
    nfc_tag_mapping_id = _find_mapping_for_bin_visit_day(
        exact_time=event_timestamp,
        bin_id=event.bin_id,
        mappings_by_bin=mappings_by_bin,
    )
    if nfc_tag_mapping_id is None:
        return

    observation = latent_filllevel_simulator.observe_visit(
        bin_id=event.bin_id,
        area=event.area,
        visit_day=event.day,
    )

    bin_visit_records.append(
        BinVisitRecord(
            client_event_id=str(uuid4()),
            event_timestamp=event_timestamp,
            received_timestamp=event_timestamp + timedelta(seconds=1),
            connectivity_state=ConnectivityState.ONLINE,
            fill_level=observation.fill_level,
            action=observation.action,
            tour_id=tour.id,
            nfc_tag_mapping_id=nfc_tag_mapping_id,
        )
    )


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
            connectivity_state=ConnectivityState.ONLINE,
            tour_id=tour.id,
        )
    )


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
    latent_filllevel_simulator: LatentFillLevelSimulator,
) -> datetime:
    current_x, current_y = vehicle_emptying_coords
    current_timestamp = tour.started_at.astimezone(timezone.utc)

    last_vehicle_emptying_event_timestamp: datetime | None = None

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
                    latent_filllevel_simulator=latent_filllevel_simulator,
                )
        else:
            _append_vehicle_emptying_record_if_logged(
                event=event,
                event_timestamp=event_timestamp,
                tour=tour,
                rng=rng,
                vehicle_emptying_records=vehicle_emptying_records,
            )
            last_vehicle_emptying_event_timestamp = event_timestamp

        current_x = event.coord_x
        current_y = event.coord_y

    return last_vehicle_emptying_event_timestamp
