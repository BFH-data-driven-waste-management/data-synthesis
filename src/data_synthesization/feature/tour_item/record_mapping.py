import random
from datetime import datetime
from uuid import uuid4

from data_synthesization.feature.tour_item.types import BinVisitEvent, VehicleEmptyingEvent
from data_synthesization.shared.domain.enums import ConnectivityState
from data_synthesization.shared.domain.models import BinVisitRecord, TourRecord, VehicleEmptyingRecord


def map_events_to_records_for_vehicle_tours(
        vehicle_events: list[BinVisitEvent | VehicleEmptyingEvent],
        vehicle_tours: list[TourRecord],
        rng: random.Random,
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
            rng=rng,
            bin_visit_records=bin_visit_records,
            vehicle_emptying_records=vehicle_emptying_records,
        )
        last_vehicle_emptying_per_tour[tour.id] = last_vehicle_emptying_at

    return bin_visit_records, vehicle_emptying_records, last_vehicle_emptying_per_tour


def _map_single_tour_events_to_records(
        tour_index: int,
        tour: TourRecord,
        vehicle_events: list[BinVisitEvent | VehicleEmptyingEvent],
        belongs_to_first_virtual_tour: list[int],
        rng: random.Random,
        bin_visit_records: list[BinVisitRecord],
        vehicle_emptying_records: list[VehicleEmptyingRecord],
) -> datetime:
    last_vehicle_emptying_event_timestamp: datetime | None = None

    for event_index, event in enumerate(vehicle_events):
        if isinstance(event, BinVisitEvent):
            if _event_assigned_to_current_virtual_tour(
                    event_index=event_index,
                    tour_index=tour_index,
                    belongs_to_first_virtual_tour=belongs_to_first_virtual_tour,
                    rng=rng,
            ):
                _append_bin_visit_record_if_possible(
                    event=event,
                    tour=tour,
                    bin_visit_records=bin_visit_records
                )
        else:
            _append_vehicle_emptying_record_if_logged(
                event=event,
                tour=tour,
                rng=rng,
                vehicle_emptying_records=vehicle_emptying_records,
            )
            last_vehicle_emptying_event_timestamp = event.event_timestamp

    return last_vehicle_emptying_event_timestamp


def _build_virtual_tour_assignments(number_of_events: int, rng: random.Random) -> list[int]:
    number_scanned_by_first_virtual_tour = rng.randint(0, number_of_events)
    number_scanned_by_second_virtual_tour = number_of_events - number_scanned_by_first_virtual_tour
    belongs_to_first_virtual_tour = [1] * number_scanned_by_first_virtual_tour + [
        0] * number_scanned_by_second_virtual_tour
    rng.shuffle(belongs_to_first_virtual_tour)
    return belongs_to_first_virtual_tour


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
        tour: TourRecord,
        bin_visit_records: list[BinVisitRecord],
) -> None:
    if event.nfc_tag_mapping_id is None:
        return

    bin_visit_records.append(
        BinVisitRecord(
            client_event_id=str(uuid4()),
            event_timestamp=event.event_timestamp,
            received_timestamp=event.received_timestamp,
            connectivity_state=ConnectivityState.ONLINE,
            fill_level=event.fill_level,
            action=event.action,
            tour_id=tour.id,
            nfc_tag_mapping_id=event.nfc_tag_mapping_id,
        )
    )


def _append_vehicle_emptying_record_if_logged(
        *,
        event: VehicleEmptyingEvent,
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
            event_timestamp=event.event_timestamp,
            received_timestamp=event.received_timestamp,
            connectivity_state=ConnectivityState.ONLINE,
            tour_id=tour.id,
        )
    )
