from data_synthesization.shared.config.config import load_config
from data_synthesization.shared.db.connection import connect
from data_synthesization.shared.db.reader import read_bins
from data_synthesization.shared.db.writer import insert_bin_activity
from data_synthesization.feature.bin_visit.generator import generate_bin_activity_records
from data_synthesization.shared.logging import log_bin_activity_stats
from data_synthesization.validation.bin_activity_checks import validate_bin_activity


def run_generate_bin_activity(config_path: str) -> None:
    config = load_config(config_path)

    with connect(config.database.database_source_name) as connection:
        bins = read_bins(connection)
        result = generate_bin_activity_records(bins, config)

        insert_bin_activity(connection, result.records)
        connection.commit()

    validate_bin_activity(
        records=result.records,
        bins=bins,
        simulation_start=config.simulation.start_date,
        simulation_end=config.simulation.end_date,
    )

    log_bin_activity_stats(result.stats)
