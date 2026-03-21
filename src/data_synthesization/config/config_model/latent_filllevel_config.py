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
class LatentFillLevelConfig:
    thresholds: ThresholdsConfig
    action_probabilities: dict[str, ActionProbabilityConfig]
    seasonal_factors: dict[str, float]
    weekday_factors: dict[str, float]
    random_daily_multiplier: RatioRangeConfig
    zone_base_fill_rate_ratio_per_day: dict[str, float]
