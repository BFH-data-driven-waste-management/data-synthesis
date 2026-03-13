from dataclasses import dataclass

from data_synthesization.config.config_model.bin_activity_config import BinActivityConfig
from data_synthesization.config.config_model.simulation_config import SimulationConfig


@dataclass(frozen=True)
class DatabaseConfig:
    database_source_name: str


@dataclass(frozen=True)
class AppConfig:
    simulation: SimulationConfig
    bin_activity: BinActivityConfig
    database: DatabaseConfig
