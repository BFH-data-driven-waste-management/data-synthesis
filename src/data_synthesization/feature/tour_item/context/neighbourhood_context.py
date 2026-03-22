import csv
from pathlib import Path

BIN_MAPPING_PATH = Path("data/static/bin_neighbourhood_mapping.csv")


def load_bins_by_area() -> dict[str, list[int]]:
    bins_by_area: dict[str, list[int]] = {}
    with Path(BIN_MAPPING_PATH).open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            area = str(row["name"])
            bins_by_area.setdefault(area, []).append(int(row["bin_id"]))
    return bins_by_area
