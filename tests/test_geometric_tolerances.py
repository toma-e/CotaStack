"""Unit tests for ISO GPS geometric tolerances and MMR (backend.geometric_tolerances)."""

import pytest
from backend.geometric_tolerances import (
    GeometricSpec,
    calculate_mms_lms,
    calculate_virtual_condition,
    evaluate_geometric_spec,
    verify_assembly_interface,
)


def approx(val: float, expected: float, tol: float = 1e-5) -> bool:
    return abs(val - expected) < tol


class TestMmsLmsCalculation:
    def test_shaft_mms_lms(self):
        # 20 h7: es = 0, ei = -0.021 -> d_max = 20.0, d_min = 19.979
        mms, lms = calculate_mms_lms("arbre", 20.0, 0.0, -0.021)
        assert approx(mms, 20.0)
        assert approx(lms, 19.979)

    def test_hole_mms_lms(self):
        # 20 H7: es = +0.021, ei = 0 -> D_min = 20.0, D_max = 20.021
        mms, lms = calculate_mms_lms("alesage", 20.0, 0.021, 0.0)
        assert approx(mms, 20.0)
        assert approx(lms, 20.021)

    def test_plane_mms_lms(self):
        mms, lms = calculate_mms_lms("plan", 50.0, 0.1, -0.1)
        assert approx(mms, 50.0)
        assert approx(lms, 50.0)

    def test_invalid_nominal(self):
        with pytest.raises(ValueError, match="cote nominale doit être > 0"):
            calculate_mms_lms("arbre", 0.0, 0.0, -0.02)
        with pytest.raises(ValueError, match="cote nominale doit être > 0"):
            calculate_mms_lms("arbre", -10.0, 0.0, -0.02)

    def test_invalid_es_ei(self):
        with pytest.raises(ValueError, match="es .* doit être >= ei"):
            calculate_mms_lms("arbre", 20.0, -0.05, -0.02)


class TestVirtualCondition:
    def test_shaft_vc(self):
        # Shaft 20 h7 (d_max = 20.0), t0 = 0.05 -> Vc = 20.05
        vc = calculate_virtual_condition("arbre", 20.0, 0.0, -0.021, 0.05)
        assert approx(vc, 20.05)

    def test_hole_vc(self):
        # Hole 20 H7 (D_min = 20.0), t0 = 0.05 -> Vc = 19.95
        vc = calculate_virtual_condition("alesage", 20.0, 0.021, 0.0, 0.05)
        assert approx(vc, 19.95)

    def test_plane_vc(self):
        vc = calculate_virtual_condition("plan", 30.0, 0.1, -0.1, 0.04)
        assert approx(vc, 30.04)

    def test_negative_base_tolerance(self):
        with pytest.raises(ValueError, match="tolérance géométrique de base doit être >= 0"):
            calculate_virtual_condition("arbre", 20.0, 0.0, -0.02, -0.01)


class TestEvaluateGeometricSpec:
    def test_shaft_mmr_at_mms(self):
        spec = GeometricSpec(
            name="Goupille Ø20",
            feature_type="arbre",
            tolerance_type="localisation",
            nominal_size=20.0,
            es=0.0,
            ei=-0.020,
            base_tolerance=0.050,
            mmr=True,
        )
        res = evaluate_geometric_spec(spec)
        assert approx(res.mms, 20.0)
        assert approx(res.lms, 19.980)
        assert approx(res.max_bonus, 0.020)
        assert approx(res.virtual_condition, 20.050)
        assert approx(res.actual_bonus, 0.0)
        assert approx(res.total_geometric_tolerance, 0.050)
        assert approx(res.equivalent_1d_it, 0.050)
        assert "Au pire des cas matière" in res.explanation

    def test_shaft_mmr_at_lms(self):
        spec = GeometricSpec(
            name="Goupille Ø20",
            feature_type="arbre",
            tolerance_type="localisation",
            nominal_size=20.0,
            es=0.0,
            ei=-0.020,
            base_tolerance=0.050,
            mmr=True,
        )
        res = evaluate_geometric_spec(spec, actual_size=19.980)
        assert approx(res.actual_bonus, 0.020)
        assert approx(res.total_geometric_tolerance, 0.070)
        assert approx(res.equivalent_1d_it, 0.070)

    def test_hole_mmr_at_actual(self):
        spec = GeometricSpec(
            name="Alésage Ø20",
            feature_type="alesage",
            tolerance_type="perpendicularite",
            nominal_size=20.0,
            es=0.025,
            ei=0.0,
            base_tolerance=0.040,
            mmr=True,
        )
        # Evaluated at nominal + 0.010 -> bonus = 0.010 - 0.0 = 0.010
        res = evaluate_geometric_spec(spec, actual_size=20.010)
        assert approx(res.mms, 20.0)
        assert approx(res.lms, 20.025)
        assert approx(res.max_bonus, 0.025)
        assert approx(res.virtual_condition, 19.960)
        assert approx(res.actual_bonus, 0.010)
        assert approx(res.total_geometric_tolerance, 0.050)

    def test_spec_without_mmr_rfs(self):
        spec = GeometricSpec(
            name="Axe haute précision",
            feature_type="arbre",
            tolerance_type="coaxialite",
            nominal_size=15.0,
            es=0.0,
            ei=-0.015,
            base_tolerance=0.020,
            mmr=False,
        )
        res = evaluate_geometric_spec(spec, actual_size=14.985)
        assert approx(res.max_bonus, 0.0)
        assert approx(res.actual_bonus, 0.0)
        assert approx(res.total_geometric_tolerance, 0.020)
        assert "RFS" in res.explanation

    def test_plane_with_mmr_ignored(self):
        spec = GeometricSpec(
            name="Face d'appui",
            feature_type="plan",
            tolerance_type="parallelisme",
            nominal_size=40.0,
            es=0.1,
            ei=-0.1,
            base_tolerance=0.030,
            mmr=True,
        )
        res = evaluate_geometric_spec(spec)
        assert approx(res.max_bonus, 0.0)
        assert approx(res.actual_bonus, 0.0)

    def test_negative_base_tolerance_raises(self):
        spec = GeometricSpec(
            name="Invalide",
            feature_type="arbre",
            tolerance_type="symetrie",
            nominal_size=10.0,
            es=0.0,
            ei=-0.01,
            base_tolerance=-0.05,
        )
        with pytest.raises(ValueError, match="tolérance de base doit être >= 0"):
            evaluate_geometric_spec(spec)


class TestAssemblyInterface:
    def test_guaranteed_assemblability(self):
        # Hole D_min = 20.0, t0 = 0.02 -> Vc_hole = 19.98
        hole = GeometricSpec(
            name="Logement",
            feature_type="alesage",
            tolerance_type="localisation",
            nominal_size=20.0,
            es=0.030,
            ei=0.0,
            base_tolerance=0.020,
        )
        # Shaft d_max = 19.95, t0 = 0.02 -> Vc_shaft = 19.97
        shaft = GeometricSpec(
            name="Pion",
            feature_type="arbre",
            tolerance_type="localisation",
            nominal_size=20.0,
            es=-0.050,
            ei=-0.070,
            base_tolerance=0.020,
        )
        res = verify_assembly_interface(hole, shaft)
        assert res.is_assemblable is True
        assert approx(res.hole_vc, 19.980)
        assert approx(res.shaft_vc, 19.970)
        assert approx(res.guaranteed_min_clearance, 0.010)
        assert "✅ Assemblage 100% garanti" in res.verdict

    def test_interference_risk(self):
        # Hole D_min = 20.0, t0 = 0.05 -> Vc_hole = 19.95
        hole = GeometricSpec(
            name="Logement serré",
            feature_type="alesage",
            tolerance_type="localisation",
            nominal_size=20.0,
            es=0.020,
            ei=0.0,
            base_tolerance=0.050,
        )
        # Shaft d_max = 20.0, t0 = 0.02 -> Vc_shaft = 20.02
        shaft = GeometricSpec(
            name="Pion",
            feature_type="arbre",
            tolerance_type="localisation",
            nominal_size=20.0,
            es=0.0,
            ei=-0.020,
            base_tolerance=0.020,
        )
        res = verify_assembly_interface(hole, shaft)
        assert res.is_assemblable is False
        assert approx(res.hole_vc, 19.950)
        assert approx(res.shaft_vc, 20.020)
        assert approx(res.guaranteed_min_clearance, -0.070)
        assert "❌ Risque de collision" in res.verdict

    def test_invalid_feature_types(self):
        hole = GeometricSpec("H", "arbre", "localisation", 20.0, 0.0, -0.02, 0.02)
        shaft = GeometricSpec("S", "arbre", "localisation", 20.0, 0.0, -0.02, 0.02)
        with pytest.raises(ValueError, match="hole_spec doit avoir feature_type='alesage'"):
            verify_assembly_interface(hole, shaft)

        hole_valid = GeometricSpec("H", "alesage", "localisation", 20.0, 0.02, 0.0, 0.02)
        shaft_invalid = GeometricSpec("S", "alesage", "localisation", 20.0, 0.02, 0.0, 0.02)
        with pytest.raises(ValueError, match="shaft_spec doit avoir feature_type='arbre'"):
            verify_assembly_interface(hole_valid, shaft_invalid)
