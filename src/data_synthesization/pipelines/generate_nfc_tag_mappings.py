from data_synthesization.shared.config.config import load_config
from data_synthesization.shared.db.connection import connect
from data_synthesization.shared.db.reader import read_bin_activities, read_bins
from data_synthesization.shared.db.writer import insert_nfc_tag_mappings
from data_synthesization.feature.nfc_tag_mapping.generator import generate_nfc_tag_mapping_history
from data_synthesization.shared.logging import log_nfc_tag_mapping_stats
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

    log_nfc_tag_mapping_stats(result.stats)
