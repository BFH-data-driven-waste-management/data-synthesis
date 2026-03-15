from datetime import datetime, time, timezone

from data_synthesization.config.config import load_config
from data_synthesization.db.connection import connect
from data_synthesization.db.reader import read_vehicles
from data_synthesization.db.writer import insert_tours
from data_synthesization.generation.tour_generator import generate_tours
from data_synthesization.validation.tour_checks import validate_tours


def run_generate_tours(config_path: str) -> None:
    config = load_config(config_path)

    with connect(config.database.database_source_name) as connection:
        vehicle_ids = read_vehicles(connection)
        result = generate_tours(vehicle_ids, config)

        generation_end = datetime.combine(
            config.simulation.tour_generation_end_date,
            time(hour=23, minute=59, second=59),
            tzinfo=timezone.utc,
        )
        validate_tours(
            records=result.records,
            simulation_start=config.simulation.start_date,
            generation_end_date=generation_end,
        )

        insert_tours(connection, result.records)
        connection.commit()

    print(f"Generated tour rows: {result.stats.generated_rows}")
    print(f"Generation days: {result.stats.generated_days}")
