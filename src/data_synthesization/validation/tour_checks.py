from datetime import datetime
from zoneinfo import ZoneInfo

from data_synthesization.shared.domain.models import TourRecord
from data_synthesization.shared.utils.time import to_utc


def validate_tours(
    records: list[TourRecord],
    simulation_start: datetime,
    generation_end_date: datetime,
) -> None:
    start_utc = to_utc(simulation_start)
    zurich_start = datetime(start_utc.year, start_utc.month, start_utc.day, 1, 0, 0, tzinfo=ZoneInfo("Europe/Zurich"))
    end_utc = to_utc(generation_end_date)

    for record in records:
        started_at = record.started_at

        if started_at < zurich_start or started_at > end_utc:
            raise ValueError(
                f"Tour started_at out of configured generation range: {started_at.isoformat()}"
            )

        # expected tour start window around 03:30 UTC
        if started_at.hour not in {4}:
            raise ValueError(
                f"Tour started_at outside 04:00-04:59 UTC window: {started_at.isoformat()}"
            )
