from datetime import datetime

from data_synthesization.shared.domain.models import NfcTagMappingRecord


def find_mapping_for_bin_visit_day(
        exact_time: datetime,
        bin_id: int,
        mappings_by_bin: dict[int, list[NfcTagMappingRecord]],
) -> int | None:
    for mapping in mappings_by_bin.get(bin_id, []):
        if mapping.mapped_at <= exact_time and (mapping.unmapped_at is None or exact_time < mapping.unmapped_at):
            return mapping.id
    return None
