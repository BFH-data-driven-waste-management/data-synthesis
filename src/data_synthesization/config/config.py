from datetime import date
from datetime import datetime
from datetime import time
from pathlib import Path
import os
from typing import Any

from data_synthesization.config.config_model.app_config import DatabaseConfig, AppConfig
from data_synthesization.config.config_model.bin_activity_config import InitialStateConfig, TransitionProbabilityConfig, \
    EpisodeDurationConfig, BinActivityConfig
from data_synthesization.config.config_model.nfc_tag_mapping_config import NfcTagMappingConfig, NfcTagMappingDistributionConfig
from data_synthesization.config.config_model.simulation_config import SimulationConfig, TourTimingConfig


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_time(value: str) -> time:
    return time.fromisoformat(value)


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    import yaml

    with config_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    simulation = raw.get("simulation", {})
    bin_activity = raw.get("bin_activity", {})
    nfc_tag_mapping = raw.get("nfc_tag_mapping", {})

    database_source_name = os.getenv("DATABASE_URL")
    if not database_source_name:
        raise ValueError("Missing: DATABASE_URL env var is not set.")

    return AppConfig(
        simulation=SimulationConfig(
            start_date=_parse_datetime(simulation["start_date"]),
            end_date=_parse_datetime(simulation["end_date"]),
            tour_generation_end_date=_parse_date(simulation["tour_generation_end_date"]),
            seed=int(simulation["seed"]),
            tour_timing=TourTimingConfig(
                reference_start_time_utc=_parse_time(simulation["tour_timing"]["reference_start_time_utc"]),
                start_time_delta_min_minutes=int(simulation["tour_timing"]["start_time_delta_min_minutes"]),
                start_time_delta_max_minutes=int(simulation["tour_timing"]["start_time_delta_max_minutes"]),
                second_phone_offset_min_seconds=int(simulation["tour_timing"]["second_phone_offset_min_seconds"]),
                second_phone_offset_max_seconds=int(simulation["tour_timing"]["second_phone_offset_max_seconds"]),
                reference_end_time_utc=_parse_time(simulation["tour_timing"]["reference_end_time_utc"]),
                reference_end_time_spread_minutes=int(simulation["tour_timing"]["reference_end_time_spread_minutes"]),
                next_day_midnight_ending_share=float(simulation["tour_timing"]["next_day_midnight_ending_share"]),
            ),
        ),
        bin_activity=BinActivityConfig(
            initial=InitialStateConfig(
                poc_bins_active=bool(bin_activity["initial"]["poc_bins_active"]),
                late_import_bins_active=bool(bin_activity["initial"]["late_import_bins_active"]),
            ),
            transition_probability=TransitionProbabilityConfig(
                active_to_inactive_monthly=float(
                    bin_activity["transition_probability"]["active_to_inactive_monthly"]
                ),
                inactive_to_active_monthly=float(
                    bin_activity["transition_probability"]["inactive_to_active_monthly"]
                ),
            ),
            episode_duration=EpisodeDurationConfig(
                short_share=float(bin_activity["episode_duration"]["short_share"]),
                short_days_min=int(bin_activity["episode_duration"]["short_days_min"]),
                short_days_max=int(bin_activity["episode_duration"]["short_days_max"]),
                long_share=float(bin_activity["episode_duration"]["long_share"]),
                long_days_min=int(bin_activity["episode_duration"]["long_days_min"]),
                long_days_max=int(bin_activity["episode_duration"]["long_days_max"]),
            ),
        ),
        nfc_tag_mapping=NfcTagMappingConfig(
            min_mapping_lifetime_days=int(nfc_tag_mapping["min_mapping_lifetime_days"]),
            replacement_distribution=NfcTagMappingDistributionConfig(
                no_replacement_share=float(nfc_tag_mapping["replacement_distribution"]["no_replacement_share"]),
                one_replacement_share=float(nfc_tag_mapping["replacement_distribution"]["one_replacement_share"]),
            ),
        ),
        database=DatabaseConfig(database_source_name=database_source_name),
    )
