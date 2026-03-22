from datetime import date, timedelta
from random import Random

from data_synthesization.feature.tour_item.context.models import EventDefinition, ActiveEventForDay
from data_synthesization.shared.config.config_model.latent_filllevel_config import EventEffectsConfig

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
