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
from data_synthesization.utils.service_schedule import load_service_schedule
from data_synthesization.utils.time import to_utc

SCHEDULE_PATH = Path("config/schedule.yaml")
BIN_MAPPING_PATH = Path("data/static/bin_neighbourhood_mapping.csv")


def run_generate_tour_items(config_path: str) -> None:
    config = load_config(config_path)
    service_schedule = load_service_schedule(SCHEDULE_PATH)
    bins_by_area_config = load_bins_by_area(BIN_MAPPING_PATH)

    with connect(config.database.database_source_name) as connection:
        bin_locations_list = read_bins(connection)

    bin_locations = {item.id: item for item in bin_locations_list}
    first_day = to_utc(config.simulation.start_date).date()

    result = generate_day_tour_items(
        day=first_day,
        vehicles=service_schedule.vehicles,
        seasons=service_schedule.seasons,
        bins_by_area=bins_by_area_config,
        bins=bin_locations,
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
