import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import yaml

WEATHER_URLS = [
    "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/neu/ogd-smn_neu_d_historical.csv", # historical until last year
    "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/neu/ogd-smn_neu_d_recent.csv", # current year
]
COLUMNS_TO_KEEP = [
    "reference_timestamp",
    "tre200d0", # air temperature, 2m above ground, average, °C
    "tre200dx", # air temperature, 2m above ground, maximum, °C
    "rka150d0", # daily rainfall mm
    "sre000d0", # sunshine duration in minutes
]

def read_simulation_start(config_path: Path) -> pd.Timestamp:
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    start_date_raw = config["simulation"]["start_date"]
    start_date = pd.to_datetime(start_date_raw, utc=True)
    return start_date.tz_convert(None)


def download_weather_csv(url: str) -> pd.DataFrame:
    with urlopen(url) as response:
        return pd.read_csv(response, sep=";")


def download_weather_data() -> pd.DataFrame:
    weather_frames = [download_weather_csv(url) for url in WEATHER_URLS]
    return pd.concat(weather_frames, ignore_index=True)


def transform_weather(df: pd.DataFrame, simulation_start: pd.Timestamp) -> pd.DataFrame:
    transformed = df.copy()
    transformed["reference_timestamp"] = pd.to_datetime(
        transformed["reference_timestamp"],
        format="%d.%m.%Y %H:%M",
        errors="coerce",
    )
    transformed = transformed.dropna(subset=["reference_timestamp"])

    transformed = transformed.sort_values("reference_timestamp")
    transformed = transformed.drop_duplicates(subset=["reference_timestamp"], keep="last")

    filtered = transformed[transformed["reference_timestamp"] >= simulation_start]
    return filtered.loc[:, COLUMNS_TO_KEEP]


def output_path(output_dir: Path) -> Path:
    run_date = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    return output_dir / f"historical_weater_neuchatle_{run_date}.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and prepare historical + recent MeteoSchweiz weather data for Neuchatel.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/base.yaml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/static"),
    )
    args = parser.parse_args()

    simulation_start = read_simulation_start(args.config)
    weather = download_weather_data()
    prepared = transform_weather(weather, simulation_start)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = output_path(args.output_dir)
    prepared.to_csv(target, index=False)
    print(f"Saved {len(prepared)} rows to {target}")


if __name__ == "__main__":
    main()
