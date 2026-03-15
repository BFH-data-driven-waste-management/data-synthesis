from data_synthesization.config.config import load_config
from data_synthesization.db.connection import connect
from data_synthesization.db.reader import read_bin_activities, read_bins
from data_synthesization.db.writer import insert_nfc_tag_mappings
from data_synthesization.generation.nfc_tag_mapping_generator import generate_nfc_tag_mapping_history
from data_synthesization.validation.nfc_tag_mapping_checks import validate_nfc_tag_mapping


def run_generate_nfc_tag_mapping(config_path: str) -> None:
    config = load_config(config_path)

    with connect(config.database.database_source_name) as connection:
        bins = read_bins(connection)
        activities = read_bin_activities(connection)
        result = generate_nfc_tag_mapping_history(bins, activities, config)

        validate_nfc_tag_mapping(
            records=result.records,
            bins=bins,
            simulation_end=config.simulation.end_date,
            min_mapping_lifetime_days=config.nfc_tag_mapping.min_mapping_lifetime_days,
        )

        insert_nfc_tag_mappings(connection, result.records)
        connection.commit()

    print(f"Loaded bins: {result.stats.total_bins}")
    print(f"Generated nfc_tag_mapping rows: {result.stats.generated_rows}")
    print(f"Bins with 0 replacements: {result.stats.bins_with_0_replacements}")
    print(f"Bins with 1 replacement: {result.stats.bins_with_1_replacement}")
    print(f"Bins with 2 replacements: {result.stats.bins_with_2_replacements}")
