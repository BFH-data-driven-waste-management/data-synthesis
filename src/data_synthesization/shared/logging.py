from data_synthesization.feature.bin_visit.generator import BinActivityStats
from data_synthesization.feature.nfc_tag_mappinggenerator.generator import NfcTagMappingGenerationStats


def log_bin_activity_stats(stats: BinActivityStats) -> None:
    print(f"Loaded bins: {stats.total_bins}")
    print(f"Generated bin_activity rows: {stats.generated_rows}")


def log_nfc_tag_mapping_stats(stats: NfcTagMappingGenerationStats):
    print(f"Loaded bins: {stats.total_bins}")
    print(f"Generated nfc_tag_mapping rows: {stats.generated_rows}")