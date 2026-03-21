from data_synthesization.feature.bin_visit.generator import BinActivityStats
from data_synthesization.feature.nfc_tag_mapping.generator import NfcTagMappingGenerationStats
from data_synthesization.generation.tour_generator import TourGenerationStats


def log_bin_activity_stats(stats: BinActivityStats) -> None:
    print(f"Loaded bins: {stats.total_bins}")
    print(f"Generated bin_activity rows: {stats.generated_rows}")


def log_nfc_tag_mapping_stats(stats: NfcTagMappingGenerationStats):
    print(f"Loaded bins: {stats.total_bins}")
    print(f"Generated nfc_tag_mapping rows: {stats.generated_rows}")


def log_tour_stats(stats: TourGenerationStats):
    print(f"Generated tour rows: {stats.generated_rows}")
    print(f"Generation days: {stats.generated_days}")
