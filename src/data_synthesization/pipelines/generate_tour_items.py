import random
from datetime import timedelta
from pathlib import Path

from data_synthesization.feature.tour_item.context.neighbourhood_context import load_bins_by_area
from data_synthesization.feature.tour_item.context.weather_context import DEFAULT_WEATHER_FILE_PATTERN, load_weather_context
from data_synthesization.feature.tour_item.generator import generate_tour_item_records
from data_synthesization.feature.tour_item.fill_level.latent_filllevel_simulator import LatentFillLevelSimulator
from data_synthesization.shared.config.config import load_config
from data_synthesization.shared.config.latent_filllevel import load_latent_filllevel_config
from data_synthesization.shared.config.schedule import load_service_schedule
from data_synthesization.shared.db.connection import connect
from data_synthesization.shared.db.reader import read_bin_activities, read_bins, read_nfc_tag_mappings, read_tours
from data_synthesization.shared.db.writer import insert_bin_visits, insert_vehicle_emptyings, update_tours_ended_at
from data_synthesization.shared.logging import log_tour_item_stats

SCHEDULE_PATH = Path("config/schedule.yaml")
LATENT_FILLLEVEL_PATH = Path("config/latent_filllevel.yaml")


def run_generate_tour_items(config_path: str) -> None:
    config = load_config(config_path)
    service_schedule = load_service_schedule(SCHEDULE_PATH)
    latent_filllevel_config = load_latent_filllevel_config(path=LATENT_FILLLEVEL_PATH)
    weather_by_day = load_weather_context(DEFAULT_WEATHER_FILE_PATTERN)
    bins_by_area_config = load_bins_by_area()
    rng = random.Random(config.simulation.seed)

    with connect(config.database.database_source_name) as connection:
        bins = read_bins(connection)
        bin_activities = read_bin_activities(connection)
        tours = read_tours(connection)
        nfc_tag_mappings = read_nfc_tag_mappings(connection)

        bins_by_id = {_bin.id: _bin for _bin in bins}
        latent_filllevel_simulator = LatentFillLevelSimulator(
            config=latent_filllevel_config,
            bins_by_id=bins_by_id,
            bins_by_area=bins_by_area_config,
            seasons=service_schedule.seasons,
            rng=rng,
            weather_by_day=weather_by_day,
        )

        result = generate_tour_item_records(
            config=config,
            service_schedule=service_schedule,
            bins_by_area_config=bins_by_area_config,
            bins=bins,
            bin_activities=bin_activities,
            tours=tours,
            nfc_tag_mappings=nfc_tag_mappings,
            rng=rng,
            latent_filllevel_simulator=latent_filllevel_simulator,
        )

        insert_bin_visits(connection, result.bin_visit_records)
        insert_vehicle_emptyings(connection, result.vehicle_emptying_records)

        tours_closed_after_last_vehicle_emptying = [
            (tour_id, ended_at + timedelta(seconds=rng.randint(8, 12)))
            for tour_id, ended_at in result.last_vehicle_emptying_per_tour
        ]

        update_tours_ended_at(connection, tours_closed_after_last_vehicle_emptying)
        connection.commit()

    log_tour_item_stats(result.stats)


