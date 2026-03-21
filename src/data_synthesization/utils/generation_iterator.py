from datetime import date, timedelta

from data_synthesization.shared.config.config_model.app_config import AppConfig
from data_synthesization.utils.time import to_utc


def iter_generation_days(config: AppConfig) -> list[date]:
    simulation_start = to_utc(config.simulation.start_date).date()
    generation_end = config.simulation.tour_generation_end_date

    day_count = (generation_end - simulation_start).days + 1
    return [simulation_start + timedelta(days=offset) for offset in range(day_count)]
