from datetime import datetime

from data_synthesization.shared.domain.models import TourRecord
from data_synthesization.shared.utils.time import to_utc


def validate_tours(
    records: list[TourRecord],
    simulation_start: datetime,
    generation_end_date: datetime,
) -> None:
    start_utc = to_utc(simulation_start)
    end_utc = to_utc(generation_end_date)

    for record in records:
        started_at = to_utc(record.started_at)

        if started_at < start_utc or started_at > end_utc:
            raise ValueError(
                f"Tour started_at out of configured generation range: {started_at.isoformat()}"
            )

        # expected tour start window around 03:30 UTC
        if started_at.hour not in {3}:
            raise ValueError(
                f"Tour started_at outside 03:00-03:59 UTC window: {started_at.isoformat()}"
            )
