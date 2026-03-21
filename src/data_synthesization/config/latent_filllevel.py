from pathlib import Path
from typing import Any

import yaml

from data_synthesization.config.config_model.latent_filllevel_config import (
    ActionProbabilityConfig,
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
    )
