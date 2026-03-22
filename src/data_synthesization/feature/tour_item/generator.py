import random
from dataclasses import dataclass
from datetime import date, datetime

from data_synthesization.feature.tour_item.events_generation import generate_day_events
from data_synthesization.feature.tour_item.record_mapping import map_events_to_records_for_vehicle_tours
from data_synthesization.feature.tour_item.types import BinVisitEvent, VehicleEmptyingEvent
from data_synthesization.feature.tour_item.util import _group_tours_by_vehicle_and_day, _group_nfc_mappings_by_bin, \
    _group_activities_by_bin, _group_events_by_vehicle, _active_bins_for_day
from data_synthesization.feature.tour_item.fill_level.latent_fill_level_simulator import LatentFillLevelSimulator
from data_synthesization.shared.config.config_model.app_config import AppConfig
from data_synthesization.shared.config.config_model.schedule_config import ServiceSchedule
from data_synthesization.shared.domain.models import (
    BinActivityRecord,
    BinRecord,
    BinVisitRecord,
    NfcTagMappingRecord,
    TourRecord,
    VehicleEmptyingRecord,
)
from data_synthesization.shared.utils.generation_iterator import iterator_over_entire_generation_days


@dataclass(frozen=True)
class TourItemGenerationStats:
    bin_visit_records: int
    vehicle_emptying_records: int


@dataclass(frozen=True)
class TourItemGenerationResult:
    bin_visit_records: list[BinVisitRecord]
    vehicle_emptying_records: list[VehicleEmptyingRecord]
    last_vehicle_emptying_per_tour: list[tuple[int, datetime]]
    stats: TourItemGenerationStats

"""
first generate events for a day => then map/reduce to database records
"""
def generate_tour_item_records(
        *,
        config: AppConfig,
        service_schedule: ServiceSchedule,
        bins_by_area_config: dict[str, list[int]],
        bins: list[BinRecord],
        bin_activities: list[BinActivityRecord],
        tours: list[TourRecord],
        nfc_tag_mappings: list[NfcTagMappingRecord],
        rng: random.Random,
        latent_filllevel_simulator: LatentFillLevelSimulator,
) -> TourItemGenerationResult:
    tours_by_vehicle_day = _group_tours_by_vehicle_and_day(tours)
    nfc_mappings_by_bin = _group_nfc_mappings_by_bin(nfc_tag_mappings)
    activities_by_bin = _group_activities_by_bin(bin_activities)
    bins_by_id = {_bin.id: _bin for _bin in bins}

    bin_visit_records: list[BinVisitRecord] = []
    vehicle_emptying_records: list[VehicleEmptyingRecord] = []
    last_vehicle_emptying_per_tour: list[tuple[int, datetime]] = []

    for day in iterator_over_entire_generation_days(config):
        day_events = _generate_day_events(
            day=day,
            service_schedule=service_schedule,
            bins_by_area_config=bins_by_area_config,
            bins_by_id=bins_by_id,
            activities_by_bin=activities_by_bin,
            vehicle_emptying_coords=config.tour_item_generation.vehicle_emptying_coords,
            empty_after_volume=config.tour_item_generation.empty_after_volume,
            latent_filllevel_simulator=latent_filllevel_simulator,
            average_speed_meters_per_second=config.tour_and_nfc_mapping.average_speed_meters_per_second,
            road_network_detour_factor=config.tour_and_nfc_mapping.road_network_detour_factor,
            seconds_per_bin_visit=config.tour_and_nfc_mapping.seconds_per_bin_visit,
            seconds_per_vehicle_emptying=config.tour_and_nfc_mapping.seconds_per_vehicle_emptying,
        )

        day_bin_visits, day_vehicle_emptyings, last_vehicle_emptying_per_tour_per_day = _generate_records_for_day(
            day=day,
            events=day_events,
            tours_by_vehicle_day=tours_by_vehicle_day,
            nfc_mappings_by_bin=nfc_mappings_by_bin,
            rng=rng,
        )
        bin_visit_records.extend(day_bin_visits)
        vehicle_emptying_records.extend(day_vehicle_emptyings)
        last_vehicle_emptying_per_tour.extend(
            [(tour_id, last_emptying) for tour_id, last_emptying in last_vehicle_emptying_per_tour_per_day.items()]
        )

    return TourItemGenerationResult(
        bin_visit_records=bin_visit_records,
        vehicle_emptying_records=vehicle_emptying_records,
        last_vehicle_emptying_per_tour=last_vehicle_emptying_per_tour,
        stats=TourItemGenerationStats(
            bin_visit_records=len(bin_visit_records),
            vehicle_emptying_records=len(vehicle_emptying_records),
        ),
    )


def _generate_day_events(
        day: date,
        service_schedule: ServiceSchedule,
        bins_by_area_config: dict[str, list[int]],
        bins_by_id: dict[int, BinRecord],
        activities_by_bin: dict[int, list[tuple[datetime, bool]]],
        vehicle_emptying_coords: tuple[float, float],
        empty_after_volume: int,
        latent_filllevel_simulator: LatentFillLevelSimulator,
        average_speed_meters_per_second: float,
        road_network_detour_factor: float,
        seconds_per_bin_visit: int,
        seconds_per_vehicle_emptying: int,
) -> list[BinVisitEvent | VehicleEmptyingEvent]:
    active_bins_by_id = _active_bins_for_day(
        day=day,
        bins_by_id=bins_by_id,
        activities_by_bin=activities_by_bin,
    )
    return generate_day_events(
        day=day,
        vehicles_schedules=service_schedule.vehicles,
        seasons=service_schedule.seasons,
        bins_by_area=bins_by_area_config,
        bins=active_bins_by_id,
        vehicle_emptying_coords=vehicle_emptying_coords,
        empty_after_volume=empty_after_volume,
        latent_fill_level_simulator=latent_filllevel_simulator,
        average_speed_meters_per_second=average_speed_meters_per_second,
        road_network_detour_factor=road_network_detour_factor,
        seconds_per_bin_visit=seconds_per_bin_visit,
        seconds_per_vehicle_emptying=seconds_per_vehicle_emptying,
    )


def _generate_records_for_day(
        day: date,
        events: list[BinVisitEvent | VehicleEmptyingEvent],
        tours_by_vehicle_day: dict[tuple[int, date], list[TourRecord]],
        nfc_mappings_by_bin: dict[int, list[NfcTagMappingRecord]],
        rng: random.Random,
) -> tuple[list[BinVisitRecord], list[VehicleEmptyingRecord], dict[int, datetime]]:
    day_bin_visits: list[BinVisitRecord] = []
    day_vehicle_emptyings: list[VehicleEmptyingRecord] = []

    last_vehicle_emptying_per_tour: dict[int, datetime] = {}

    for vehicle_number, vehicle_events in _group_events_by_vehicle(events).items():
        vehicle_tours = tours_by_vehicle_day.get((vehicle_number, day), [])

        bin_visits, vehicle_emptyings, last_vehicle_emptying_per_tour_per_vehicle = map_events_to_records_for_vehicle_tours(
            vehicle_events=vehicle_events,
            vehicle_tours=vehicle_tours,
            mappings_by_bin=nfc_mappings_by_bin,
            rng=rng,
        )
        day_bin_visits.extend(bin_visits)
        day_vehicle_emptyings.extend(vehicle_emptyings)

        last_vehicle_emptying_per_tour.update(last_vehicle_emptying_per_tour_per_vehicle)

    return day_bin_visits, day_vehicle_emptyings, last_vehicle_emptying_per_tour
