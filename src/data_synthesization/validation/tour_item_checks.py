from collections import defaultdict
from datetime import datetime

from data_synthesization.shared.domain.models import BinVisitRecord, TourRecord, VehicleEmptyingRecord
from data_synthesization.shared.utils.time import to_utc


def validate_tour_items_end_with_vehicle_emptying(
        *,
        tours: list[TourRecord],
        bin_visit_records: list[BinVisitRecord],
        vehicle_emptying_records: list[VehicleEmptyingRecord],
) -> None:
    last_event_by_tour: dict[int, tuple[datetime, str]] = {}
    tours_by_id = {tour.id: tour for tour in tours if tour.id is not None}
    known_tour_ids = set(tours_by_id.keys())

    vehicle_emptyings_by_tour: dict[int, int] = defaultdict(int)

    for visit in bin_visit_records:
        if visit.tour_id not in known_tour_ids:
            raise ValueError(f"bin_visit references unknown tour_id={visit.tour_id}")

        _validate_event_timestamp_within_tour_window(
            event_type="bin_visit",
            tour=tours_by_id[visit.tour_id],
            event_timestamp=visit.event_timestamp,
        )

        _update_last_event(
            last_event_by_tour=last_event_by_tour,
            tour_id=visit.tour_id,
            event_timestamp=visit.event_timestamp,
            event_type="bin_visit",
        )

    for emptying in vehicle_emptying_records:
        if emptying.tour_id not in known_tour_ids:
            raise ValueError(f"vehicle_emptying references unknown tour_id={emptying.tour_id}")

        _validate_event_timestamp_within_tour_window(
            event_type="vehicle_emptying",
            tour=tours_by_id[emptying.tour_id],
            event_timestamp=emptying.event_timestamp,
        )

        vehicle_emptyings_by_tour[emptying.tour_id] += 1
        _update_last_event(
            last_event_by_tour=last_event_by_tour,
            tour_id=emptying.tour_id,
            event_timestamp=emptying.event_timestamp,
            event_type="vehicle_emptying",
        )

    for tour_id in sorted(last_event_by_tour.keys()):
        if vehicle_emptyings_by_tour.get(tour_id, 0) == 0:
            raise ValueError(f"Tour {tour_id} has no vehicle_emptying")

        _, last_event_type = last_event_by_tour[tour_id]
        if last_event_type != "vehicle_emptying":
            raise ValueError(f"Tour {tour_id} does not end with vehicle_emptying")


def _update_last_event(
        *,
        last_event_by_tour: dict[int, tuple[datetime, str]],
        tour_id: int,
        event_timestamp: datetime,
        event_type: str,
) -> None:
    event_timestamp_utc = to_utc(event_timestamp)

    if tour_id not in last_event_by_tour:
        last_event_by_tour[tour_id] = (event_timestamp_utc, event_type)
        return

    current_last_timestamp, _ = last_event_by_tour[tour_id]
    if event_timestamp_utc >= current_last_timestamp:
        last_event_by_tour[tour_id] = (event_timestamp_utc, event_type)


def _validate_event_timestamp_within_tour_window(
        *,
        event_type: str,
        tour: TourRecord,
        event_timestamp: datetime,
) -> None:
    if tour.id is None:
        raise ValueError(f"{event_type} references unknown tour_id=None")

    event_timestamp_utc = to_utc(event_timestamp)
    tour_started_at_utc = to_utc(tour.started_at)

    if event_timestamp_utc < tour_started_at_utc:
        raise ValueError(
            f"{event_type} event_timestamp {event_timestamp_utc.isoformat()} is before "
            f"tour {tour.id} started_at {tour_started_at_utc.isoformat()}"
        )
