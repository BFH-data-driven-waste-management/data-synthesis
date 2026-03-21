import random
from datetime import datetime, timedelta, time, timezone

from data_synthesization.shared.config.config_model.simulation_config import TourTimingConfig
from data_synthesization.shared.domain.models import TourRecord

# on each vehicle and day, two tours are generated, which represent two mobile phones resp. two operators
def generate_tours_for_vehicle_and_day(day_start: datetime, records: list[TourRecord], rng: random.Random,
                                       tour_timing: TourTimingConfig, vehicle_id: int):
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

    first_virtual_end = _build_tour_end(first_virtual_start, tour_timing, rng)
    second_virtual_end = _build_tour_end(second_virtual_start, tour_timing, rng)

    records.append(
        TourRecord(
            id=None,
            vehicle_id=vehicle_id,
            started_at=first_virtual_start,
            ended_at=first_virtual_end
        )
    )
    records.append(
        TourRecord(
            id=None,
            vehicle_id=vehicle_id,
            started_at=second_virtual_start,
            ended_at=second_virtual_end,
        )
    )

"""
sets the tour end time to midnight of the next day for a given chance.
other tour's ended_at will be set later.
"""
def _build_tour_end(started_at: datetime, tour_timing: TourTimingConfig, rng: random.Random) -> datetime | None:
    if rng.random() < tour_timing.next_day_midnight_ending_share:
        next_day = started_at.date() + timedelta(days=1)
        microsecond = rng.randint(0, 9999)
        return datetime.combine(next_day, time(0, 0, 0, microsecond), tzinfo=timezone.utc)
    else:
        return None
