from data_synthesization.shared.domain.enums import FillLevel


def continuous_ratio_to_ordinal_label(_config, ratio: float) -> str:
    if ratio <= _config.thresholds.empty_or_almost_empty_max_ratio:
        return "empty_or_almost_empty"
    if ratio <= _config.thresholds.half_full_max_ratio:
        return "half_full"
    if ratio <= _config.thresholds.full_max_ratio:
        return "full"
    return "over_full"


def fill_level_str_to_enum(fill_level_key: str) -> FillLevel:
    mapping = {
        "empty_or_almost_empty": FillLevel.EMPTY_OR_ALMOST_EMPTY,
        "half_full": FillLevel.HALF_FULL,
        "full": FillLevel.FULL,
        "over_full": FillLevel.OVERFULL,
    }
    return mapping[fill_level_key]
