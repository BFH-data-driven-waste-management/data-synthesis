from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import random

from data_synthesization.feature.nfc_tag_mapping.build_nfc_uid import build_uid
from data_synthesization.feature.nfc_tag_mapping.draw_timestamps import draw_nfc_mapping_timestamps
from data_synthesization.shared.config.config_model.app_config import AppConfig
from data_synthesization.shared.domain.models import BinActivityRecord, BinRecord, NfcTagMappingRecord
from data_synthesization.shared.utils.time import to_utc

INITIAL_MAPPING_TIMESTAMP = datetime(2025, 1, 1, 2, 30, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class NfcTagMappingGenerationStats:
    total_bins: int
    generated_rows: int


@dataclass(frozen=True)
class NfcTagMappingGenerationResult:
    records: list[NfcTagMappingRecord]
    stats: NfcTagMappingGenerationStats


def generate_nfc_tag_mapping_history(
        bins: list[BinRecord],
        activities: list[BinActivityRecord],
        config: AppConfig,
) -> NfcTagMappingGenerationResult:
    rng = random.Random(config.simulation.seed)
    simulation_end = to_utc(config.simulation.end_date)
    min_mapping_lifetime_days = config.nfc_tag_mapping.min_mapping_lifetime_days

    total_bins = len(bins)
    replacement_counts_by_bin = _create_and_shuffle_replacement_counts(config, total_bins, rng)

    activity_by_bin: dict[int, list[BinActivityRecord]] = defaultdict(list)
    for activity in activities:
        activity_by_bin[activity.bin_id].append(activity)

    records: list[NfcTagMappingRecord] = []

    for bin_record, target_replacements in zip(bins, replacement_counts_by_bin):
        mapping_timestamps = draw_nfc_mapping_timestamps(min_mapping_lifetime_days, rng, simulation_end,
                                                         target_replacements, INITIAL_MAPPING_TIMESTAMP)

        valid_mapping_timestamps = _drop_timestamps_if_bin_is_inactive_at(activity_by_bin, bin_record,
                                                                          mapping_timestamps)

        for sequence_index, mapped_at in enumerate(valid_mapping_timestamps):
            unmapped_at = (
                valid_mapping_timestamps[sequence_index + 1]
                if sequence_index < len(valid_mapping_timestamps) - 1
                else None
            )

            records.append(
                NfcTagMappingRecord(
                    id=None,
                    uid=build_uid(bin_record.id, sequence_index),
                    bin_id=bin_record.id,
                    mapped_at=mapped_at,
                    unmapped_at=unmapped_at,
                )
            )

    stats = NfcTagMappingGenerationStats(
        total_bins=len(bins),
        generated_rows=len(records)
    )

    return NfcTagMappingGenerationResult(records=records, stats=stats)


def _drop_timestamps_if_bin_is_inactive_at(activity_by_bin: dict[int, list[BinActivityRecord]], bin_record: BinRecord,
                                           mapping_timestamps: list[datetime]) -> list[datetime]:
    valid_mapping_timestamps = [
        mapped_at
        for mapped_at in mapping_timestamps
        if _is_bin_active_at(bin_record.id, to_utc(mapped_at), activity_by_bin)
    ]
    return valid_mapping_timestamps


def _create_and_shuffle_replacement_counts(config: AppConfig, total_bins: int, _rng: random.Random) -> list[int]:
    no_replacement_share = config.nfc_tag_mapping.replacement_distribution.no_replacement_share
    one_replacement_share = config.nfc_tag_mapping.replacement_distribution.one_replacement_share

    no_replacement_count = int(round(total_bins * no_replacement_share))
    one_replacement_count = int(round(total_bins * one_replacement_share))
    two_replacement_count = total_bins - no_replacement_count - one_replacement_count

    replacement_counts_by_bin = ([0] * no_replacement_count + [1] * one_replacement_count + [2] * two_replacement_count)
    _rng.shuffle(replacement_counts_by_bin)
    return replacement_counts_by_bin


def _is_bin_active_at(
        bin_id: int,
        timestamp: datetime,
        activity_by_bin: dict[int, list[BinActivityRecord]],
) -> bool:
    activities = activity_by_bin.get(bin_id, [])
    last_active_state = False

    for activity in activities:
        if to_utc(activity.activity_timestamp) > timestamp:
            break
        last_active_state = activity.active

    return bool(last_active_state)
