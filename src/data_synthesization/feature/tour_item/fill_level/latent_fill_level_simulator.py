from dataclasses import dataclass
from datetime import date, timedelta
import random

from data_synthesization.feature.tour_item.fill_level.compute_weather_multiplier import compute_weather_multiplier
from data_synthesization.feature.tour_item.fill_level.util import continuous_ratio_to_ordinal_label, \
    fill_level_str_to_enum
from data_synthesization.shared.config.config_model.latent_filllevel_config import LatentFillLevelConfig
from data_synthesization.shared.domain.enums import FillLevel, VisitAction
from data_synthesization.shared.domain.models import BinRecord
from data_synthesization.feature.tour_item.fill_level.compute_event_multiplier import compute_event_multiplier
from data_synthesization.feature.tour_item.context.events_context import load_events, build_active_event_index, \
    get_active_events_for_area_and_date
from data_synthesization.shared.config.config_model.schedule_config import SeasonBounds
from data_synthesization.feature.tour_item.context.models import DailyWeatherContext


@dataclass(frozen=True)
class FillObservation:
    fill_level: FillLevel
    fill_level_continuous: float
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
        weather_by_day: dict[date, DailyWeatherContext],
    ) -> None:
        self._config = config
        self._bins_by_id = bins_by_id
        self._seasons = seasons
        self._rng = rng
        self._weather_by_day = weather_by_day
        self._states: dict[int, _BinState] = {}

        loaded_events = load_events(
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
        fill_level_key = continuous_ratio_to_ordinal_label(self._config, state.latent_fill_volume / bin_record.volume)
        fill_level = fill_level_str_to_enum(fill_level_key)

        emptied_probability = self._config.action_probabilities[fill_level_key].emptied
        emptied = self._rng.random() < emptied_probability
        action = VisitAction.EMPTIED if emptied else VisitAction.NOT_EMPTIED

        if emptied:
            state.latent_fill_volume = 0.0

        return FillObservation(fill_level=fill_level,
                               fill_level_continuous=state.latent_fill_volume / bin_record.volume,
                               action=action)

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
        weather_multiplier = compute_weather_multiplier(self._config, self._weather_by_day, area=area, current_day=current_day)
        return base_increment * event_multiplier * weather_multiplier


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

