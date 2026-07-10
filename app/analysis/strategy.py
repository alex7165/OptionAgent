from enum import StrEnum


class Strategy(StrEnum):
    SHORT_STRANGLE = "Short Strangle"
    IRON_CONDOR = "Iron Condor"
    STRADDLE = "Straddle"