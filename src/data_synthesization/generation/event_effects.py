from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import json
from random import Random

from data_synthesization.config.config_model.latent_filllevel_config import EventEffectsConfig

@dataclass(frozen=True)
class EventPeriod:
    start: date
    end: date
    expected_people_per_day: int


@dataclass(frozen=True)
class EventDefinition:
    event_key: str
    name: str
    periods: list[EventPeriod]
    affected_neighbourhoods: list[str]


@dataclass(frozen=True)
class ActiveEventForDay:
    event_key: str
    name: str
    area_code: str
    expected_people_per_day: int

def load_events(
    path: str | Path,
    known_areas: set[str],
    bins_by_area: dict[str, list[int]] | None = None,
) -> list[EventDefinition]:
    source_path = Path(path)
    raw_events = json.loads(source_path.read_text(encoding="utf-8"))

    events: list[EventDefinition] = []
    unknown_areas = 0
    active_event_days = 0
    for raw_event in raw_events:
        raw_areas = raw_event.get("AffectedNeighbourhoods", [])
        normalized_areas = [str(value) for value in raw_areas]
        for area in normalized_areas:
            if area not in known_areas:
                unknown_areas += 1

        periods: list[EventPeriod] = []
        for period in raw_event.get("Periods", []):
            start = date.fromisoformat(str(period["Start"]))
            end = date.fromisoformat(str(period["End"]))
            expected_people = period.get("ExpectedPeoplePerDay")
            periods.append(
                EventPeriod(
                    start=start,
                    end=end,
                    expected_people_per_day=expected_people,
                )
            )
            active_event_days += (end - start).days + 1

        event_definition = EventDefinition(
            event_key=str(raw_event.get("EventKey")),
            name=str(raw_event.get("Name")),
            periods=periods,
            affected_neighbourhoods=normalized_areas,
        )
        events.append(event_definition)

        if bins_by_area is not None:
            affected_bin_ids: set[int] = set()
            for area_code in event_definition.affected_neighbourhoods:
                affected_bin_ids.update(bins_by_area.get(area_code, []))
    if unknown_areas:
        print(f"Unknown affected area references: {unknown_areas}")
    return events

"""
index structure:
- key: day
- value: dict[area_code, list[ActiveEventForDay]]
"""
def build_active_event_index(events: list[EventDefinition]) -> dict[date, dict[str, list[ActiveEventForDay]]]:
    index: dict[date, dict[str, list[ActiveEventForDay]]] = {}

    for event in events:
        for period in event.periods:
            current_day = period.start
            while current_day <= period.end:
                areas_for_day = index.setdefault(current_day, {})
                for area_code in event.affected_neighbourhoods:
                    areas_for_day.setdefault(area_code, []).append(
                        ActiveEventForDay(
                            event_key=event.event_key,
                            name=event.name,
                            area_code=area_code,
                            expected_people_per_day=period.expected_people_per_day,
                        )
                    )
                current_day += timedelta(days=1)

    return index


def get_active_events_for_area_and_date(
    index: dict[date, dict[str, list[ActiveEventForDay]]],
    area: str,
    current_day: date,
) -> list[ActiveEventForDay]:
    return index.get(current_day, {}).get(area, [])

"""
Calculate the combined multiplier for the given active events.
"""
def compute_event_multiplier(
    active_events: list[ActiveEventForDay],
    config: EventEffectsConfig,
    rng: Random,
) -> float:
    if not config.enabled or not active_events:
        return 1.0

    combined_multiplier = 1.0

    for event in active_events:
        people_factor = 0.0
        for bucket in config.people_factor_buckets:
            if bucket.min_people <= event.expected_people_per_day <= bucket.max_people:
                people_factor = bucket.factor
                break

        random_factor = rng.uniform(config.random_multiplier_min, config.random_multiplier_max)
        event_multiplier = 1.0 + (people_factor * config.area_weight_default * random_factor)
        combined_multiplier *= event_multiplier

    return combined_multiplier
