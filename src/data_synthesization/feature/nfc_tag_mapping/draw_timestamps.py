import random
from datetime import datetime, timedelta

def draw_nfc_mapping_timestamps(min_mapping_lifetime_days: int, rng: random.Random, simulation_end: datetime,
                                target_replacements: int, initial_mapping_timestamp: datetime) -> list[datetime]:
    mapping_timestamps = [initial_mapping_timestamp]
    mapping_timestamps.extend(
        _draw_replacement_timestamps(
            rng=rng,
            start=initial_mapping_timestamp,
            end=simulation_end,
            replacement_count=target_replacements,
            min_mapping_lifetime_days=min_mapping_lifetime_days,
        )
    )
    return mapping_timestamps

# idea for the random sampling:
# https://stackoverflow.com/questions/51918580/python-random-list-of-numbers-in-a-range-keeping-with-a-minimum-distance
def _draw_replacement_timestamps(
        rng: random.Random,
        start: datetime,
        end: datetime,
        replacement_count: int,
        min_mapping_lifetime_days: int,
) -> list[datetime]:
    if replacement_count <= 0:
        return []

    min_lifetime_seconds = min_mapping_lifetime_days * 24 * 3600
    total_span_seconds = int((end - start).total_seconds())
    compressed_range_size = total_span_seconds - replacement_count * min_lifetime_seconds

    offsets = [
        i * min_lifetime_seconds + x
        for i, x in enumerate(
            sorted(rng.sample(range(compressed_range_size), replacement_count)),
            # because start timestamp is already a mapping record.
            start=1,
        )
    ]

    return [start + timedelta(seconds=offset) for offset in offsets]
