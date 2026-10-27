"""Data models for CotaStack tolerance chain calculations."""

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class Item:
    """Represents a single dimension/link in a 1D tolerance chain."""
    name: str
    nominal: float
    tolerance_minus: float
    tolerance_plus: float
    direction: Literal["positive", "negative"] = "positive"

    def __post_init__(self) -> None:
        if self.tolerance_minus > 0:
            raise ValueError("tolerance_minus must be <= 0")
        if self.tolerance_plus < 0:
            raise ValueError("tolerance_plus must be >= 0")
        if self.nominal < 0:
            raise ValueError("nominal must be >= 0")

    @property
    def upper_limit(self) -> float:
        return self.nominal + self.tolerance_plus

    @property
    def lower_limit(self) -> float:
        return self.nominal + self.tolerance_minus

    @property
    def tolerance_total(self) -> float:
        return self.tolerance_plus - self.tolerance_minus


@dataclass(slots=True)
class ChainResult:
    """Result of a tolerance chain calculation."""
    nominal: float
    worst_case_minus: float
    worst_case_plus: float
    rss_minus: float
    rss_plus: float
    items: list[Item]