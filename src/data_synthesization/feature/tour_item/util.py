from collections import defaultdict
from datetime import date, datetime, time, timezone

from data_synthesization.feature.tour_item.types import BinVisitEvent, VehicleEmptyingEvent
from data_synthesization.shared.domain.models import TourRecord, NfcTagMappingRecord, BinActivityRecord, BinRecord


def _group_tours_by_vehicle_and_day(tours: list[TourRecord]) -> dict[tuple[int, date], list[TourRecord]]:
    grouped: dict[tuple[int, date], list[TourRecord]] = defaultdict(list)
    for tour in tours:
        grouped[(tour.vehicle_id, tour.started_at.date())].append(tour)

    for key in grouped:
        grouped[key].sort(key=lambda _tour: _tour.started_at)

    return grouped


def _group_nfc_mappings_by_bin(
        nfc_tag_mappings: list[NfcTagMappingRecord],
) -> dict[int, list[NfcTagMappingRecord]]:
    mappings_by_bin: dict[int, list[NfcTagMappingRecord]] = defaultdict(list)

    for mapping in nfc_tag_mappings:
        mappings_by_bin[mapping.bin_id].append(mapping)

    for bin_id in mappings_by_bin:
        mappings_by_bin[bin_id].sort(key=lambda mapping: mapping.mapped_at)

    return mappings_by_bin


def _group_activities_by_bin(bin_activities: list[BinActivityRecord]) -> dict[int, list[tuple[datetime, bool]]]:
    activities_by_bin: dict[int, list[tuple[datetime, bool]]] = defaultdict(list)
    for activity in bin_activities:
        activity_timestamp = activity.activity_timestamp.astimezone(timezone.utc)
        activities_by_bin[activity.bin_id].append((activity_timestamp, activity.active))
    return activities_by_bin


def _group_events_by_vehicle(
        events: list[BinVisitEvent | VehicleEmptyingEvent],
) -> dict[int, list[BinVisitEvent | VehicleEmptyingEvent]]:
    events_by_vehicle: dict[int, list[BinVisitEvent | VehicleEmptyingEvent]] = defaultdict(list)
    for event in events:
        events_by_vehicle[event.vehicle_number].append(event)
    return events_by_vehicle


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
