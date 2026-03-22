from datetime import date
from datetime import time
from pathlib import Path
import os
from typing import Any

from data_synthesization.shared.config.config_model.app_config import DatabaseConfig, AppConfig
from data_synthesization.shared.config.config_model.bin_activity_config import InitialStateConfig, TransitionProbabilityConfig, \
    EpisodeDurationConfig, BinActivityConfig
from data_synthesization.shared.config.config_model.nfc_tag_mapping_config import NfcTagMappingConfig, NfcTagMappingDistributionConfig
from data_synthesization.shared.config.config_model.simulation_config import SimulationConfig, TourTimingConfig
from data_synthesization.shared.config.config_model.tour_generation_config import (
    TourAndNfcMappingConfig,
    TourItemGenerationConfig,
)
from data_synthesization.shared.utils.time import parse_datetime


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
    tour_item_generation = raw.get("tour_item_generation", {})
    tour_and_nfc_mapping = raw.get("tour_and_nfc_mapping", {})

    database_source_name = os.getenv("DATABASE_URL")
    if not database_source_name:
        raise ValueError("Missing: DATABASE_URL env var is not set.")

    return AppConfig(
        simulation=SimulationConfig(
            start_date=parse_datetime(simulation["start_date"]),
            end_date=parse_datetime(simulation["end_date"]),
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
        tour_item_generation=TourItemGenerationConfig(
            vehicle_emptying_coords=(
                float(tour_item_generation["VEHICLE_EMPTYING_COORDS"][0]),
                float(tour_item_generation["VEHICLE_EMPTYING_COORDS"][1]),
            ),
            empty_after_volume=int(tour_item_generation["EMTPY_AFTER_VOLUME"]),
            missing_vehicle_emptying_log_share=float(
                tour_item_generation["MISSING_VEHICLE_EMPTYING_LOG_SHARE"]
            ),
            cross_tour_duplicate_assignment_share=float(
                tour_item_generation["CROSS_TOUR_DUPLICATE_ASSIGNMENT_SHARE"]
            ),
        ),
        tour_and_nfc_mapping=TourAndNfcMappingConfig(
            average_speed_meters_per_second=float(tour_and_nfc_mapping["AVERAGE_SPEED_METERS_PER_SECOND"]),
            road_network_detour_factor=float(tour_and_nfc_mapping["ROAD_NETWORK_DETOUR_FACTOR"]),
            seconds_per_bin_visit=int(tour_and_nfc_mapping["SECONDS_PER_BIN_VISIT"]),
            seconds_per_vehicle_emptying=int(tour_and_nfc_mapping["SECONDS_PER_VEHICLE_EMPTYING"]),
        ),
        database=DatabaseConfig(database_source_name=database_source_name),
    )
