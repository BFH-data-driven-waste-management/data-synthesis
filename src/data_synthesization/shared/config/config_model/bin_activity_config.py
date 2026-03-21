from dataclasses import dataclass


@dataclass(frozen=True)
class InitialStateConfig:
    poc_bins_active: bool
    late_import_bins_active: bool


@dataclass(frozen=True)
class TransitionProbabilityConfig:
    active_to_inactive_monthly: float
    inactive_to_active_monthly: float


@dataclass(frozen=True)
class EpisodeDurationConfig:
    short_share: float
    short_days_min: int
    short_days_max: int
    long_share: float
    long_days_min: int
    long_days_max: int


@dataclass(frozen=True)
class BinActivityConfig:
    initial: InitialStateConfig
    transition_probability: TransitionProbabilityConfig
    episode_duration: EpisodeDurationConfig
