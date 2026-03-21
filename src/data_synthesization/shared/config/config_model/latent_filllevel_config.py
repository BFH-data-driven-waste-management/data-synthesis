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
    people_factor_buckets: list[EventPeopleFactorBucketConfig]


@dataclass(frozen=True)
class WeatherVariableWeightsConfig:
    temp_mean: float
    temp_max: float
    sunshine: float
    precipitation: float


@dataclass(frozen=True)
class WeatherNormalizationConfig:
    temp_mean_baseline: float
    temp_mean_scale: float
    temp_max_baseline: float
    temp_max_scale: float
    sunshine_baseline: float
    sunshine_scale: float
    precipitation_baseline: float
    precipitation_scale: float


@dataclass(frozen=True)
class WeatherEffectConfig:
    enabled: bool
    strong_weather_areas: set[str]
    strong_area_intensity: float
    default_area_intensity: float
    min_multiplier: float
    max_multiplier: float
    weights: WeatherVariableWeightsConfig
    normalization: WeatherNormalizationConfig


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
    weather_effects: WeatherEffectConfig
