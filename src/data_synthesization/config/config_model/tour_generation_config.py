from dataclasses import dataclass


@dataclass(frozen=True)
class TourItemGenerationConfig:
    vehicle_emptying_coords: tuple[float, float]
    empty_after_volume: int


@dataclass(frozen=True)
class TourAndNfcMappingConfig:
    average_speed_meters_per_second: float
    road_network_detour_factor: float
    seconds_per_bin_visit: int
    seconds_per_vehicle_emptying: int
