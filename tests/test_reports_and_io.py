"""Test suite for project IO (.cotastack JSON) and PDF report generator."""

import pytest
from backend.models import Item
from backend.calculator import ChainCalculator
from backend.project_io import serialize_project, deserialize_project
from backend.report_generator import generate_pdf_report


class TestProjectIO:
    """Tests for .cotastack serialization and deserialization."""

    def test_roundtrip_serialization(self) -> None:
        items = [
            Item(name="Carter", nominal=100.0, ei=-0.1, es=0.1, orientation=1, material="Aluminium (alliage 6000/7000)"),
            Item(name="Arbre", nominal=98.0, ei=-0.05, es=0.05, orientation=-1, material="Acier (standard)"),
        ]
        meta = {"title": "Test Assembly", "author": "Bureau d'Études", "revision": "B"}
        dists = {"Carter": "uniforme", "Arbre": "normale"}

        json_str = serialize_project(
            items=items,
            project_metadata=meta,
            target_min=1.5,
            target_max=2.5,
            t_service=80.0,
            distributions=dists,
        )

        loaded = deserialize_project(json_str)
        assert len(loaded["items"]) == 2
        assert loaded["items"][0].name == "Carter"
        assert loaded["items"][0].material == "Aluminium (alliage 6000/7000)"
        assert loaded["items"][0].orientation == 1
        assert loaded["items"][1].name == "Arbre"
        assert loaded["items"][1].orientation == -1
        assert loaded["target_min"] == 1.5
        assert loaded["target_max"] == 2.5
        assert loaded["t_service"] == 80.0
        assert loaded["metadata"]["title"] == "Test Assembly"
        assert loaded["distributions"]["Carter"] == "uniforme"

    def test_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Fichier JSON invalide"):
            deserialize_project("Not a json")

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="pas un fichier de projet CotaStack"):
            deserialize_project('{"format": "other"}')

    def test_invalid_root_structure(self) -> None:
        with pytest.raises(ValueError, match="Structure de fichier .cotastack invalide"):
            deserialize_project('"plain string"')

    def test_invalid_items_list(self) -> None:
        with pytest.raises(ValueError, match="La liste des maillons est invalide"):
            deserialize_project('{"format": "cotastack", "items": "not a list"}')

    def test_invalid_item_data(self) -> None:
        with pytest.raises(ValueError, match="Erreur lors de la lecture"):
            deserialize_project('{"format": "cotastack", "items": [{"name": "bad", "nominal": "abc"}]}')

    def test_item_data_fallback_and_skip(self) -> None:
        # non-dict item skipped, orientation out of (1, -1) normalized to 1
        json_data = '''{
            "format": "cotastack",
            "items": [
                "not-a-dict",
                {"name": "Valid", "nominal": 10.0, "es": 0.1, "ei": -0.1, "orientation": 42}
            ]
        }'''
        res = deserialize_project(json_data)
        assert len(res["items"]) == 1
        assert res["items"][0].orientation == 1


class TestPDFReportGenerator:
    """Tests for PDF report generation."""

    def test_pdf_generation_basic(self) -> None:
        items = [
            Item(name="Cote A", nominal=50.0, ei=-0.1, es=0.1, orientation=1),
            Item(name="Cote B", nominal=30.0, ei=-0.05, es=0.05, orientation=-1),
        ]
        calc = ChainCalculator(items, target_min=19.8, target_max=20.2)
        res = calc.calculate()

        pdf_bytes = generate_pdf_report(
            items=items,
            result=res,
            project_metadata={"title": "Projet Guidage", "author": "BE Tech", "revision": "1.0"},
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")

    def test_pdf_generation_escapes_special_characters_and_tags(self) -> None:
        """Security: Verify user input with HTML/XML characters does not break PDF generation."""
        items = [
            Item(
                name="<script>alert('xss')</script> & Cote <1>",
                nominal=25.0,
                ei=-0.05,
                es=0.05,
                orientation=1,
                material="Acier & Alliage <Special>",
            ),
        ]
        calc = ChainCalculator(items)
        res = calc.calculate()

        # Metadata with unclosed tags and XML entities that would cause ReportLab parse errors
        meta = {
            "title": "Projet <Test> & <Unclosed Tag",
            "author": "Ingénieur <BE> & 'Qualité'",
            "revision": "Rev <A&B>",
            "date": "2026-10-30 <UTC>",
        }

        pdf_bytes = generate_pdf_report(
            items=items,
            result=res,
            project_metadata=meta,
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")

    def test_pdf_generation_with_advanced_summaries(self) -> None:
        items = [Item(name="Solo", nominal=10.0, ei=-0.1, es=0.1)]
        calc = ChainCalculator(items)
        res = calc.calculate()

        thermal_data = {"t_service": 85.0, "nominal_at_t": 10.05, "delta_j_nominal": 0.05}
        mc_data = {"defect_ppm": 240.0, "cp": 1.45, "cpk": 1.38}

        pdf_bytes = generate_pdf_report(
            items=items,
            result=res,
            thermal_summary=thermal_data,
            monte_carlo_summary=mc_data,
        )

        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")
