from dataclasses import dataclass
from datetime import date
from datetime import datetime, time, timedelta, timezone
import random

from data_synthesization.config.config_model.app_config import AppConfig
from data_synthesization.domain.models import TourRecord
from data_synthesization.utils.time import to_utc

REFERENCE_START_TIME_UTC = time(hour=3, minute=30)
# TODO: find empirical value, and think about auto ending
DEFAULT_TOUR_DURATION_MINUTES = 180


@dataclass(frozen=True)
class TourGenerationStats:
    generated_rows: int
    generated_days: int


@dataclass(frozen=True)
class TourGenerationResult:
    records: list[TourRecord]
    stats: TourGenerationStats


def _iter_generation_days(config: AppConfig) -> list[date]:
    simulation_start = to_utc(config.simulation.start_date).date()
    generation_end = config.simulation.tour_generation_end_date

    if generation_end < simulation_start:
        return []

    day_count = (generation_end - simulation_start).days + 1
    return [simulation_start + timedelta(days=offset) for offset in range(day_count)]


def _build_base_start(day: date) -> datetime:
    return datetime.combine(day, REFERENCE_START_TIME_UTC, tzinfo=timezone.utc)


def generate_tours(vehicle_ids: list[int], config: AppConfig) -> TourGenerationResult:
    if len(vehicle_ids) < 2:
        raise ValueError("Error in vehicle fetching")

    rng = random.Random(config.simulation.seed)
    records: list[TourRecord] = []
    generation_days = _iter_generation_days(config)

    for day in generation_days:
        day_start = _build_base_start(day)
        selected_vehicle_ids = sorted(vehicle_ids)[:2]

        for vehicle_id in selected_vehicle_ids:
            real_tour_start = day_start + timedelta(minutes=rng.randint(-10, 10))
            second_phone_offset = rng.randint(-120, 120)

            first_virtual_start = real_tour_start
            second_virtual_start = real_tour_start + timedelta(seconds=second_phone_offset)

            records.append(
                TourRecord(
                    vehicle_id=vehicle_id,
                    started_at=first_virtual_start,
                    ended_at=first_virtual_start + timedelta(minutes=DEFAULT_TOUR_DURATION_MINUTES),
                )
            )
            records.append(
                TourRecord(
                    vehicle_id=vehicle_id,
                    started_at=second_virtual_start,
                    ended_at=second_virtual_start + timedelta(minutes=DEFAULT_TOUR_DURATION_MINUTES),
                )
            )

    return TourGenerationResult(
        records=records,
        stats=TourGenerationStats(generated_rows=len(records), generated_days=len(generation_days)),
    )
