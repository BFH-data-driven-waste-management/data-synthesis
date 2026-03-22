from math import hypot

from data_synthesization.shared.domain.models import BinRecord


def nearest_bin_order(
    bin_ids_by_area_config: list[int],
    bins: dict[int, BinRecord],
    start_x: float,
    start_y: float,
) -> list[int]:
    remaining = [bin_id for bin_id in bin_ids_by_area_config if bin_id in bins]

    current_x, current_y = start_x, start_y
    ordered: list[int] = []

    while remaining:
        next_bin = min(
            remaining,
            key=lambda bin_id: hypot(
                bins[bin_id].coord_x - current_x,
                bins[bin_id].coord_y - current_y,
            ),
        )
        ordered.append(next_bin)
        current_x = bins[next_bin].coord_x
        current_y = bins[next_bin].coord_y
        remaining.remove(next_bin)

    return ordered
