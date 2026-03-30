from datetime import timedelta, date

from data_synthesization.feature.tour_item.context.models import DailyWeatherContext
from data_synthesization.shared.config.config_model.latent_filllevel_config import LatentFillLevelConfig

"""
Every day receives a weather multiplier that is influenced by the weather conditions.
Due to the daily increment the weather is considered for every day since last bin_activty
"""
def compute_weather_multiplier(_config, _weather_by_day, area: str, current_day: date) -> float:
    if not _config.weather_effects.enabled:
        return 1.0

    weather_context = _weather_by_day.get(current_day - timedelta(days=1))
    if weather_context is None:
        return 1.0

    intensity = (
        _config.weather_effects.strong_area_intensity
        if area in _config.weather_effects.strong_weather_areas
        else _config.weather_effects.default_area_intensity
    )
    score = _weather_score(_config, weather_context)
    multiplier = 1.0 + intensity * score
    return max(
        _config.weather_effects.min_multiplier,
        min(multiplier, _config.weather_effects.max_multiplier),
    )


"""
Calculates a weather score based on the configured weights and normalization for the weather variables.
All variables are normalized to the configured baseline and scale.
"""
def _weather_score(_config: LatentFillLevelConfig, weather: DailyWeatherContext) -> float:
    weights = _config.weather_effects.weights
    norm = _config.weather_effects.normalization

    temp_mean_component = weights.temp_mean * ((weather.temp_mean - norm.temp_mean_baseline) / norm.temp_mean_scale)
    temp_max_component = weights.temp_max * ((weather.temp_max - norm.temp_max_baseline) / norm.temp_max_scale)
    sunshine_component = weights.sunshine * ((weather.sunshine_duration - norm.sunshine_baseline) / norm.sunshine_scale)
    precipitation_component = weights.precipitation * (
                (weather.precipitation - norm.precipitation_baseline) / norm.precipitation_scale)

    return temp_mean_component + temp_max_component + sunshine_component - precipitation_component
