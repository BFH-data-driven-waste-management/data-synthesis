from dataclasses import dataclass
from datetime import date
from datetime import datetime, time, timedelta, timezone
import random

from data_synthesization.config.config_model.app_config import AppConfig
from data_synthesization.config.config_model.simulation_config import TourTimingConfig
from data_synthesization.domain.models import TourRecord
from data_synthesization.utils.time import to_utc


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


def _build_base_start(day: date, tour_timing: TourTimingConfig) -> datetime:
    return datetime.combine(day, tour_timing.reference_start_time_utc, tzinfo=timezone.utc)


def _build_tour_end(started_at: datetime, tour_timing: TourTimingConfig, rng: random.Random) -> datetime:
    # 1 of 10 tims the crew forgets to end the tour manually
    if rng.random() < tour_timing.next_day_midnight_ending_share:
        next_day = started_at.date() + timedelta(days=1)
        microsecond = rng.randint(0, 9999)
        return datetime.combine(next_day, time(0, 0, 0, microsecond), tzinfo=timezone.utc)

    minutes_offset = rng.randint(
        -tour_timing.reference_end_time_spread_minutes,
        tour_timing.reference_end_time_spread_minutes,
    )
    return datetime.combine(started_at.date(), tour_timing.reference_end_time_utc, tzinfo=timezone.utc) + timedelta(
        minutes=minutes_offset
    )


def generate_tours(vehicle_ids: list[int], config: AppConfig) -> TourGenerationResult:
    if len(vehicle_ids) < 2:
        raise ValueError("Error in vehicle fetching")

    rng = random.Random(config.simulation.seed)
    tour_timing = config.simulation.tour_timing
    records: list[TourRecord] = []
    generation_days = _iter_generation_days(config)

    for day in generation_days:
        day_start = _build_base_start(day, tour_timing)
        selected_vehicle_ids = sorted(vehicle_ids)[:2]

        for vehicle_id in selected_vehicle_ids:
            real_tour_start = day_start + timedelta(
                minutes=rng.randint(
                    tour_timing.start_time_delta_min_minutes,
                    tour_timing.start_time_delta_max_minutes,
                )
            )
            second_phone_offset = rng.randint(
                tour_timing.second_phone_offset_min_seconds,
                tour_timing.second_phone_offset_max_seconds,
            )

            first_virtual_start = real_tour_start
            second_virtual_start = real_tour_start + timedelta(seconds=second_phone_offset)

            records.append(
                TourRecord(
                    vehicle_id=vehicle_id,
                    started_at=first_virtual_start,
                    ended_at=_build_tour_end(first_virtual_start, tour_timing, rng),
                )
            )
            records.append(
                TourRecord(
                    vehicle_id=vehicle_id,
                    started_at=second_virtual_start,
                    ended_at=_build_tour_end(second_virtual_start, tour_timing, rng),
                )
            )

    return TourGenerationResult(
        records=records,
        stats=TourGenerationStats(generated_rows=len(records), generated_days=len(generation_days)),
    )
