from data_synthesization.feature.bin_visit.generator import BinActivityStats


def log_bin_activity_stats(stats: BinActivityStats) -> None:
    print(f"Loaded bins: {stats.total_bins}")
    print(f"Generated bin_activity rows: {stats.generated_rows}")
