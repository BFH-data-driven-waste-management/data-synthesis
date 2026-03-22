from math import hypot


def estimate_travel_seconds(
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
