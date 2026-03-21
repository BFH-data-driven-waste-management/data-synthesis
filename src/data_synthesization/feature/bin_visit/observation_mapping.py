from datetime import datetime, timezone

from data_synthesization.config.config_model.app_config import AppConfig

POC_CREATED_AT = datetime(2024, 12, 31, 2, 0, 0, tzinfo=timezone.utc)
LATE_IMPORT_CREATED_AT = datetime(2025, 1, 1, 2, 0, 0, tzinfo=timezone.utc)


def is_created_at_date_initially_active(created_at: datetime, config: AppConfig) -> bool:
    if created_at == POC_CREATED_AT:
        return config.bin_activity.initial.poc_bins_active
    if created_at == LATE_IMPORT_CREATED_AT:
        return config.bin_activity.initial.late_import_bins_active
    else: return False