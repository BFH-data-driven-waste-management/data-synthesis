from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BinRecord:
    id: int
    created_at: datetime


@dataclass(frozen=True)
class BinActivityRecord:
    bin_id: int
    active: bool
    activity_timestamp: datetime
