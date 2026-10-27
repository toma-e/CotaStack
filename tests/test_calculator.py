"""Test suite for ChainCalculator - CotaStack tolerance chain engine."""

import pytest
from backend.models import Item
from backend.calculator import ChainCalculator


def approx_equal(a: float, b: float, rel_tol: float = 1e-9) -> bool:
    return abs(a - b) <= rel_tol * max(abs(a), abs(b), 1.0)


class TestItemValidation:
    """Tests for Item dataclass validation."""

    def test_valid_item_creation(self) -> None:
        item = Item(name="Cote A", nominal=10.0, tolerance_minus=-0.1, tolerance_plus=0.1)
        assert item.nominal == 10.0
        assert item.tolerance_minus == -0.1
        assert item.tolerance_plus == 0.1

    def test_invalid_positive_tolerance_minus(self) -> None:
        with pytest.raises(ValueError, match="tolerance_minus must be <= 0"):
            Item(name="Test", nominal=10.0, tolerance_minus=0.1, tolerance_plus=0.1)

    def test_invalid_negative_tolerance_plus(self) -> None:
        with pytest.raises(ValueError, match="tolerance_plus must be >= 0"):
            Item(name="Test", nominal=10.0, tolerance_minus=-0.1, tolerance_plus=-0.1)

    def test_invalid_negative_nominal(self) -> None:
        with pytest.raises(ValueError, match="nominal must be >= 0"):
            Item(name="Test", nominal=-1.0, tolerance_minus=-0.1, tolerance_plus=0.1)

    def test_item_properties(self) -> None:
        item = Item(name="Test", nominal=20.0, tolerance_minus=-0.05, tolerance_plus=0.1)
        assert approx_equal(item.upper_limit, 20.1)
        assert approx_equal(item.lower_limit, 19.95)
        assert approx_equal(item.tolerance_total, 0.15)


class TestChainCalculator:
    """Tests for ChainCalculator calculation methods."""

    def setup_method(self) -> None:
        self.items = [
            Item(name="Maillon 1", nominal=10.0, tolerance_minus=-0.1, tolerance_plus=0.1),
            Item(name="Maillon 2", nominal=20.0, tolerance_minus=-0.05, tolerance_plus=0.05),
            Item(name="Maillon 3", nominal=5.0, tolerance_minus=-0.2, tolerance_plus=0.2),
        ]
        self.calculator = ChainCalculator(self.items)

    def test_calculate_worst_case(self) -> None:
        wc_minus, wc_plus = self.calculator.calculate_worst_case()
        assert approx_equal(wc_minus, -0.35)  # -0.1 + -0.05 + -0.2
        assert approx_equal(wc_plus, 0.35)   # 0.1 + 0.05 + 0.2

    def test_calculate_rss(self) -> None:
        rss_minus, rss_plus = self.calculator.calculate_rss()
        expected_rss = (0.1**2 + 0.05**2 + 0.2**2) ** 0.5  # sqrt(0.01 + 0.0025 + 0.04)
        assert abs(rss_minus + expected_rss) < 1e-10
        assert abs(rss_plus - expected_rss) < 1e-10

    def test_calculate_full_result(self) -> None:
        result = self.calculator.calculate()
        assert approx_equal(result.nominal, 35.0)  # 10 + 20 + 5
        assert approx_equal(result.worst_case_minus, -0.35)
        assert approx_equal(result.worst_case_plus, 0.35)
        assert len(result.items) == 3

    def test_single_item_chain(self) -> None:
        single = [Item(name="Solo", nominal=50.0, tolerance_minus=-0.02, tolerance_plus=0.03)]
        calc = ChainCalculator(single)
        result = calc.calculate()
        assert result.nominal == 50.0
        assert result.worst_case_minus == -0.02
        assert result.worst_case_plus == 0.03
        assert result.rss_minus == -0.02
        assert result.rss_plus == 0.03

    def test_direction_negative_items(self) -> None:
        """Test that direction attribute is stored (calculation logic TBD)."""
        items = [
            Item(name="Pos", nominal=10.0, tolerance_minus=-0.1, tolerance_plus=0.1, direction="positive"),
            Item(name="Neg", nominal=5.0, tolerance_minus=-0.05, tolerance_plus=0.05, direction="negative"),
        ]
        calc = ChainCalculator(items)
        result = calc.calculate()
        assert result.nominal == 15.0


class TestEdgeCases:
    """Edge case and regression tests."""

    def test_zero_tolerance(self) -> None:
        items = [Item(name="Exact", nominal=10.0, tolerance_minus=0.0, tolerance_plus=0.0)]
        calc = ChainCalculator(items)
        result = calc.calculate()
        assert result.worst_case_minus == 0.0
        assert result.worst_case_plus == 0.0
        assert result.rss_minus == 0.0
        assert result.rss_plus == 0.0

    def test_asymmetric_tolerances(self) -> None:
        items = [Item(name="Asym", nominal=10.0, tolerance_minus=-0.2, tolerance_plus=0.05)]
        calc = ChainCalculator(items)
        result = calc.calculate()
        assert result.worst_case_minus == -0.2
        assert result.worst_case_plus == 0.05
        assert result.rss_minus == -0.2
        assert result.rss_plus == 0.05