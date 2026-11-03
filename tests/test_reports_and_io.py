"""Test suite for project IO (.cotastack JSON) and PDF report generator."""

import pytest
from backend.models import Item
from backend.calculator import ChainCalculator
from backend.project_io import serialize_project, deserialize_project, ProjectImportError
from backend.report_generator import (
    generate_pdf_report,
    generate_multi_chain_pdf_report,
    _build_1d_chain_drawing,
)
from backend.multi_chain import MultiChainProject, CatalogPart, AssemblyChain, ChainLink


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

    def test_deserialize_null_and_malformed_sections(self) -> None:
        # None and non-dict values for metadata, targets, and thermal sections must not crash
        json_nulls = '{"format": "cotastack", "metadata": null, "targets": null, "thermal": null, "items": []}'
        res_nulls = deserialize_project(json_nulls)
        assert res_nulls["metadata"] == {}
        assert res_nulls["target_min"] is None
        assert res_nulls["target_max"] is None
        assert res_nulls["t_service"] == 20.0

        json_invalid_types = '{"format": "cotastack", "metadata": "not_a_dict", "targets": 123, "thermal": false, "items": []}'
        res_invalid = deserialize_project(json_invalid_types)
        assert res_invalid["metadata"] == {}
        assert res_invalid["target_min"] is None
        assert res_invalid["target_max"] is None
        assert res_invalid["t_service"] == 20.0

    def test_deserialize_target_validations(self) -> None:
        # Non-numeric target_min
        with pytest.raises(ValueError, match="Valeur de cible dimensionnelle invalide"):
            deserialize_project('{"format": "cotastack", "targets": {"target_min": "bad"}}')

        # Non-finite target_min (NaN / Inf)
        with pytest.raises(ValueError, match="Valeur de cible dimensionnelle invalide"):
            deserialize_project('{"format": "cotastack", "targets": {"target_min": "nan"}}')

        # target_min > target_max
        with pytest.raises(ValueError, match="target_min ne peut pas être strictement supérieur"):
            deserialize_project('{"format": "cotastack", "targets": {"target_min": 5.0, "target_max": 2.0}}')

    def test_deserialize_thermal_validations(self) -> None:
        # Non-numeric t_service
        with pytest.raises(ValueError, match="Température de service invalide"):
            deserialize_project('{"format": "cotastack", "thermal": {"t_service": "invalid"}}')

        # Temperature below absolute zero (-273.15 °C)
        with pytest.raises(ValueError, match="Température de service invalide"):
            deserialize_project('{"format": "cotastack", "thermal": {"t_service": -300.0}}')

        # Non-finite temperature (NaN)
        with pytest.raises(ValueError, match="Température de service invalide"):
            deserialize_project('{"format": "cotastack", "thermal": {"t_service": "nan"}}')

    def test_deserialize_non_finite_item_dimensions(self) -> None:
        # NaN nominal
        with pytest.raises(ValueError, match="Les cotes doivent être des valeurs numériques finies"):
            deserialize_project('{"format": "cotastack", "items": [{"name": "P1", "nominal": "nan", "es": 0.1, "ei": -0.1}]}')

        # Inf es
        with pytest.raises(ValueError, match="Les cotes doivent être des valeurs numériques finies"):
            deserialize_project('{"format": "cotastack", "items": [{"name": "P2", "nominal": 10.0, "es": "inf", "ei": -0.1}]}')

    def test_deserialize_distribution_sanitization(self) -> None:
        # Unknown or unallowed distribution defaults safely to "normale"
        json_data = '{"format": "cotastack", "items": [{"name": "P1", "nominal": 10.0, "es": 0.1, "ei": -0.1, "distribution": "custom_hack"}]}'
        res = deserialize_project(json_data)
        assert res["distributions"]["P1"] == "normale"

    def test_project_import_error_subclass(self) -> None:
        """Verify that ProjectImportError is raised and is a subclass of ValueError."""
        assert issubclass(ProjectImportError, ValueError)
        with pytest.raises(ProjectImportError, match="Fichier JSON invalide"):
            deserialize_project("invalid json {")


class TestPDFReportGenerator:
    """Tests for single-chain PDF report generation."""

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


class TestMultiChainPDFReport:
    """Tests for multi-chain A4 PDF report generation and vector drawing."""

    def test_generate_multi_chain_pdf_nominal(self) -> None:
        proj = MultiChainProject(name="Boîte de Transmission Robotique", description="Système réducteur d'axe")
        p1 = CatalogPart(id="CARTER_01", name="Carter usiné", nominal=120.0, es=0.08, ei=-0.08, material="Aluminium (alliage 6000/7000)")
        p2 = CatalogPart(id="ARBRE_01", name="Arbre primaire", nominal=118.0, es=0.04, ei=-0.04, material="Acier (standard)")
        p3 = CatalogPart(id="ROULEMENT_01", name="Roulement à billes", nominal=10.0, es=0.02, ei=-0.02, material="Acier trempé 100Cr6")
        proj.add_part(p1)
        proj.add_part(p2)
        proj.add_part(p3)

        c1 = AssemblyChain(id="JEU_AXIAL", name="Jeu axial arbre-carter", description="Jeu fonctionnel de liberté axiale", target_min=0.5, target_max=2.5)
        c1.links.append(ChainLink(orientation=1, part_id="CARTER_01"))
        c1.links.append(ChainLink(orientation=-1, part_id="ARBRE_01"))
        c1.links.append(ChainLink(orientation=-1, custom_name="Rondelle calage", local_nominal=1.0, local_es=0.01, local_ei=-0.01))
        proj.add_chain(c1)

        c2 = AssemblyChain(id="JEU_LOGEMENT", name="Guidage roulement", target_min=0.0, target_max=0.1)
        c2.links.append(ChainLink(orientation=1, part_id="CARTER_01", scale_factor=0.5))
        c2.links.append(ChainLink(orientation=-1, part_id="ROULEMENT_01"))
        proj.add_chain(c2)

        pdf_bytes = generate_multi_chain_pdf_report(
            proj,
            project_metadata={
                "title": "Étude Tolérancement Réducteur",
                "author": "Ingénieur R&D Mécanique",
                "revision": "B",
                "date": "2026-11-02",
            },
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 2000
        assert pdf_bytes.startswith(b"%PDF-")

    def test_generate_multi_chain_pdf_empty_project(self) -> None:
        proj = MultiChainProject(name="Projet Vierge")
        pdf_bytes = generate_multi_chain_pdf_report(proj)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")

    def test_generate_multi_chain_pdf_empty_chain_and_partial_links(self) -> None:
        proj = MultiChainProject(name="Projet Chaîne Vide")
        c_empty = AssemblyChain(id="EMPTY_C", name="Chaîne sans maillon", description="Chaîne en cours de saisie")
        proj.add_chain(c_empty)

        # Chaîne avec cote locale
        c_local = AssemblyChain(id="LOCAL_C", name="Chaîne cote locale")
        c_local.links.append(ChainLink(orientation=1, custom_name="Cote directe", local_nominal=10.0, local_es=0.1, local_ei=-0.1))
        proj.add_chain(c_local)

        pdf_bytes = generate_multi_chain_pdf_report(proj)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")

    def test_generate_multi_chain_pdf_special_characters_escaping(self) -> None:
        proj = MultiChainProject(name="Projet <Système> & \"Spécial\"")
        p = CatalogPart(id="P_SPEC", name="Pièce <XSS> & Inox", nominal=20.0, es=0.1, ei=-0.1)
        proj.add_part(p)

        c = AssemblyChain(id="C_SPEC", name="Chaîne <T1> & 'T2'", description="Desc avec <balise> & ampersand")
        c.links.append(ChainLink(orientation=1, part_id="P_SPEC", custom_name="Cote <A&B>"))
        proj.add_chain(c)

        pdf_bytes = generate_multi_chain_pdf_report(
            proj,
            project_metadata={
                "title": "Titre <Dangereux> & 'XML'",
                "author": "Auteur & <BE>",
                "revision": "Rév <1.0>",
                "date": "2026-11-02",
            },
        )
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-")

    def test_build_1d_chain_drawing_edge_cases(self) -> None:
        chain = AssemblyChain(id="C1", name="Test")
        # 1. Empty items
        d_empty = _build_1d_chain_drawing(chain, [])
        assert d_empty.height == 40.0

        # 2. Items resulting in negative closure game
        items_neg = [
            Item(name="A", nominal=10.0, ei=-0.1, es=0.1, orientation=1),
            Item(name="B", nominal=15.0, ei=-0.1, es=0.1, orientation=-1),
        ]
        d_neg = _build_1d_chain_drawing(chain, items_neg)
        assert d_neg.height > 50.0

        # 3. Items resulting in zero span
        items_zero = [
            Item(name="Zero1", nominal=0.0, ei=0.0, es=0.0, orientation=1),
        ]
        d_zero = _build_1d_chain_drawing(chain, items_zero)
        assert d_zero.height > 50.0
