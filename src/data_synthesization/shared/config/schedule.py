from pathlib import Path

import yaml

from data_synthesization.shared.config.config_model.schedule_config import (
    ServiceSchedule,
    VehicleSchedule,
)


def load_service_schedule(schedule_path: str | Path) -> ServiceSchedule:
    raw = yaml.safe_load(Path(schedule_path).read_text(encoding="utf-8"))
    root = raw["service_schedule"]

    seasons = {
        str(season_name): (
            (int(season_data["start_month"]), int(season_data["start_day"])),
            (int(season_data["end_month"]), int(season_data["end_day"])),
        )
        for season_name, season_data in root.get("seasons", {}).items()
    }
    vehicles = [VehicleSchedule.from_dict(item) for item in root.get("vehicles", [])]
    return ServiceSchedule(seasons=seasons, vehicles=vehicles)