from pathlib import Path
from typing import Any

import yaml

from data_synthesization.config.config_model.latent_filllevel_config import (
    ActionProbabilityConfig,
    EventEffectsConfig,
    EventPeopleFactorBucketConfig,
    LatentFillLevelConfig,
    RatioRangeConfig,
    ThresholdsConfig,
)

def load_latent_filllevel_config(
    path: str | Path,
) -> LatentFillLevelConfig:
    config_path = Path(path)
    raw: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}

    config = raw.get("latent_filllevel", {})

    configured_rates = dict(config["zone_base_fill_rate_ratio_per_day"])
    configured_weekday_overrides = dict(config.get("zone_base_fill_rate_ratio_per_day_weekday_overrides", {}))
    event_effects_raw = dict(config.get("event_effects", {}))
    people_buckets_raw = list(event_effects_raw.get("people_factor_buckets", []))

    thresholds_raw = config["thresholds"]
    random_raw = config["random_daily_multiplier"]

    return LatentFillLevelConfig(
        thresholds=ThresholdsConfig(
            empty_or_almost_empty_max_ratio=float(thresholds_raw["empty_or_almost_empty_max_ratio"]),
            half_full_max_ratio=float(thresholds_raw["half_full_max_ratio"]),
            full_max_ratio=float(thresholds_raw["full_max_ratio"]),
        ),
        action_probabilities={
            key: ActionProbabilityConfig(emptied=float(value["emptied"]))
            for key, value in config["action_probabilities"].items()
        },
        seasonal_factors={key: float(value) for key, value in config["seasonal_factors"].items()},
        weekday_factors={key: float(value) for key, value in config["weekday_factors"].items()},
        random_daily_multiplier=RatioRangeConfig(
            min=float(random_raw["min"]),
            max=float(random_raw["max"]),
        ),
        zone_base_fill_rate_ratio_per_day={
            key: float(value)
            for key, value in configured_rates.items()
        },
        zone_base_fill_rate_ratio_per_day_weekday_overrides={
            area: {day: float(value) for day, value in weekday_overrides.items()}
            for area, weekday_overrides in configured_weekday_overrides.items()
        },
        event_effects=EventEffectsConfig(
            enabled=bool(event_effects_raw.get("enabled", True)),
            area_weight_default=float(event_effects_raw.get("area_weight_default", 1.0)),
            random_multiplier_min=float(event_effects_raw.get("random_multiplier_min", 0.9)),
            random_multiplier_max=float(event_effects_raw.get("random_multiplier_max", 1.1)),
            people_factor_buckets=[
                EventPeopleFactorBucketConfig(
                    min_people=int(bucket["min_people"]),
                    max_people=int(bucket["max_people"]),
                    factor=float(bucket["factor"]),
                )
                for bucket in people_buckets_raw
            ] or [
                EventPeopleFactorBucketConfig(min_people=0, max_people=999, factor=0.02),
                EventPeopleFactorBucketConfig(min_people=1000, max_people=2999, factor=0.04),
                EventPeopleFactorBucketConfig(min_people=3000, max_people=6999, factor=0.07),
                EventPeopleFactorBucketConfig(min_people=7000, max_people=11999, factor=0.10),
                EventPeopleFactorBucketConfig(min_people=12000, max_people=999999, factor=0.14),
            ],
        ),
    )
