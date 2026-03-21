from dataclasses import dataclass


@dataclass(frozen=True)
class ThresholdsConfig:
    empty_or_almost_empty_max_ratio: float
    half_full_max_ratio: float
    full_max_ratio: float


@dataclass(frozen=True)
class RatioRangeConfig:
    min: float
    max: float


@dataclass(frozen=True)
class ActionProbabilityConfig:
    emptied: float


@dataclass(frozen=True)
class EventPeopleFactorBucketConfig:
    min_people: int
    max_people: int
    factor: float


@dataclass(frozen=True)
class EventEffectsConfig:
    enabled: bool
    area_weight_default: float
    random_multiplier_min: float
    random_multiplier_max: float
    per_day_event_increment_cap_ratio: float
    multi_event_combination_cap_ratio: float
    people_factor_buckets: list[EventPeopleFactorBucketConfig]


@dataclass(frozen=True)
class LatentFillLevelConfig:
    thresholds: ThresholdsConfig
    action_probabilities: dict[str, ActionProbabilityConfig]
    seasonal_factors: dict[str, float]
    weekday_factors: dict[str, float]
    random_daily_multiplier: RatioRangeConfig
    zone_base_fill_rate_ratio_per_day: dict[str, float]
    zone_base_fill_rate_ratio_per_day_weekday_overrides: dict[str, dict[str, float]]
    event_effects: EventEffectsConfig
