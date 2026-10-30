"""Test suite for ISO standards (ISO 286 and ISO 2768-1)."""

import pytest
from backend.iso_standards import (
    get_available_iso286_symbols,
    get_iso286_limits,
    parse_iso_fit,
    calculate_fit,
    get_iso2768_linear_tolerance,
    get_iso2768_broken_edges_tolerance,
    get_iso2768_angular_tolerance,
)


class TestISO286Limits:
    """Tests for ISO 286 lookup limits."""

    def test_available_symbols(self) -> None:
        symbols = get_available_iso286_symbols()
        assert "H7" in symbols["holes"]
        assert "g6" in symbols["shafts"]
        assert "p6" in symbols["shafts"]

    def test_h7_limits_known_sizes(self) -> None:
        # Step <= 3mm: IT7 = 10 µm
        assert get_iso286_limits(2.5, "H7") == (0.0, 0.010)
        # Step 18-30mm: IT7 = 21 µm
        assert get_iso286_limits(20.0, "H7") == (0.0, 0.021)
        # Step 30-50mm: IT7 = 25 µm
        assert get_iso286_limits(50.0, "H7") == (0.0, 0.025)

    def test_shaft_limits_known_sizes(self) -> None:
        # 20mm g6 (step 18-30): es = -7 µm, ei = -20 µm
        assert get_iso286_limits(20.0, "g6") == (-0.020, -0.007)
        # 20mm h6: es = 0, ei = -13 µm
        assert get_iso286_limits(20.0, "h6") == (-0.013, 0.0)
        # 20mm k6: es = +15 µm, ei = +2 µm
        assert get_iso286_limits(20.0, "k6") == (0.002, 0.015)
        # 20mm p6: es = +35 µm, ei = +22 µm
        assert get_iso286_limits(20.0, "p6") == (0.022, 0.035)

    def test_invalid_nominal(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            get_iso286_limits(0.0, "H7")
        with pytest.raises(ValueError, match="must be > 0"):
            get_iso286_limits(-10.0, "H7")
        with pytest.raises(ValueError, match="> 500 mm not supported"):
            get_iso286_limits(600.0, "H7")

    def test_unsupported_symbol(self) -> None:
        with pytest.raises(ValueError, match="Unsupported ISO 286 symbol"):
            get_iso286_limits(20.0, "Z99")


class TestParseISOFit:
    """Tests for parse_iso_fit helper."""

    def test_valid_fits(self) -> None:
        assert parse_iso_fit("H7/g6") == ("H7", "g6")
        assert parse_iso_fit("H8 / f7") == ("H8", "f7")
        assert parse_iso_fit("D10/h6") == ("D10", "h6")

    def test_invalid_fits(self) -> None:
        with pytest.raises(ValueError, match="Expected format"):
            parse_iso_fit("H7-g6")
        with pytest.raises(ValueError, match="Invalid hole format"):
            parse_iso_fit("h7/g6")
        with pytest.raises(ValueError, match="Invalid shaft format"):
            parse_iso_fit("H7/G6")


class TestCalculateFit:
    """Tests for ISO fit calculations (clearance, interference, transition)."""

    def test_clearance_fit(self) -> None:
        # Ø20 H7/g6:
        # H7: [0, +0.021]
        # g6: [-0.020, -0.007]
        # J_min = 0 - (-0.007) = +0.007 mm
        # J_max = 0.021 - (-0.020) = +0.041 mm
        res = calculate_fit(20.0, "H7", "g6")
        assert res.fit_type == "jeu"
        assert res.min_clearance == 0.007
        assert res.max_clearance == 0.041
        assert res.hole_min == 20.0
        assert res.hole_max == 20.021
        assert res.shaft_min == 19.980
        assert res.shaft_max == 19.993

    def test_interference_fit(self) -> None:
        # Ø20 H7/p6:
        # H7: [0, +0.021]
        # p6: [+0.022, +0.035]
        # J_min = 0 - 0.035 = -0.035 mm
        # J_max = 0.021 - 0.022 = -0.001 mm
        res = calculate_fit(20.0, "H7", "p6")
        assert res.fit_type == "serrage"
        assert res.min_clearance == -0.035
        assert res.max_clearance == -0.001

    def test_transition_fit(self) -> None:
        # Ø20 H7/k6:
        # H7: [0, +0.021]
        # k6: [+0.002, +0.015]
        # J_min = 0 - 0.015 = -0.015 mm (serrage)
        # J_max = 0.021 - 0.002 = +0.019 mm (jeu)
        res = calculate_fit(20.0, "H7", "k6")
        assert res.fit_type == "incertain"
        assert res.min_clearance == -0.015
        assert res.max_clearance == 0.019


class TestISO2768:
    """Tests for ISO 2768-1 general tolerances."""

    def test_linear_tolerance_ranges(self) -> None:
        # Medium class (m):
        # 0.5 to 3: +/- 0.1
        assert get_iso2768_linear_tolerance(2.0, "m") == 0.1
        # 6 to 30: +/- 0.2
        assert get_iso2768_linear_tolerance(10.0, "m") == 0.2
        # Fine class (f):
        assert get_iso2768_linear_tolerance(10.0, "f") == 0.1
        # Coarse (c):
        assert get_iso2768_linear_tolerance(10.0, "c") == 0.5
        # Very small size fallback
        assert get_iso2768_linear_tolerance(0.2, "m") == 0.1
        # Beyond table size
        assert get_iso2768_linear_tolerance(5000.0, "m") == 2.0

    def test_linear_invalid(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            get_iso2768_linear_tolerance(-5.0)
        with pytest.raises(ValueError, match="Unknown ISO 2768-1 grade"):
            get_iso2768_linear_tolerance(10.0, "x")  # type: ignore

    def test_broken_edges_tolerance(self) -> None:
        assert get_iso2768_broken_edges_tolerance(2.0, "m") == 0.2
        assert get_iso2768_broken_edges_tolerance(5.0, "m") == 0.5
        assert get_iso2768_broken_edges_tolerance(10.0, "m") == 1.0
        assert get_iso2768_broken_edges_tolerance(0.2, "m") == 0.2
        assert get_iso2768_broken_edges_tolerance(5000.0, "m") == 1.0
        with pytest.raises(ValueError):
            get_iso2768_broken_edges_tolerance(0.0)
        with pytest.raises(ValueError):
            get_iso2768_broken_edges_tolerance(10.0, "invalid")  # type: ignore

    def test_angular_tolerance(self) -> None:
        assert get_iso2768_angular_tolerance(5.0, "m") == 1.0
        assert get_iso2768_angular_tolerance(25.0, "m") == 0.5
        assert get_iso2768_angular_tolerance(5000.0, "m") == 0.083
        with pytest.raises(ValueError):
            get_iso2768_angular_tolerance(0.0)
        with pytest.raises(ValueError):
            get_iso2768_angular_tolerance(10.0, "invalid")  # type: ignore
