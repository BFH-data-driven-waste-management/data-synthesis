import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class DailyWeatherContext:
    temp_mean: float
    temp_max: float
    precipitation: float
    sunshine_duration: float


def load_daily_weather_context(path: str | Path) -> dict[date, DailyWeatherContext]:
    weather_by_day: dict[date, DailyWeatherContext] = {}
    weather_path = Path(path)

    with weather_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            day = _parse_reference_day(row.get("reference_timestamp", ""))
            if day is None:
                continue
            weather_by_day[day] = DailyWeatherContext(
                temp_mean=_to_float(row.get("tre200d0")),
                temp_max=_to_float(row.get("tre200dx")),
                precipitation=_to_float(row.get("rka150d0")),
                sunshine_duration=_to_float(row.get("sre000d0")),
            )

    return weather_by_day


def resolve_latest_weather_file(pattern: str) -> Path:
    weather_files = sorted(Path().glob(pattern))
    if not weather_files:
        raise FileNotFoundError(f"No weather file found matching pattern: {pattern}")
    return weather_files[-1]


def _parse_reference_day(raw: str) -> date | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _to_float(value: str | None) -> float:
    if value is None:
        return 0.0
    parsed = value.strip().replace(",", ".")
    if parsed == "":
        return 0.0
    return float(parsed)
