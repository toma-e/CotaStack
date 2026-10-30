"""Data models for CotaStack tolerance chain calculations."""

from dataclasses import dataclass, field
from typing import Literal
import uuid


@dataclass(slots=True)
class Item:
    """Represents a single dimension/link in a 1D tolerance chain."""
    name: str
    nominal: float
    es: float
    ei: float
    orientation: Literal[1, -1] = 1
    material: str = "Acier"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if self.es < self.ei:
            raise ValueError("es must be >= ei")
        if self.nominal < 0:
            raise ValueError("nominal must be >= 0")
        if self.orientation not in (1, -1):
            raise ValueError("orientation must be 1 or -1")

    @property
    def upper_limit(self) -> float:
        return self.nominal + self.es

    @property
    def lower_limit(self) -> float:
        return self.nominal + self.ei

    @property
    def IT(self) -> float:
        return self.es - self.ei

    @property
    def L_moy(self) -> float:
        return self.nominal + (self.es + self.ei) / 2


@dataclass(slots=True)
class ChainResult:
    """Result of a tolerance chain calculation."""
    nominal: float
    mean: float
    worst_case_minus: float
    worst_case_plus: float
    rss_minus: float
    rss_plus: float
    items: list[Item]
    pareto: list[dict]
    compliance: dict
    target_min: float | None = None
    target_max: float | None = None