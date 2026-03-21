from dataclasses import dataclass
from datetime import date, timedelta
import random
from pathlib import Path

from data_synthesization.shared.config.config_model.latent_filllevel_config import LatentFillLevelConfig
from data_synthesization.shared.domain.enums import FillLevel, VisitAction
from data_synthesization.shared.domain.models import BinRecord
from data_synthesization.generation.event_effects import (
    build_active_event_index,
    compute_event_multiplier,
    get_active_events_for_area_and_date,
    load_events,
)
from data_synthesization.shared.utils.schedule import SeasonBounds
from data_synthesization.shared.utils.weather import DailyWeatherContext


@dataclass(frozen=True)
class FillObservation:
    fill_level: FillLevel
    action: VisitAction


@dataclass
class _BinState:
    latent_fill_volume: float
    last_updated_day: date


class LatentFillLevelSimulator:
    def __init__(
        self,
        config: LatentFillLevelConfig,
        bins_by_id: dict[int, BinRecord],
        bins_by_area: dict[str, list[int]],
        seasons: dict[str, SeasonBounds],
        rng: random.Random,
        events_path: str | Path,
        weather_by_day: dict[date, DailyWeatherContext],
    ) -> None:
        self._config = config
        self._bins_by_id = bins_by_id
        self._seasons = seasons
        self._rng = rng
        self._weather_by_day = weather_by_day
        self._states: dict[int, _BinState] = {}

        loaded_events = load_events(
            events_path,
            known_areas=set(bins_by_area.keys()),
            bins_by_area=bins_by_area,
        )
        self._active_event_index = build_active_event_index(loaded_events)

    """
    Simulates the latent fill level of a bin over time.
    Determines fill level label and action based on the observed fill level.
    """
    def observe_visit(self, bin_id: int, area: str, visit_day: date) -> FillObservation:
        bin_record = self._bins_by_id[bin_id]
        state = self._state_for_visit(bin_id=bin_id, area=area, visit_day=visit_day)
        fill_level_key = self._fill_level_key(state.latent_fill_volume / bin_record.volume)
        fill_level = self._to_observed_fill_level(fill_level_key)

        emptied_probability = self._config.action_probabilities[fill_level_key].emptied
        emptied = self._rng.random() < emptied_probability
        action = VisitAction.EMPTIED if emptied else VisitAction.NOT_EMPTIED

        if emptied:
            state.latent_fill_volume = 0.0

        return FillObservation(fill_level=fill_level, action=action)

    """
    Determines the latent waste for a visit to a bin.
    Note: this is only used for calculating the actual capacity addition to the vehicle.
    FIXME: The latent fill level should only be calculated and used via observe_visit. Therefore the time when the observe_visit
    function is called should be changed.    
    """
    def latent_collection_ratio_for_visit(self, bin_id: int, area: str, visit_day: date) -> float:
        state = self._state_for_visit(bin_id=bin_id, area=area, visit_day=visit_day)
        bin_record = self._bins_by_id[bin_id]
        fill_level_key = self._fill_level_key(state.latent_fill_volume / bin_record.volume)
        if fill_level_key == "half_full":
            return 0.5
        if fill_level_key in ("full", "over_full"):
            return 1.0
        return 0.0

    def _state_for_visit(self, bin_id: int, area: str, visit_day: date) -> _BinState:
        bin_record = self._bins_by_id[bin_id]
        state = self._states.get(bin_id)
        if state is None:
            initial_ratio = self._rng.uniform(0.05, 0.35)
            state = _BinState(latent_fill_volume=bin_record.volume * initial_ratio, last_updated_day=visit_day)
            self._states[bin_id] = state
            return state

        self._accumulate_between_days(state, bin_record, area, visit_day)
        return state

    """
    for each day since last update, accumulate the daily increment of the latent fill level.
    """
    def _accumulate_between_days(self, state: _BinState, bin_record: BinRecord, area: str, visit_day: date) -> None:
        day = state.last_updated_day + timedelta(days=1)
        while day <= visit_day:
            state.latent_fill_volume += self._daily_increment(bin_record.volume, area, day)
            state.latent_fill_volume = max(0.0, min(state.latent_fill_volume, float(bin_record.volume)))
            day += timedelta(days=1)
        state.last_updated_day = visit_day

    """
    central logic for calculating the daily increment of the latent fill level in liters.
    """
    def _daily_increment(self, volume: int, area: str, current_day: date) -> float:
        weekday_name = current_day.strftime("%A").lower()
        base_rate = self._base_rate_for_day(area, weekday_name)
        seasonal_factor = self._config.seasonal_factors.get(self._season_for_day(current_day), 1)
        weekday_factor = self._config.weekday_factors.get(weekday_name, 1.0)

        random_multiplier = self._rng.uniform(
            self._config.random_daily_multiplier.min,
            self._config.random_daily_multiplier.max,
        )
        base_increment = volume * base_rate * seasonal_factor * weekday_factor * random_multiplier
        active_events = get_active_events_for_area_and_date(
            self._active_event_index,
            area=area,
            current_day=current_day,
        )
        event_multiplier = compute_event_multiplier(
            active_events=active_events,
            config=self._config.event_effects,
            rng=self._rng,
        )
        weather_multiplier = self._weather_multiplier(area=area, current_day=current_day)
        return base_increment * event_multiplier * weather_multiplier

    """
    Every day receives a weather multiplier that is influenced by the weather conditions.
    Due to the daily increment the weather is considered for every day since last bin_visit
    """
    def _weather_multiplier(self, area: str, current_day: date) -> float:
        if not self._config.weather_effects.enabled:
            return 1.0

        weather_context = self._weather_by_day.get(current_day - timedelta(days=1))
        if weather_context is None:
            return 1.0

        intensity = (
            self._config.weather_effects.strong_area_intensity
            if area in self._config.weather_effects.strong_weather_areas
            else self._config.weather_effects.default_area_intensity
        )
        score = self._weather_score(weather_context)
        multiplier = 1.0 + intensity * score
        return max(
            self._config.weather_effects.min_multiplier,
            min(multiplier, self._config.weather_effects.max_multiplier),
        )

    """
    Calculates a weather score based on the configured weights and normalization for the weather variables.
    All variables are normalized to the configured baseline and scale.
    """
    def _weather_score(self, weather: DailyWeatherContext) -> float:
        weights = self._config.weather_effects.weights
        norm = self._config.weather_effects.normalization

        temp_mean_component = weights.temp_mean * ((weather.temp_mean - norm.temp_mean_baseline) / norm.temp_mean_scale)
        temp_max_component = weights.temp_max * ((weather.temp_max - norm.temp_max_baseline) / norm.temp_max_scale)
        sunshine_component = weights.sunshine * ((weather.sunshine_duration - norm.sunshine_baseline) / norm.sunshine_scale)
        precipitation_component = weights.precipitation * ((weather.precipitation - norm.precipitation_baseline) / norm.precipitation_scale)

        return temp_mean_component + temp_max_component + sunshine_component - precipitation_component

    def _base_rate_for_day(self, area: str, weekday_name: str) -> float:
        area_overrides = self._config.zone_base_fill_rate_ratio_per_day_weekday_overrides.get(area, {})
        if weekday_name in area_overrides:
            return area_overrides[weekday_name]
        return self._config.zone_base_fill_rate_ratio_per_day.get(
            area,
            self._config.zone_base_fill_rate_ratio_per_day["default"],
        )

    def _season_for_day(self, current_day: date) -> str:
        month_day = (current_day.month, current_day.day)
        for season_name, (start, end) in self._seasons.items():
            if start <= month_day <= end:
                return season_name
        return "default"

    def _fill_level_key(self, ratio: float) -> str:
        if ratio <= self._config.thresholds.empty_or_almost_empty_max_ratio:
            return "empty_or_almost_empty"
        if ratio <= self._config.thresholds.half_full_max_ratio:
            return "half_full"
        if ratio <= self._config.thresholds.full_max_ratio:
            return "full"
        return "over_full"

    @staticmethod
    def _to_observed_fill_level(fill_level_key: str) -> FillLevel:
        mapping = {
            "empty_or_almost_empty": FillLevel.EMPTY_OR_ALMOST_EMPTY,
            "half_full": FillLevel.HALF_FULL,
            "full": FillLevel.FULL,
            "over_full": FillLevel.OVERFULL,
        }
        return mapping[fill_level_key]
