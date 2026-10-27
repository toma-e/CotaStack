"""Calculator engine for 1D tolerance chain analysis."""

import math
from backend.models import Item, ChainResult


class ChainCalculator:
    """Performs worst-case and RSS (Root Sum Square) tolerance analysis."""

    def __init__(self, items: list[Item]) -> None:
        self.items = items

    def calculate_worst_case(self) -> tuple[float, float]:
        """Calculate worst-case (arithmetic) tolerance stack-up.
        
        Returns:
            Tuple of (minus_tolerance, plus_tolerance) relative to nominal.
        """
        total_minus = sum(item.tolerance_minus for item in self.items)
        total_plus = sum(item.tolerance_plus for item in self.items)
        return total_minus, total_plus

    def calculate_rss(self) -> tuple[float, float]:
        """Calculate statistical (RSS) tolerance stack-up.
        
        Assumes normal distribution and independence.
        Returns:
            Tuple of (minus_tolerance, plus_tolerance) relative to nominal.
        """
        rss_minus = math.sqrt(sum(item.tolerance_minus ** 2 for item in self.items))
        rss_plus = math.sqrt(sum(item.tolerance_plus ** 2 for item in self.items))
        return -rss_minus, rss_plus

    def calculate(self) -> ChainResult:
        """Run full calculation and return structured result."""
        nominal = sum(item.nominal for item in self.items)
        wc_minus, wc_plus = self.calculate_worst_case()
        rss_minus, rss_plus = self.calculate_rss()
        return ChainResult(
            nominal=nominal,
            worst_case_minus=wc_minus,
            worst_case_plus=wc_plus,
            rss_minus=rss_minus,
            rss_plus=rss_plus,
            items=self.items,
        )