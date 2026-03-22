from datetime import datetime, timedelta
from math import hypot


def event_timestamps_for_next_stop(
    current_x: float,
    current_y: float,
    current_timestamp: datetime,
    target_x: float,
    target_y: float,
    seconds_spent: int,
    road_network_detour_factor: float,
    average_speed_meters_per_second: float,
) -> tuple[datetime, datetime]:
    travel_seconds = _estimate_travel_seconds(
        start_x=current_x,
        start_y=current_y,
        target_x=target_x,
        target_y=target_y,
        road_network_detour_factor=road_network_detour_factor,
        average_speed_meters_per_second=average_speed_meters_per_second,
    )
    event_timestamp = current_timestamp + timedelta(seconds=travel_seconds + seconds_spent)
    return event_timestamp, event_timestamp + timedelta(seconds=1)


def _estimate_travel_seconds(
    start_x: float,
    start_y: float,
    target_x: float,
    target_y: float,
    road_network_detour_factor: float,
    average_speed_meters_per_second: float,
) -> int:
    direct_distance_meters = hypot(target_x - start_x, target_y - start_y)
    network_distance_meters = direct_distance_meters * road_network_detour_factor
    return max(1, int(network_distance_meters / average_speed_meters_per_second))
