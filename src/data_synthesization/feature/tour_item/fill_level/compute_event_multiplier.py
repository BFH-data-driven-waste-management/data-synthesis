from random import Random

from data_synthesization.feature.tour_item.context.models import ActiveEventForDay
from data_synthesization.shared.config.config_model.latent_filllevel_config import EventEffectsConfig


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
