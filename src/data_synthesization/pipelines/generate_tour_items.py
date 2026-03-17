from datetime import timedelta
from pathlib import Path

from data_synthesization.config.config import load_config
from data_synthesization.db.connection import connect
from data_synthesization.db.reader import read_bins
from data_synthesization.generation.tour_item_generator import (
    TourItemVisit,
    VehicleEmptyingEvent,
    generate_day_tour_items,
    load_bins_by_area,
)
from data_synthesization.utils.generation_iterator import iter_generation_days
from data_synthesization.utils.schedule import load_service_schedule
from data_synthesization.utils.time import to_utc, parse_datetime

SCHEDULE_PATH = Path("config/schedule.yaml")
BIN_MAPPING_PATH = Path("data/static/bin_neighbourhood_mapping.csv")


def run_generate_tour_items(config_path: str) -> None:
    config = load_config(config_path)
    service_schedule = load_service_schedule(SCHEDULE_PATH)
    bins_by_area_config = load_bins_by_area(BIN_MAPPING_PATH)

    with connect(config.database.database_source_name) as connection:
        bins = read_bins(connection)

    bins_by_id = {_bin.id: _bin for _bin in bins}
    for day in iter_generation_days(config):
        result = generate_day_tour_items(
            day=day,
            vehicles=service_schedule.vehicles,
            seasons=service_schedule.seasons,
            bins_by_area=bins_by_area_config,
            bins=bins_by_id,
        )

        for event in result.events:
            if isinstance(event, TourItemVisit):
                print(
                    f"bin_visit day={event.day.isoformat()} vehicle={event.vehicle_number} "
                    f"area={event.area} bin_id={event.bin_id} "
                    f"coord_x={event.coord_x:.2f} coord_y={event.coord_y:.2f}"
                )
                continue

            if isinstance(event, VehicleEmptyingEvent):
                print(
                    f"vehicle_emptying day={event.day.isoformat()} vehicle={event.vehicle_number} "
                    f"coord_x={event.coord_x:.2f} coord_y={event.coord_y:.2f}"
                )
