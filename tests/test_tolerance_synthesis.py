"""Test suite for inverse tolerance allocation (backend/tolerance_synthesis.py)."""

import pytest
from backend.models import Item
from backend.tolerance_synthesis import (
    _compute_iso_factor,
    allocate_tolerances,
)


def approx_equal(a: float, b: float, rel_tol: float = 1e-4) -> bool:
    return abs(a - b) <= rel_tol * max(abs(a), abs(b), 1.0)


class TestToleranceSynthesis:
    """Tests for inverse tolerance allocation algorithms."""

    def setup_method(self) -> None:
        self.items = [
            Item(name="Piece A", nominal=50.0, ei=-0.1, es=0.1, orientation=1),   # IT=0.2
            Item(name="Piece B", nominal=30.0, ei=-0.05, es=0.05, orientation=-1), # IT=0.1
            Item(name="Piece C", nominal=20.0, ei=-0.05, es=0.05, orientation=-1), # IT=0.1
        ]
        # Current WC = 0.2 + 0.1 + 0.1 = 0.4
        # Current RSS = sqrt(0.04 + 0.01 + 0.01) = sqrt(0.06) ≈ 0.2449

    def test_validation_errors(self) -> None:
        with pytest.raises(ValueError, match="ne peut pas être vide"):
            allocate_tolerances([], target_it=0.2)
        with pytest.raises(ValueError, match="doit être strictement positif"):
            allocate_tolerances(self.items, target_it=-0.1)
        with pytest.raises(ValueError, match="Méthode d'allocation inconnue"):
            allocate_tolerances(self.items, target_it=0.2, method="magique")  # type: ignore
        with pytest.raises(ValueError, match="Mode de cumul inconnu"):
            allocate_tolerances(self.items, target_it=0.2, mode="other")  # type: ignore

    def test_proportional_wc(self) -> None:
        # Request tighter target_it = 0.2 (reduction by 50%)
        res = allocate_tolerances(self.items, target_it=0.2, mode="wc", method="proportionnelle")
        assert approx_equal(res.total_it_wc, 0.2)
        assert approx_equal(res.achieved_it, 0.2)

        # Individual ITs should be scaled by 0.5:
        # A: 0.1, B: 0.05, C: 0.05
        assert approx_equal(res.allocated_links[0].new_it, 0.1)
        assert approx_equal(res.allocated_links[1].new_it, 0.05)
        assert approx_equal(res.allocated_links[2].new_it, 0.05)

        # Check symmetric interval centering
        for link in res.allocated_links:
            assert approx_equal(link.new_es - link.new_ei, link.new_it)

    def test_proportional_rss(self) -> None:
        # Target RSS = 0.15
        res = allocate_tolerances(self.items, target_it=0.15, mode="rss", method="proportionnelle")
        assert approx_equal(res.total_it_rss, 0.15)
        assert approx_equal(res.achieved_it, 0.15)
        # WC should be larger than RSS target
        assert res.total_it_wc > res.total_it_rss

    def test_cost_minimization_weights(self) -> None:
        # If Piece A has high cost weight (difficult to machine, e.g. 4.0),
        # Piece B is easy (0.25), Piece C standard (1.0).
        # Piece A should receive significantly larger tolerance than B.
        # Test negative weight fallback on Piece C (<= 0 -> 1.0)
        weights = {"Piece A": 4.0, "Piece B": 0.25, "Piece C": -2.0}
        res = allocate_tolerances(self.items, target_it=0.3, mode="wc", method="cout_usinage", cost_weights=weights)
        assert approx_equal(res.total_it_wc, 0.3)
        assert res.allocated_links[0].new_it > res.allocated_links[1].new_it
        assert res.allocated_links[0].new_it > res.allocated_links[2].new_it

    def test_iso_grade_method(self) -> None:
        # ISO sizing factor: larger nominal size gets larger IT
        # Piece A (50mm) > Piece B (30mm) > Piece C (20mm)
        res = allocate_tolerances(self.items, target_it=0.3, mode="wc", method="degré_iso")
        assert approx_equal(res.total_it_wc, 0.3)
        it_a = res.allocated_links[0].new_it
        it_b = res.allocated_links[1].new_it
        it_c = res.allocated_links[2].new_it
        assert it_a > it_b > it_c

    def test_zero_base_it_fallback(self) -> None:
        # Test item with IT=0
        items_zero = [
            Item(name="Z1", nominal=10.0, ei=0.0, es=0.0),
            Item(name="Z2", nominal=10.0, ei=0.0, es=0.0),
        ]
        res = allocate_tolerances(items_zero, target_it=0.1, mode="wc", method="proportionnelle")
        assert approx_equal(res.total_it_wc, 0.1)
        assert approx_equal(res.allocated_links[0].new_it, 0.05)
        assert approx_equal(res.allocated_links[1].new_it, 0.05)

    def test_iso_factor_calculation(self) -> None:
        factor_small = _compute_iso_factor(1.0)
        factor_large = _compute_iso_factor(100.0)
        assert factor_small > 0
        assert factor_large > factor_small
