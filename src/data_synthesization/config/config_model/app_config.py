from dataclasses import dataclass

from data_synthesization.config.config_model.bin_activity_config import BinActivityConfig
from data_synthesization.config.config_model.nfc_tag_mapping_config import NfcTagMappingConfig
from data_synthesization.config.config_model.simulation_config import SimulationConfig
from data_synthesization.config.config_model.tour_generation_config import (
    TourAndNfcMappingConfig,
    TourItemGenerationConfig,
)


@dataclass(frozen=True)
class DatabaseConfig:
    database_source_name: str


@dataclass(frozen=True)
class AppConfig:
    simulation: SimulationConfig
    bin_activity: BinActivityConfig
    nfc_tag_mapping: NfcTagMappingConfig
    tour_item_generation: TourItemGenerationConfig
    tour_and_nfc_mapping: TourAndNfcMappingConfig
    database: DatabaseConfig
