from dataclasses import dataclass
from datetime import timedelta, datetime
import math
import random

from data_synthesization.shared.config.config_model.app_config import AppConfig
from data_synthesization.shared.domain.models import BinActivityRecord, BinRecord
from data_synthesization.feature.bin_activty.map_created_at_to_activity_state import is_created_at_date_initially_active
from data_synthesization.shared.utils.time import to_utc


@dataclass(frozen=True)
class BinActivityStats:
    total_bins: int
    generated_rows: int


@dataclass(frozen=True)
class GenerationResult:
    records: list[BinActivityRecord]
    stats: BinActivityStats


def generate_bin_activity_records(bins: list[BinRecord], config: AppConfig) -> GenerationResult:
    rng = random.Random(config.simulation.seed)
    start = to_utc(config.simulation.start_date)
    end = to_utc(config.simulation.end_date)

    records: list[BinActivityRecord] = []

    for bin_record in bins:
        _generate_bin_activity_records_for_bin(bin_record, config, start, end, records, rng)

    stats = BinActivityStats(
        total_bins=len(bins),
        generated_rows=len(records),
    )
    return GenerationResult(records=records, stats=stats)


def _generate_bin_activity_records_for_bin(bin_record: BinRecord, config: AppConfig, start: datetime, end: datetime,
                                           records: list[BinActivityRecord], rng: random.Random):
    current_active = is_created_at_date_initially_active(
        created_at=to_utc(bin_record.created_at),
        config=config
    )

    initial_bin_activity_record_of_bin = BinActivityRecord(
        bin_id=bin_record.id,
        active=current_active,
        activity_timestamp=start,
    )
    records.append(initial_bin_activity_record_of_bin)

    current_timestamp = start

    while True:
        episode_days = _draw_episode_days(config, rng)
        episode_end = current_timestamp + timedelta(days=episode_days)
        if episode_end > end:
            break

        monthly_probability = (
            config.bin_activity.transition_probability.active_to_inactive_monthly
            if current_active
            else config.bin_activity.transition_probability.inactive_to_active_monthly
        )
        switch_probability = _episode_transition_probability(monthly_probability, episode_days)

        if rng.random() < switch_probability:
            current_active = not current_active
            records.append(
                BinActivityRecord(
                    bin_id=bin_record.id,
                    active=current_active,
                    activity_timestamp=episode_end.replace(hour=1, minute=0, second=0, microsecond=0),
                )
            )

        current_timestamp = episode_end


def _draw_episode_days(config: AppConfig, rng: random.Random) -> int:
    episode = config.bin_activity.episode_duration
    if rng.random() < episode.short_share:
        return rng.randint(episode.short_days_min, episode.short_days_max)
    return rng.randint(episode.long_days_min, episode.long_days_max)


def _episode_transition_probability(monthly_probability: float, episode_days: int) -> float:
    if monthly_probability <= 0:
        return 0.0
    if monthly_probability >= 1:
        return 1.0
    return 1 - math.pow(1 - monthly_probability, episode_days / 30.0)
