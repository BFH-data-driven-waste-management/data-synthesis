from collections import defaultdict
from datetime import datetime, timedelta

from data_synthesization.shared.domain.models import BinRecord, NfcTagMappingRecord
from data_synthesization.feature.nfc_tag_mapping.generator import INITIAL_MAPPING_TIMESTAMP
from data_synthesization.shared.utils.time import to_utc


def validate_nfc_tag_mapping(
        records: list[NfcTagMappingRecord],
        bins: list[BinRecord],
        simulation_end: datetime,
        min_mapping_lifetime_days: int,
) -> None:
    expected_bin_ids = {bin_record.id for bin_record in bins}
    by_bin: dict[int, list[NfcTagMappingRecord]] = defaultdict(list)
    seen_uids: set[str] = set()

    # Check references, uniqueness of UIDs
    for record in records:
        if record.bin_id not in expected_bin_ids:
            raise ValueError(f"nfc_tag_mapping references unknown bin_id={record.bin_id}")
        if record.uid in seen_uids:
            raise ValueError(f"Duplicate UID detected: {record.uid}")
        seen_uids.add(record.uid)
        by_bin[record.bin_id].append(record)

    sim_end = to_utc(simulation_end)
    min_gap = timedelta(days=min_mapping_lifetime_days)

    for bin_id in sorted(by_bin.keys()):
        mappings = sorted(by_bin[bin_id], key=lambda row: to_utc(row.mapped_at))

        # loop over all mappings by bin
        for index, mapping in enumerate(mappings):
            mapped_at = to_utc(mapping.mapped_at)
            unmapped_at = to_utc(mapping.unmapped_at) if mapping.unmapped_at else None

            _check_mapping_per_bin(bin_id, index, mapped_at, mapping, mappings, min_gap, sim_end, unmapped_at)


def _check_mapping_per_bin(bin_id: int, index: int, mapped_at: datetime, mapping: NfcTagMappingRecord,
                           mappings: list[NfcTagMappingRecord], min_gap: timedelta, sim_end: datetime,
                           unmapped_at: datetime | None):
    if mapped_at < INITIAL_MAPPING_TIMESTAMP or mapped_at > sim_end:
        raise ValueError(f"Bin {bin_id} has mapping outside simulation range")

    if index < len(mappings) - 1:
        next_mapping = mappings[index + 1]
        next_mapped_at = to_utc(next_mapping.mapped_at)

        if unmapped_at is None:
            raise ValueError(f"Bin {bin_id} has non-final mapping with NULL unmapped_at")
        if unmapped_at != next_mapped_at:
            raise ValueError(f"Bin {bin_id} mapping continuity broken")
        if (next_mapped_at - mapped_at) < min_gap:
            raise ValueError(f"Bin {bin_id} mappings violate minimum 7-day spacing")
    else:
        if unmapped_at is not None:
            raise ValueError(f"Bin {bin_id} final mapping must remain active")

    if any(char not in "0123456789ABCDEF" for char in mapping.uid):
        raise ValueError(f"Bin {bin_id} has non-hex UID: {mapping.uid}")
