from data_synthesization.config.config import load_config
from data_synthesization.db.connection import connect
from data_synthesization.db.reader import read_bins
from data_synthesization.db.writer import insert_bin_activity
from data_synthesization.generation.bin_activity_generator import generate_bin_activity
from data_synthesization.validation.bin_activity_checks import validate_bin_activity


def run_generate_bin_activity(config_path: str) -> None:
    config = load_config(config_path)

    with connect(config.database.database_source_name) as connection:
        bins = read_bins(connection)
        result = generate_bin_activity(bins, config)

        validate_bin_activity(
            records=result.records,
            bins=bins,
            simulation_start=config.simulation.start_date,
            simulation_end=config.simulation.end_date,
        )

        insert_bin_activity(connection, result.records)
        connection.commit()

    print(f"Loaded bins: {result.stats.total_bins}")
    print(f"PoC bins: {result.stats.poc_bins}")
    print(f"Late import bins: {result.stats.late_import_bins}")
    print(f"Generated bin_activity rows: {result.stats.generated_rows}")
    print(f"Bins with 0 extra switches: {result.stats.bins_with_no_extra_switch}")
    print(f"Bins with >0 extra switch: {result.stats.bins_with_extra_switch}")
