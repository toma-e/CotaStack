"""Test suite for ChainCalculator - CotaStack tolerance chain engine."""

import math
import pytest
from backend.models import Item
from backend.calculator import ChainCalculator


def approx_equal(a: float, b: float, rel_tol: float = 1e-9) -> bool:
    return abs(a - b) <= rel_tol * max(abs(a), abs(b), 1.0)


class TestItemValidation:
    """Tests for Item dataclass validation."""

    def test_valid_item_creation(self) -> None:
        item = Item(name="Cote A", nominal=10.0, ei=-0.1, es=0.1)
        assert item.nominal == 10.0
        assert item.ei == -0.1
        assert item.es == 0.1
        assert item.orientation == 1
        assert item.id is not None

    def test_invalid_es_lt_ei(self) -> None:
        with pytest.raises(ValueError, match="es must be >= ei"):
            Item(name="Test", nominal=10.0, ei=0.1, es=-0.1)

    def test_invalid_negative_nominal(self) -> None:
        with pytest.raises(ValueError, match="nominal must be >= 0"):
            Item(name="Test", nominal=-1.0, ei=-0.1, es=0.1)

    def test_invalid_orientation(self) -> None:
        with pytest.raises(ValueError, match="orientation must be 1 or -1"):
            Item(name="Test", nominal=10.0, ei=-0.1, es=0.1, orientation=0)

    def test_item_properties(self) -> None:
        item = Item(name="Test", nominal=20.0, ei=-0.05, es=0.1)
        assert approx_equal(item.upper_limit, 20.1)
        assert approx_equal(item.lower_limit, 19.95)
        assert approx_equal(item.IT, 0.15)
        assert approx_equal(item.L_moy, 20.025)


class TestChainCalculator:
    """Tests for ChainCalculator calculation methods."""

    def setup_method(self) -> None:
        self.items = [
            Item(name="Maillon 1", nominal=10.0, ei=-0.1, es=0.1, orientation=1),
            Item(name="Maillon 2", nominal=20.0, ei=-0.05, es=0.05, orientation=1),
            Item(name="Maillon 3", nominal=5.0, ei=-0.2, es=0.2, orientation=1),
        ]
        self.calculator = ChainCalculator(self.items)

    def test_calculate_worst_case(self) -> None:
        """Test WC returns absolute limits J_min, J_max."""
        j_min, j_max = self.calculator.calculate_worst_case()
        # Nominal = 10 + 20 + 5 = 35
        # J_min = 35 + (-0.1) + (-0.05) + (-0.2) = 34.65
        # J_max = 35 + 0.1 + 0.05 + 0.2 = 35.35
        assert approx_equal(j_min, 34.65)
        assert approx_equal(j_max, 35.35)

    def test_calculate_rss(self) -> None:
        """Test RSS returns absolute limits J_min, J_max (IT_total/2 range)."""
        j_min, j_max = self.calculator.calculate_rss()
        # Nominal = 35, Mean = 35 (symmetric tolerances)
        # IT values: 0.2, 0.1, 0.4
        # IT_total,RSS = sqrt(0.2^2 + 0.1^2 + 0.4^2) = sqrt(0.04 + 0.01 + 0.16) = sqrt(0.21) ≈ 0.4583
        # Half-range = IT_total,RSS / 2 ≈ 0.2291
        # J_min = 35 - 0.2291 = 34.7709, J_max = 35 + 0.2291 = 35.2291
        it_values = [0.2, 0.1, 0.4]
        it_total_rss = math.sqrt(sum(it**2 for it in it_values))
        half_range = it_total_rss / 2
        assert approx_equal(j_min, 35 - half_range)
        assert approx_equal(j_max, 35 + half_range)

    def test_calculate_full_result(self) -> None:
        result = self.calculator.calculate()
        assert approx_equal(result.nominal, 35.0)
        assert approx_equal(result.mean, 35.0)
        assert approx_equal(result.worst_case_minus, 34.65)
        assert approx_equal(result.worst_case_plus, 35.35)
        assert len(result.items) == 3
        assert result.pareto is not None
        assert result.compliance is not None

    def test_single_item_chain(self) -> None:
        single = [Item(name="Solo", nominal=50.0, ei=-0.02, es=0.03, orientation=1)]
        calc = ChainCalculator(single)
        result = calc.calculate()
        assert result.nominal == 50.0
        assert result.mean == 50.005
        assert result.worst_case_minus == 49.98
        assert result.worst_case_plus == 50.03
        # RSS: IT = 0.05, IT_total,RSS = 0.05, half-range = 0.025
        # For single item, RSS == WC
        assert approx_equal(result.rss_minus, 49.98)
        assert approx_equal(result.rss_plus, 50.03)

    def test_orientation_negative_items(self) -> None:
        """Test that orientation attribute is used in calculations."""
        items = [
            Item(name="Pos", nominal=10.0, ei=-0.1, es=0.1, orientation=1),
            Item(name="Neg", nominal=5.0, ei=-0.05, es=0.05, orientation=-1),
        ]
        calc = ChainCalculator(items)
        result = calc.calculate()
        # Nominal: 10*1 + 5*(-1) = 5
        assert result.nominal == 5.0
        # Mean: 10*(1+(0.1-0.1)/2) + 5*(-1+(0.05-0.05)/2) = 10 - 5 = 5
        assert result.mean == 5.0
        # WC: J_min = 5 + 1*(-0.1) + (-1)*0.05 = 5 - 0.1 - 0.05 = 4.85
        #     J_max = 5 + 1*0.1 + (-1)*(-0.05) = 5 + 0.1 + 0.05 = 5.15
        assert approx_equal(result.worst_case_minus, 4.85)
        assert approx_equal(result.worst_case_plus, 5.15)
        # RSS: IT = 0.2, 0.1 -> IT_total = sqrt(0.04+0.01) = sqrt(0.05) ≈ 0.2236, half = 0.1118
        # J_min = 5 - 0.1118 = 4.8882, J_max = 5 + 0.1118 = 5.1118
        it_total = math.sqrt(0.2**2 + 0.1**2)
        half = it_total / 2
        assert approx_equal(result.rss_minus, 5 - half)
        assert approx_equal(result.rss_plus, 5 + half)


class TestEdgeCases:
    """Edge case and regression tests."""

    def test_zero_tolerance(self) -> None:
        items = [Item(name="Exact", nominal=10.0, ei=0.0, es=0.0, orientation=1)]
        calc = ChainCalculator(items)
        result = calc.calculate()
        assert result.worst_case_minus == 10.0
        assert result.worst_case_plus == 10.0
        assert result.rss_minus == 10.0
        assert result.rss_plus == 10.0

    def test_asymmetric_tolerances(self) -> None:
        items = [Item(name="Asym", nominal=10.0, ei=-0.2, es=0.05, orientation=1)]
        calc = ChainCalculator(items)
        result = calc.calculate()
        # Nominal = 10, Mean = 10 + (-0.2+0.05)/2 = 9.925
        # WC: J_min = 10 - 0.2 = 9.8, J_max = 10 + 0.05 = 10.05
        assert result.worst_case_minus == 9.8
        assert result.worst_case_plus == 10.05
        # RSS: IT = 0.25, IT_total,RSS = 0.25, half-range = 0.125
        # For single item, RSS == WC
        assert result.rss_minus == 9.8
        assert result.rss_plus == 10.05

    def test_hole_and_shaft_tolerances(self) -> None:
        """Test with both positive (hole) and negative (shaft) deviations."""
        # Hole H7: ei=0, es=+0.021 (for 10mm)
        # Shaft g6: ei=-0.014, es=-0.005 (for 10mm)
        items = [
            Item(name="Hole", nominal=10.0, ei=0.0, es=0.021, orientation=1),
            Item(name="Shaft", nominal=10.0, ei=-0.014, es=-0.005, orientation=-1),
        ]
        calc = ChainCalculator(items)
        result = calc.calculate()
        # Nominal: 10*1 + 10*(-1) = 0
        assert result.nominal == 0.0
        # Mean: 10*(1+(0+0.021)/2) + 10*(-1+(-0.014-0.005)/2) = 10.0105 - 9.9905 = 0.02
        assert approx_equal(result.mean, 0.02)
        # WC: J_min = 0 + 1*0 + (-1)*(-0.005) = 0.005
        #     J_max = 0 + 1*0.021 + (-1)*(-0.014) = 0.035
        assert approx_equal(result.worst_case_minus, 0.005)
        assert approx_equal(result.worst_case_plus, 0.035)
        # RSS: IT = 0.021, 0.009 -> IT_total = sqrt(0.021^2 + 0.009^2) = sqrt(0.000441 + 0.000081) = sqrt(0.000522) ≈ 0.02285
        # half-range = 0.0114
        # J_min = 0.02 - 0.0114 = 0.0086, J_max = 0.02 + 0.0114 = 0.0314
        it_total = math.sqrt(0.021**2 + 0.009**2)
        half = it_total / 2
        assert approx_equal(result.rss_minus, 0.02 - half)
        assert approx_equal(result.rss_plus, 0.02 + half)


class TestPareto:
    """Tests for Pareto contribution analysis."""

    def test_pareto_sum_equals_100(self) -> None:
        items = [
            Item(name="A", nominal=10.0, ei=-0.1, es=0.1, orientation=1),
            Item(name="B", nominal=20.0, ei=-0.2, es=0.2, orientation=1),
            Item(name="C", nominal=5.0, ei=-0.05, es=0.05, orientation=1),
        ]
        calc = ChainCalculator(items)
        result = calc.calculate()
        total_pct = sum(p["contribution_pct"] for p in result.pareto)
        assert approx_equal(total_pct, 100.0)

    def test_pareto_sorted_descending(self) -> None:
        items = [
            Item(name="A", nominal=10.0, ei=-0.1, es=0.1, orientation=1),
            Item(name="B", nominal=20.0, ei=-0.2, es=0.2, orientation=1),
            Item(name="C", nominal=5.0, ei=-0.05, es=0.05, orientation=1),
        ]
        calc = ChainCalculator(items)
        result = calc.calculate()
        # B has largest IT (0.4), then A (0.2), then C (0.1)
        assert result.pareto[0]["name"] == "B"
        assert result.pareto[1]["name"] == "A"
        assert result.pareto[2]["name"] == "C"


class TestCompliance:
    """Tests for compliance checking."""

    def test_compliance_within_targets_wc(self) -> None:
        """WC compliant when targets are wide enough."""
        items = [Item(name="Test", nominal=10.0, ei=-0.1, es=0.1, orientation=1)]
        calc = ChainCalculator(items, target_min=9.8, target_max=10.2)
        result = calc.calculate()
        # WC: J_min=9.9, J_max=10.1 -> within [9.8, 10.2]
        assert result.compliance["wc_compliant"] is True
        # RSS: same as WC for single item
        assert result.compliance["rss_compliant"] is True

    def test_compliance_outside_targets_wc(self) -> None:
        items = [Item(name="Test", nominal=10.0, ei=-0.2, es=0.2, orientation=1)]
        calc = ChainCalculator(items, target_min=9.9, target_max=10.1)
        result = calc.calculate()
        # WC: J_min=9.8, J_max=10.2 -> outside [9.9, 10.1]
        assert result.compliance["wc_compliant"] is False
        # RSS: same as WC for single item
        assert result.compliance["rss_compliant"] is False

    def test_compliance_rss_tighter_than_wc(self) -> None:
        """RSS is tighter than WC for multiple items."""
        # 4 items, each nominal=10, ei=-0.2, es=0.2
        items = [
            Item(name="A", nominal=10.0, ei=-0.2, es=0.2, orientation=1),
            Item(name="B", nominal=10.0, ei=-0.2, es=0.2, orientation=1),
            Item(name="C", nominal=10.0, ei=-0.2, es=0.2, orientation=1),
            Item(name="D", nominal=10.0, ei=-0.2, es=0.2, orientation=1),
        ]
        # WC: IT_total = 1.6, J_min=39.2, J_max=40.8
        # RSS: IT_total = sqrt(4*0.4^2)=0.8, half-range = 0.4, J_min=39.6, J_max=40.4
        calc = ChainCalculator(items, target_min=39.5, target_max=40.5)
        result = calc.calculate()
        # WC outside (39.2 < 39.5), RSS inside (39.6 > 39.5 and 40.4 < 40.5)
        assert result.compliance["wc_compliant"] is False
        assert result.compliance["rss_compliant"] is True

    def test_compliance_one_sided_targets(self) -> None:
        items = [Item(name="Test", nominal=10.0, ei=-0.1, es=0.1, orientation=1)]
        calc_min = ChainCalculator(items, target_min=9.95)
        calc_max = ChainCalculator(items, target_max=10.05)
        result_min = calc_min.calculate()
        result_max = calc_max.calculate()
        # WC: J_min=9.9, J_max=10.1
        assert result_min.compliance["wc_compliant"] is False  # J_min=9.9 < 9.95
        assert result_max.compliance["wc_compliant"] is False  # J_max=10.1 > 10.05