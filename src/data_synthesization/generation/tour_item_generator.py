import csv
from dataclasses import dataclass
from datetime import date
from math import hypot
from pathlib import Path

from data_synthesization.domain.models import BinRecord
from data_synthesization.utils.service_schedule import VehicleSchedule, areas_for_vehicle_day

VEHICLE_EMPTYING_COORDS = (2586282.75, 1218884.52)
EMTPY_AFTER_VOLUME = 2000


@dataclass(frozen=True)
class TourItemVisit:
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


@dataclass(frozen=True)
class TourItemsResult:
    visits: list[TourItemVisit]
    events: list[TourItemVisit | VehicleEmptyingEvent]


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


def generate_day_tour_items(
    day: date,
    vehicles: list[VehicleSchedule],
    seasons: dict[str, tuple[tuple[int, int], tuple[int, int]]],
    bins_by_area: dict[str, list[int]],
    bins: dict[int, BinRecord],
) -> TourItemsResult:
    visits: list[TourItemVisit] = []
    events: list[TourItemVisit | VehicleEmptyingEvent] = []

    for vehicle in vehicles:
        volume_since_emptying = 0
        # start from Müve instead of street inspectorate
        current_x, current_y = VEHICLE_EMPTYING_COORDS
        areas = areas_for_vehicle_day(vehicle, day, seasons)

        for area in areas:
            ordered_bins = _nearest_bin_order(
                bins_by_area.get(area, []),
                bins,
                start_x=current_x,
                start_y=current_y,
            )
            for bin_id in ordered_bins:
                _bin = bins[bin_id]
                visit = TourItemVisit(
                    day=day,
                    vehicle_number=vehicle.vehicle_number,
                    area=area,
                    bin_id=bin_id,
                    coord_x=_bin.coord_x,
                    coord_y=_bin.coord_y,
                )
                visits.append(visit)
                events.append(visit)
                volume_since_emptying += _bin.volume
                current_x = _bin.coord_x
                current_y = _bin.coord_y

                if volume_since_emptying >= EMTPY_AFTER_VOLUME:
                    emptying_event = VehicleEmptyingEvent(
                        day=day,
                        vehicle_number=vehicle.vehicle_number,
                        coord_x=VEHICLE_EMPTYING_COORDS[0],
                        coord_y=VEHICLE_EMPTYING_COORDS[1],
                    )
                    events.append(emptying_event)
                    volume_since_emptying = 0
                    current_x, current_y = VEHICLE_EMPTYING_COORDS

        end_of_tour_emptying = VehicleEmptyingEvent(
            day=day,
            vehicle_number=vehicle.vehicle_number,
            coord_x=VEHICLE_EMPTYING_COORDS[0],
            coord_y=VEHICLE_EMPTYING_COORDS[1],
        )
        events.append(end_of_tour_emptying)

    return TourItemsResult(visits=visits, events=events)
