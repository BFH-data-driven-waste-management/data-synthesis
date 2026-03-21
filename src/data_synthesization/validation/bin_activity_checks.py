from collections import defaultdict
from datetime import datetime

from data_synthesization.shared.domain.models import BinActivityRecord, BinRecord
from data_synthesization.shared.utils.time import to_utc


def validate_bin_activity(
        records: list[BinActivityRecord],
        bins: list[BinRecord],
        simulation_start: datetime,
        simulation_end: datetime,
) -> None:
    start = to_utc(simulation_start)
    end = to_utc(simulation_end)

    activities_by_bin: dict[int, list[BinActivityRecord]] = defaultdict(list)
    for record in records:
        activities_by_bin[record.bin_id].append(record)

    # Check that all bins have activity records and no records exist for non-existent bins.
    expected_bin_ids = {b.id for b in bins}
    if set(activities_by_bin.keys()) != expected_bin_ids:
        missing = sorted(expected_bin_ids - set(activities_by_bin.keys()))
        extra = sorted(set(activities_by_bin.keys()) - expected_bin_ids)
        raise ValueError(f"Bin activity coverage mismatch. missing={missing} extra={extra}")

    # Check that all activity records are within the simulation range and strictly increasing.
    for bin_id in sorted(activities_by_bin.keys()):
        bin_records = sorted(activities_by_bin[bin_id], key=lambda item: item.activity_timestamp)

        if len(bin_records) < 1:
            raise ValueError(f"Bin {bin_id} has no activity records")

        if to_utc(bin_records[0].activity_timestamp) != start:
            raise ValueError(f"Bin {bin_id} first activity timestamp is not simulation start")

        for index, bin in enumerate(bin_records):
            activity_timestamp = to_utc(bin.activity_timestamp)
            if activity_timestamp < start or activity_timestamp > end:
                raise ValueError(f"Bin {bin_id} has activity outside simulation range: {activity_timestamp}")

            if index > 0:
                prev = bin_records[index - 1]
                prev_timestamp = to_utc(prev.activity_timestamp)
                if activity_timestamp <= prev_timestamp:
                    raise ValueError(f"Bin {bin_id} timestamps are not strictly increasing")
                if bin.active == prev.active:
                    raise ValueError(
                        f"Bin {bin_id} has repeated consecutive state {bin.active} at {activity_timestamp}"
                    )
