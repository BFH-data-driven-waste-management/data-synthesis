#!/usr/bin/env python3
from datetime import date, timedelta
from pathlib import Path

from data_synthesization.utils.service_schedule import areas_for_vehicle_day, load_service_schedule

START_DATE = "2025-04-21"
END_DATE = "2025-05-11"
SCHEDULE_PATH = Path("config/schedule.yaml")


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

# simulates the schedule on a given date-range.
# this script is not need for generation, but useful for debugging.
def main() -> None:
    service_schedule = load_service_schedule(SCHEDULE_PATH)
    start = parse_date(START_DATE)
    end = parse_date(END_DATE)

    for day in iter_dates(start, end):
        print(day.isoformat())
        for vehicle in service_schedule.vehicles:
            route = areas_for_vehicle_day(vehicle, day, service_schedule.seasons)
            print(f"  vehicle {vehicle.vehicle_number}: {' -> '.join(route)}")
        print()


if __name__ == "__main__":
    main()
