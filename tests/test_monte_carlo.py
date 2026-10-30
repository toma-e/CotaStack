"""Test suite for Monte Carlo simulation engine (backend/monte_carlo.py)."""

import pytest
import numpy as np
from backend.models import Item
from backend.monte_carlo import (
    _draw_item_samples,
    run_monte_carlo,
)


class TestDrawItemSamples:
    """Tests for individual dimension sampling."""

    def test_zero_tolerance(self) -> None:
        item = Item(name="Fixe", nominal=25.0, ei=0.0, es=0.0)
        samples = _draw_item_samples(item, num_simulations=500)
        assert len(samples) == 500
        assert np.all(samples == 25.0)

    def test_normal_distribution(self) -> None:
        # Nominal=50, ES=0.3, EI=-0.3 -> L_moy=50.0, IT=0.6, sigma=0.1
        item = Item(name="Norm", nominal=50.0, ei=-0.3, es=0.3)
        rng = np.random.default_rng(123)
        samples = _draw_item_samples(item, num_simulations=50_000, distribution="normale", rng=rng)
        assert abs(np.mean(samples) - 50.0) < 0.01
        assert abs(np.std(samples) - 0.1) < 0.01

    def test_uniform_distribution(self) -> None:
        item = Item(name="Unif", nominal=10.0, ei=-0.2, es=0.2)
        rng = np.random.default_rng(123)
        samples = _draw_item_samples(item, num_simulations=10_000, distribution="uniforme", rng=rng)
        assert np.all(samples >= 9.8)
        assert np.all(samples <= 10.2)
        assert abs(np.mean(samples) - 10.0) < 0.02

    def test_triangular_distribution(self) -> None:
        item = Item(name="Tri", nominal=10.0, ei=-0.1, es=0.2)
        rng = np.random.default_rng(123)
        samples = _draw_item_samples(item, num_simulations=10_000, distribution="triangulaire", rng=rng)
        assert np.all(samples >= 9.9)
        assert np.all(samples <= 10.2)

    def test_unknown_distribution(self) -> None:
        item = Item(name="Err", nominal=10.0, ei=-0.1, es=0.1)
        with pytest.raises(ValueError, match="Distribution inconnue"):
            _draw_item_samples(item, num_simulations=100, distribution="cauchy")  # type: ignore


class TestRunMonteCarlo:
    """Tests for full chain Monte Carlo simulation."""

    def setup_method(self) -> None:
        self.items = [
            Item(name="Carter", nominal=50.0, ei=-0.1, es=0.1, orientation=1),
            Item(name="Arbre", nominal=30.0, ei=-0.05, es=0.05, orientation=-1),
            Item(name="Bague", nominal=18.0, ei=-0.05, es=0.05, orientation=-1),
        ]
        # Theoretical cold nominal game = 50 - 30 - 18 = 2.0 mm

    def test_validation_errors(self) -> None:
        with pytest.raises(ValueError, match="ne peut pas être vide"):
            run_monte_carlo([])
        with pytest.raises(ValueError, match="doit être au moins de 100"):
            run_monte_carlo(self.items, num_simulations=50)

    def test_simulation_convergence(self) -> None:
        res = run_monte_carlo(self.items, num_simulations=50_000, seed=42)
        assert abs(res.mean - 2.0) < 0.005
        assert res.min_simulated < res.mean < res.max_simulated
        assert res.p001 < res.p50 < res.p999
        assert len(res.samples_summary) == 5000

    def test_compliance_and_ppm_zero(self) -> None:
        # Targets broad enough to have zero defects
        res = run_monte_carlo(self.items, num_simulations=20_000, target_min=1.5, target_max=2.5, seed=42)
        assert res.defect_count == 0
        assert res.defect_rate_pct == 0.0
        assert res.defect_ppm == 0.0
        assert res.cp is not None and res.cp > 1.33
        assert res.cpk is not None and res.cpk > 1.33

    def test_compliance_and_ppm_active(self) -> None:
        # Tight targets slicing into the distribution
        res = run_monte_carlo(self.items, num_simulations=20_000, target_min=1.98, target_max=2.02, seed=42)
        assert res.defect_count > 0
        assert res.defect_rate_pct > 0.0
        assert res.defect_ppm > 0.0
        assert res.cp is not None and res.cp < 1.0

    def test_custom_distributions_per_item(self) -> None:
        dists = {
            "Carter": "uniforme",
            "Arbre": "triangulaire",
            "Bague": "normale",
        }
        res = run_monte_carlo(self.items, num_simulations=10_000, distributions=dists, seed=42)
        assert abs(res.mean - 2.0) < 0.02

    def test_one_sided_targets(self) -> None:
        res_min_only = run_monte_carlo(self.items, num_simulations=5_000, target_min=1.95, seed=42)
        assert res_min_only.target_max is None
        assert res_min_only.cp is None
        assert res_min_only.cpk is None
