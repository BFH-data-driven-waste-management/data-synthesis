from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import random

from data_synthesization.config.config_model.app_config import AppConfig
from data_synthesization.domain.models import BinActivityRecord, BinRecord
from data_synthesization.utils.time import to_utc

"""
The following timestamps are used to determine the initial state of the bins.
Bins with created_at=POC_CREATED_AT are active from the start. They were the bins used in the PoC (Project2).
Bins with created_at=LATE_IMPORT_CREATED_AT are inactive from the start. They were imported after the PoC during the 
thesis work.
"""
POC_CREATED_AT = datetime(2024, 12, 31, 2, 0, 0, tzinfo=timezone.utc)
LATE_IMPORT_CREATED_AT = datetime(2025, 1, 1, 2, 0, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class GenerationStats:
    total_bins: int
    poc_bins: int
    late_import_bins: int
    generated_rows: int
    bins_with_no_extra_switch: int
    bins_with_extra_switch: int


@dataclass(frozen=True)
class GenerationResult:
    records: list[BinActivityRecord]
    stats: GenerationStats

# determine the number of days in the episode based on the episode duration config
def _draw_episode_days(config: AppConfig, rng: random.Random) -> int:
    e = config.bin_activity.episode_duration
    if rng.random() < e.short_share:
        return rng.randint(e.short_days_min, e.short_days_max)
    return rng.randint(e.long_days_min, e.long_days_max)

# calculate the probability of a transition from (in)active to (in)active based on the monthly probability
# and the number of days in the episode
def _episode_transition_probability(monthly_probability: float, episode_days: int) -> float:
    if monthly_probability <= 0:
        return 0.0
    if monthly_probability >= 1:
        return 1.0
    return 1 - math.pow(1 - monthly_probability, episode_days / 30.0)


def generate_bin_activity(bins: list[BinRecord], config: AppConfig) -> GenerationResult:
    rng = random.Random(config.simulation.seed)
    start = to_utc(config.simulation.start_date)
    end = to_utc(config.simulation.end_date)

    records: list[BinActivityRecord] = []
    poc_bins = 0
    late_bins = 0
    bins_with_extra_switch = 0

    for bin_record in bins:

        # Create initial bin activity which represents the state of the bin at the start of the simulation.
        created_at = to_utc(bin_record.created_at)
        if created_at == POC_CREATED_AT:
            current_active = config.bin_activity.initial.poc_bins_active
            poc_bins += 1
        elif created_at == LATE_IMPORT_CREATED_AT:
            current_active = config.bin_activity.initial.late_import_bins_active
            late_bins += 1
        else:
            raise ValueError(
                f"Unsupported created_at for bin_id={bin_record.id}: {created_at.isoformat()}"
            )

        records.append(
            BinActivityRecord(
                bin_id=bin_record.id,
                active=current_active,
                activity_timestamp=start,
            )
        )

        # Generate bin activities to simulate deactivations and activations of bins over time.
        current_timestamp = start
        extra_switches = 0

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
                extra_switches += 1
                records.append(
                    BinActivityRecord(
                        bin_id=bin_record.id,
                        active=current_active,
                        activity_timestamp=episode_end,
                    )
                )

            current_timestamp = episode_end

        if extra_switches > 0:
            bins_with_extra_switch += 1

    stats = GenerationStats(
        total_bins=len(bins),
        poc_bins=poc_bins,
        late_import_bins=late_bins,
        generated_rows=len(records),
        bins_with_no_extra_switch=len(bins) - bins_with_extra_switch,
        bins_with_extra_switch=bins_with_extra_switch,
    )
    return GenerationResult(records=records, stats=stats)
