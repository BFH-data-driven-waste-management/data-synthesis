from enum import StrEnum


class VisitAction(StrEnum):
    EMPTIED = "EMPTIED"
    NOT_EMPTIED = "NOT_EMPTIED"


class FillLevel(StrEnum):
    OVERFULL = "OVERFULL"
    FULL = "FULL"
    HALF_FULL = "HALF_FULL"
    EMPTY_OR_ALMOST_EMPTY = "EMPTY_OR_ALMOST_EMPTY"


class ConnectivityState(StrEnum):
    OFFLINE = "OFFLINE"
    ONLINE = "ONLINE"
