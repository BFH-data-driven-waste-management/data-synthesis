from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import random

from data_synthesization.config.config_model.app_config import AppConfig
from data_synthesization.domain.models import BinActivityRecord, BinRecord, NfcTagMappingRecord
from data_synthesization.utils.time import to_utc

INITIAL_MAPPING_TIMESTAMP = datetime(2025, 1, 1, 2, 30, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class NfcTagMappingGenerationStats:
    total_bins: int
    generated_rows: int
    bins_with_0_replacements: int
    bins_with_1_replacement: int
    bins_with_2_replacements: int


@dataclass(frozen=True)
class NfcTagMappingGenerationResult:
    records: list[NfcTagMappingRecord]
    stats: NfcTagMappingGenerationStats


def _build_uid(bin_id: int, sequence_index: int) -> str:
    payload = f"bin:{bin_id}|mapping_sequence:{sequence_index}"
    hash = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
    return f"0{hash[-13:]}"


"""
idea for the random sampling:
https://stackoverflow.com/questions/51918580/python-random-list-of-numbers-in-a-range-keeping-with-a-minimum-distance
"""
def _draw_replacement_timestamps(
        rng: random.Random,
        start: datetime,
        end: datetime,
        replacement_count: int,
        min_mapping_lifetime_days: int,
) -> list[datetime]:
    if replacement_count <= 0:
        return []

    min_gap_seconds = min_mapping_lifetime_days * 24 * 3600
    total_span_seconds = int((end - start).total_seconds())
    compressed_range_size = total_span_seconds - replacement_count * min_gap_seconds

    offsets = [
        i * min_gap_seconds + x
        for i, x in enumerate(
            sorted(rng.sample(range(compressed_range_size), replacement_count)),
            # because start timestamp is already a mapping record.
            start=1,
        )
    ]

    return [start + timedelta(seconds=offset) for offset in offsets]


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


def generate_nfc_tag_mapping_history(
        bins: list[BinRecord],
        activities: list[BinActivityRecord],
        config: AppConfig,
) -> NfcTagMappingGenerationResult:
    rng = random.Random(config.simulation.seed)
    simulation_end = to_utc(config.simulation.end_date)

    min_mapping_lifetime_days = config.nfc_tag_mapping.min_mapping_lifetime_days
    no_replacement_share = config.nfc_tag_mapping.replacement_distribution.no_replacement_share
    one_replacement_share = config.nfc_tag_mapping.replacement_distribution.one_replacement_share

    total_bins = len(bins)
    no_replacement_count = int(round(total_bins * no_replacement_share))
    one_replacement_count = int(round(total_bins * one_replacement_share))
    two_replacement_count = total_bins - no_replacement_count - one_replacement_count

    replacement_targets = ([0] * no_replacement_count + [1] * one_replacement_count + [2] * two_replacement_count)
    rng.shuffle(replacement_targets)

    activity_by_bin: dict[int, list[BinActivityRecord]] = defaultdict(list)
    for activity in activities:
        activity_by_bin[activity.bin_id].append(activity)

    records: list[NfcTagMappingRecord] = []

    for bin_record, target_replacements in zip(bins, replacement_targets):
        mapping_timestamps = [INITIAL_MAPPING_TIMESTAMP]
        mapping_timestamps.extend(
            _draw_replacement_timestamps(
                rng=rng,
                start=INITIAL_MAPPING_TIMESTAMP,
                end=simulation_end,
                replacement_count=target_replacements,
                min_mapping_lifetime_days=min_mapping_lifetime_days,
            )
        )

        # drop mapped_at timestamps for which the bin is inactive
        valid_mapping_timestamps = [
            mapped_at
            for mapped_at in mapping_timestamps
            if _is_bin_active_at(bin_record.id, to_utc(mapped_at), activity_by_bin)
        ]

        for sequence_index, mapped_at in enumerate(valid_mapping_timestamps):
            unmapped_at = (
                valid_mapping_timestamps[sequence_index + 1]
                if sequence_index < len(valid_mapping_timestamps) - 1
                else None
            )

            records.append(
                NfcTagMappingRecord(
                    uid=_build_uid(bin_record.id, sequence_index),
                    bin_id=bin_record.id,
                    mapped_at=mapped_at,
                    unmapped_at=unmapped_at,
                )
            )

    replacements_by_bin: dict[int, int] = defaultdict(int)
    for record in records:
        replacements_by_bin[record.bin_id] += 1

    bins_with_0_replacements = 0
    bins_with_1_replacement = 0
    bins_with_2_replacements = 0

    for bin_record in bins:
        replacement_count_for_bin = max(0, replacements_by_bin.get(bin_record.id, 0) - 1)
        if replacement_count_for_bin <= 0:
            bins_with_0_replacements += 1
        elif replacement_count_for_bin == 1:
            bins_with_1_replacement += 1
        else:
            bins_with_2_replacements += 1

    stats = NfcTagMappingGenerationStats(
        total_bins=len(bins),
        generated_rows=len(records),
        bins_with_0_replacements=bins_with_0_replacements,
        bins_with_1_replacement=bins_with_1_replacement,
        bins_with_2_replacements=bins_with_2_replacements,
    )

    return NfcTagMappingGenerationResult(records=records, stats=stats)
