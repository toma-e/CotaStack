"""Test suite for thermal expansion module (backend/thermal.py)."""

import pytest
from backend.models import Item
from backend.thermal import (
    get_available_materials,
    get_material_alpha,
    calculate_thermal_expansion,
    calculate_thermal_chain,
    simulate_thermal_sensitivity,
)


def approx_equal(a: float, b: float, rel_tol: float = 1e-6) -> bool:
    return abs(a - b) <= rel_tol * max(abs(a), abs(b), 1.0)


class TestThermalCatalog:
    """Tests for material thermal coefficients catalog."""

    def test_available_materials(self) -> None:
        mats = get_available_materials()
        assert "Acier (standard)" in mats
        assert "Aluminium (alliage 6000/7000)" in mats
        assert "Polymère POM (Delrin / Acétal)" in mats

    def test_alpha_exact_names(self) -> None:
        assert approx_equal(get_material_alpha("Acier (standard)"), 11.5e-6)
        assert approx_equal(get_material_alpha("Aluminium (alliage 6000/7000)"), 23.0e-6)

    def test_alpha_aliases(self) -> None:
        assert approx_equal(get_material_alpha("acier"), 11.5e-6)
        assert approx_equal(get_material_alpha("alu"), 23.0e-6)
        assert approx_equal(get_material_alpha("inox"), 16.0e-6)
        assert approx_equal(get_material_alpha("delrin"), 110.0e-6)

    def test_unknown_material(self) -> None:
        with pytest.raises(ValueError, match="Matériau inconnu"):
            get_material_alpha("Vibranium")


class TestThermalExpansion:
    """Tests for linear expansion calculations."""

    def test_single_dimension_expansion(self) -> None:
        # 100mm Alu heated from 20°C to 80°C (delta_T = 60°C)
        # delta_L = 100 * 23e-6 * 60 = 0.138 mm
        delta_l = calculate_thermal_expansion(100.0, "alu", t_service=80.0, t_ref=20.0)
        assert approx_equal(delta_l, 0.138)

    def test_cooling_contraction(self) -> None:
        # 50mm Steel cooled from 20°C to -20°C (delta_T = -40°C)
        # delta_L = 50 * 11.5e-6 * (-40) = -0.023 mm
        delta_l = calculate_thermal_expansion(50.0, "acier", t_service=-20.0, t_ref=20.0)
        assert approx_equal(delta_l, -0.023)

    def test_zero_delta_t(self) -> None:
        assert calculate_thermal_expansion(100.0, "acier", t_service=20.0, t_ref=20.0) == 0.0


class TestThermalChain:
    """Tests for full tolerance chain calculations with thermal effect."""

    def test_differential_assembly(self) -> None:
        # Carter Alu: 100 mm (+), ES=+0.1, EI=-0.1
        # Arbre Acier: 98 mm (-), ES=+0.05, EI=-0.05
        # Nominal cold (20°C) = 100 - 98 = 2.0 mm
        # Delta T = 60°C (80°C service)
        # delta_L(Alu) = 100 * 23e-6 * 60 = 0.138 mm
        # delta_L(Acier) = 98 * 11.5e-6 * 60 = 0.06762 mm
        # Nominal hot = 100.138 - 98.06762 = 2.07038 mm
        # delta_J_nom = +0.07038 mm
        items = [
            Item(name="Carter Alu", nominal=100.0, ei=-0.1, es=0.1, orientation=1, material="Aluminium (alliage 6000/7000)"),
            Item(name="Arbre Acier", nominal=98.0, ei=-0.05, es=0.05, orientation=-1, material="Acier (standard)"),
        ]
        res = calculate_thermal_chain(items, t_service=80.0, t_ref=20.0)

        assert approx_equal(res.nominal_at_t, 2.07038)
        assert approx_equal(res.delta_j_nominal, 0.07038)
        assert approx_equal(res.delta_t, 60.0)
        assert len(res.items_detail) == 2
        assert res.worst_case_minus_at_t < res.worst_case_plus_at_t
        assert res.rss_minus_at_t < res.rss_plus_at_t

    def test_default_material_fallback(self) -> None:
        # Item created with material="" should fallback to Steel
        item = Item(name="Test", nominal=100.0, ei=-0.1, es=0.1, orientation=1, material="")
        res = calculate_thermal_chain([item], t_service=40.0)
        assert approx_equal(res.delta_j_nominal, 100.0 * 11.5e-6 * 20.0)


class TestThermalSensitivity:
    """Tests for temperature range sensitivity simulation."""

    def test_sensitivity_curve_generation(self) -> None:
        items = [
            Item(name="Cote A", nominal=50.0, ei=-0.05, es=0.05, orientation=1, material="Acier (standard)"),
            Item(name="Cote B", nominal=30.0, ei=-0.05, es=0.05, orientation=-1, material="Aluminium (alliage 6000/7000)"),
        ]
        curve = simulate_thermal_sensitivity(items, t_min=0.0, t_max=100.0, num_points=11)
        assert len(curve) == 11
        assert curve[0]["temperature"] == 0.0
        assert curve[-1]["temperature"] == 100.0
        # Check monotonic behavior
        assert "wc_min" in curve[0]
        assert "rss_max" in curve[0]

    def test_invalid_temperature_bounds(self) -> None:
        items = [Item(name="Test", nominal=10.0, ei=-0.1, es=0.1)]
        with pytest.raises(ValueError, match="must be < t_max"):
            simulate_thermal_sensitivity(items, t_min=100.0, t_max=20.0)
