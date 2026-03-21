from dataclasses import dataclass
from datetime import date
from datetime import datetime, timezone
import random

from data_synthesization.feature.tour.build_virtual_tour_records import generate_tours_for_vehicle_and_day
from data_synthesization.shared.config.config_model.app_config import AppConfig
from data_synthesization.shared.config.config_model.simulation_config import TourTimingConfig
from data_synthesization.shared.domain.models import TourRecord
from data_synthesization.shared.utils.generation_iterator import iterator_over_entire_generation_days


@dataclass(frozen=True)
class TourGenerationStats:
    generated_rows: int
    generated_days: int


@dataclass(frozen=True)
class TourGenerationResult:
    records: list[TourRecord]
    stats: TourGenerationStats


def generate_tours(vehicle_ids: list[int], config: AppConfig) -> TourGenerationResult:
    rng = random.Random(config.simulation.seed)
    tour_timing = config.simulation.tour_timing

    records: list[TourRecord] = []
    generation_days_iter = iterator_over_entire_generation_days(config)
    selected_vehicle_ids = sorted(vehicle_ids)[:2]

    for day in generation_days_iter:
        day_start = _build_base_start(day, tour_timing)
        for vehicle_id in selected_vehicle_ids:
            generate_tours_for_vehicle_and_day(day_start, records, rng, tour_timing, vehicle_id)

    return TourGenerationResult(
        records=records,
        stats=TourGenerationStats(generated_rows=len(records), generated_days=len(generation_days_iter)),
    )


def _build_base_start(day: date, tour_timing: TourTimingConfig) -> datetime:
    return datetime.combine(day, tour_timing.reference_start_time_utc, tzinfo=timezone.utc)