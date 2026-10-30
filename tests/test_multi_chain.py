"""Unit tests for multi-chain unified repository (backend.multi_chain)."""

import pytest
from backend.multi_chain import (
    CatalogPart,
    ChainLink,
    AssemblyChain,
    MultiChainProject,
)


def approx(val: float, expected: float, tol: float = 1e-5) -> bool:
    return abs(val - expected) < tol


class TestCatalogPart:
    def test_valid_part(self):
        part = CatalogPart(
            id="P-01",
            name="Arbre primaire",
            nominal=50.0,
            es=0.0,
            ei=-0.025,
            material="Acier (standard)",
            description="Arbre de transmission",
        )
        assert approx(part.IT, 0.025)
        assert approx(part.upper_limit, 50.0)
        assert approx(part.lower_limit, 49.975)
        assert approx(part.L_moy, 49.9875)

    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="identifiant de la pièce"):
            CatalogPart(id="", name="Carter", nominal=100.0, es=0.1, ei=-0.1)

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="nom de la pièce"):
            CatalogPart(id="P-02", name="", nominal=100.0, es=0.1, ei=-0.1)

    def test_invalid_es_ei(self):
        with pytest.raises(ValueError, match="es .* doit être >= ei"):
            CatalogPart(id="P-03", name="Pignon", nominal=30.0, es=-0.05, ei=-0.02)

    def test_negative_nominal(self):
        with pytest.raises(ValueError, match="cote nominale doit être >= 0"):
            CatalogPart(id="P-04", name="Pignon", nominal=-10.0, es=0.05, ei=-0.02)


class TestChainLink:
    def test_valid_part_link(self):
        link = ChainLink(orientation=1, part_id="P-01", custom_name="Portée roulement")
        assert link.orientation == 1
        assert link.part_id == "P-01"

    def test_valid_local_link(self):
        link = ChainLink(
            orientation=-1,
            local_nominal=15.0,
            local_es=0.05,
            local_ei=-0.05,
            local_material="Aluminium",
        )
        assert link.orientation == -1
        assert link.part_id is None
        assert approx(link.local_nominal, 15.0)

    def test_invalid_orientation(self):
        with pytest.raises(ValueError, match="L'orientation doit être 1 ou -1"):
            ChainLink(orientation=0, part_id="P-01")  # type: ignore

    def test_missing_part_and_local(self):
        with pytest.raises(ValueError, match="soit référencer un part_id"):
            ChainLink(orientation=1)

    def test_invalid_local_es_ei(self):
        with pytest.raises(ValueError, match="local_es doit être >= local_ei"):
            ChainLink(orientation=1, local_nominal=10.0, local_es=-0.1, local_ei=0.0)

    def test_negative_local_nominal(self):
        with pytest.raises(ValueError, match="local_nominal doit être >= 0"):
            ChainLink(orientation=1, local_nominal=-5.0, local_es=0.1, local_ei=-0.1)


class TestAssemblyChain:
    def test_valid_chain(self):
        chain = AssemblyChain(
            id="CH-AXIAL",
            name="Jeu axial",
            target_min=0.1,
            target_max=0.5,
        )
        assert chain.id == "CH-AXIAL"
        assert chain.name == "Jeu axial"

    def test_empty_id(self):
        with pytest.raises(ValueError, match="identifiant de la chaîne"):
            AssemblyChain(id="", name="Jeu")

    def test_empty_name(self):
        with pytest.raises(ValueError, match="nom de la chaîne"):
            AssemblyChain(id="C1", name="")

    def test_invalid_targets(self):
        with pytest.raises(ValueError, match="target_min ne peut pas être strictement supérieur"):
            AssemblyChain(id="C1", name="Jeu", target_min=0.8, target_max=0.2)


class TestMultiChainProject:
    @pytest.fixture
    def project(self) -> MultiChainProject:
        proj = MultiChainProject(name="Boîte de Vitesses", description="Système de transmission")
        # Define shared master parts in catalog
        proj.add_part(CatalogPart("CARTER", "Carter principal", nominal=120.0, es=0.050, ei=-0.050, material="Aluminium"))
        proj.add_part(CatalogPart("ARBRE", "Arbre secondaire", nominal=90.0, es=0.020, ei=-0.020, material="Acier (standard)"))
        proj.add_part(CatalogPart("ROULEMENT", "Roulement 6205", nominal=15.0, es=0.010, ei=-0.010, material="Acier (standard)"))
        proj.add_part(CatalogPart("CIRCLIPS", "Circlips arrêt", nominal=2.0, es=0.005, ei=-0.005, material="Acier (standard)"))

        # Chain 1: Jeu axial = CARTER (+) - ARBRE (-) - 2 * ROULEMENT (-)
        c1 = AssemblyChain("JEU_AXIAL", "Jeu axial de l'arbre", target_min=0.2, target_max=1.0)
        proj.add_chain(c1)
        proj.add_link_to_chain("JEU_AXIAL", part_id="CARTER", orientation=1)
        proj.add_link_to_chain("JEU_AXIAL", part_id="ARBRE", orientation=-1)
        proj.add_link_to_chain("JEU_AXIAL", part_id="ROULEMENT", orientation=-1, custom_name="Roulement gauche")
        proj.add_link_to_chain("JEU_AXIAL", part_id="ROULEMENT", orientation=-1, custom_name="Roulement droit")

        # Chain 2: Jeu gorge circlips = CIRCLIPS (-) + local gorge (+)
        c2 = AssemblyChain("JEU_CIRCLIPS", "Jeu axial circlips", target_min=0.05, target_max=0.3)
        proj.add_chain(c2)
        proj.add_link_to_chain("JEU_CIRCLIPS", part_id="CIRCLIPS", orientation=-1)
        proj.add_link_to_chain("JEU_CIRCLIPS", orientation=1, local_nominal=2.2, local_es=0.05, local_ei=0.0, custom_name="Gorge usinée")

        # Chain 3: Jeu entretoise = CARTER (+) - ARBRE (-) - CIRCLIPS (-)
        c3 = AssemblyChain("JEU_ENTRETOISE", "Jeu sous entretoise", target_min=25.0, target_max=32.0)
        proj.add_chain(c3)
        proj.add_link_to_chain("JEU_ENTRETOISE", part_id="CARTER", orientation=1)
        proj.add_link_to_chain("JEU_ENTRETOISE", part_id="ARBRE", orientation=-1)
        proj.add_link_to_chain("JEU_ENTRETOISE", part_id="CIRCLIPS", orientation=-1)

        return proj

    def test_parts_and_chains_retrieval(self, project: MultiChainProject):
        assert project.get_part("CARTER").nominal == 120.0
        assert project.get_chain("JEU_AXIAL").name == "Jeu axial de l'arbre"

        with pytest.raises(KeyError, match="Pièce introuvable"):
            project.get_part("UNKNOWN")
        with pytest.raises(KeyError, match="Chaîne introuvable"):
            project.get_chain("UNKNOWN")

    def test_remove_part_and_chain(self, project: MultiChainProject):
        impact = project.remove_part("CIRCLIPS")
        assert "JEU_CIRCLIPS" in impact
        assert "JEU_ENTRETOISE" in impact
        with pytest.raises(KeyError):
            project.get_part("CIRCLIPS")
        with pytest.raises(KeyError):
            project.remove_part("NON_EXISTENT")

        project.remove_chain("JEU_CIRCLIPS")
        with pytest.raises(KeyError):
            project.get_chain("JEU_CIRCLIPS")
        with pytest.raises(KeyError):
            project.remove_chain("NON_EXISTENT")

    def test_add_link_invalid_part_raises(self, project: MultiChainProject):
        with pytest.raises(KeyError, match="la pièce 'UNKNOWN' n'existe pas"):
            project.add_link_to_chain("JEU_AXIAL", part_id="UNKNOWN")

    def test_resolve_chain_items(self, project: MultiChainProject):
        items = project.resolve_chain_items("JEU_AXIAL")
        assert len(items) == 4
        # CARTER
        assert items[0].name == "Carter principal [CARTER]"
        assert approx(items[0].nominal, 120.0)
        assert items[0].orientation == 1
        # Custom name
        assert items[2].name == "Roulement gauche"

    def test_resolve_missing_part_raises(self, project: MultiChainProject):
        project.chains["JEU_AXIAL"].links.append(ChainLink(orientation=1, part_id="DELETED_PART"))
        with pytest.raises(KeyError, match="absente du catalogue"):
            project.resolve_chain_items("JEU_AXIAL")

    def test_scale_factor(self, project: MultiChainProject):
        # Scale factor 2.0 doubles nominal, es and ei
        chain = AssemblyChain("SCALE_CH", "Test scale")
        project.add_chain(chain)
        project.add_link_to_chain("SCALE_CH", part_id="ARBRE", scale_factor=2.0)
        items = project.resolve_chain_items("SCALE_CH")
        assert approx(items[0].nominal, 180.0)
        assert approx(items[0].es, 0.040)
        assert approx(items[0].ei, -0.040)

        with pytest.raises(ValueError, match="Le facteur d'échelle doit être > 0"):
            ChainLink(orientation=1, part_id="ARBRE", scale_factor=-1.0)
        with pytest.raises(ValueError, match="Le facteur d'échelle doit être > 0"):
            ChainLink(orientation=1, part_id="ARBRE", scale_factor=0.0)

    def test_evaluate_chain_and_empty_chain(self, project: MultiChainProject):
        res1 = project.evaluate_chain("JEU_AXIAL")
        # Nominal: 120 - 90 - 15 - 15 = 0.0 mm
        assert approx(res1.nominal, 0.0)

        empty_c = AssemblyChain("EMPTY", "Vide")
        project.add_chain(empty_c)
        with pytest.raises(ValueError, match="ne contient aucun maillon"):
            project.evaluate_chain("EMPTY")

    def test_instant_propagation(self, project: MultiChainProject):
        """KEY TEST: Modifying a part in the catalog instantly updates all dependent chains."""
        # Baseline calculations
        res_axial_before = project.evaluate_chain("JEU_AXIAL")
        res_entretoise_before = project.evaluate_chain("JEU_ENTRETOISE")

        it_axial_before = res_axial_before.worst_case_plus - res_axial_before.worst_case_minus
        it_entretoise_before = res_entretoise_before.worst_case_plus - res_entretoise_before.worst_case_minus

        # Tighten the CARTER tolerance from ±0.050 to ±0.010 mm
        updated_carter = CatalogPart(
            id="CARTER",
            name="Carter principal",
            nominal=120.0,
            es=0.010,
            ei=-0.010,
            material="Aluminium",
        )
        project.add_part(updated_carter)

        # Recalculate
        res_axial_after = project.evaluate_chain("JEU_AXIAL")
        res_entretoise_after = project.evaluate_chain("JEU_ENTRETOISE")

        it_axial_after = res_axial_after.worst_case_plus - res_axial_after.worst_case_minus
        it_entretoise_after = res_entretoise_after.worst_case_plus - res_entretoise_after.worst_case_minus

        # The total worst-case tolerance range MUST have decreased in both chains by (0.100 - 0.020) = 0.080 mm
        assert approx(it_axial_before - it_axial_after, 0.080)
        assert approx(it_entretoise_before - it_entretoise_after, 0.080)

    def test_evaluate_all_and_summary(self, project: MultiChainProject):
        # Add an empty chain to test skip in summary and evaluate_all
        project.add_chain(AssemblyChain("EMPTY_CHAIN", "Chaîne vide sans maillons"))

        # Add a chain without targets (target_min=None, target_max=None)
        no_target_chain = AssemblyChain("NO_TARGETS", "Chaîne libre")
        project.add_chain(no_target_chain)
        project.add_link_to_chain("NO_TARGETS", part_id="ARBRE", orientation=1)

        # Add a non-compliant chain
        bad_chain = AssemblyChain("NON_COMPLIANT", "Hors tolérance", target_min=500.0, target_max=501.0)
        project.add_chain(bad_chain)
        project.add_link_to_chain("NON_COMPLIANT", part_id="CARTER", orientation=1)

        results = project.evaluate_all()
        assert "JEU_AXIAL" in results
        assert "JEU_CIRCLIPS" in results
        assert "JEU_ENTRETOISE" in results
        assert "NO_TARGETS" in results
        assert "NON_COMPLIANT" in results
        assert "EMPTY_CHAIN" not in results

        summary = project.get_system_summary()
        assert summary.total_chains == 5
        assert summary.non_compliant_count >= 1
        # CARTER is in JEU_AXIAL, JEU_ENTRETOISE and NON_COMPLIANT -> pivot
        # ARBRE is in JEU_AXIAL, JEU_ENTRETOISE and NO_TARGETS -> pivot
        # CIRCLIPS is in JEU_CIRCLIPS and JEU_ENTRETOISE -> pivot
        assert "CARTER" in summary.critical_pivot_parts
        assert "ARBRE" in summary.critical_pivot_parts
        assert "CIRCLIPS" in summary.critical_pivot_parts
        assert "ROULEMENT" not in summary.critical_pivot_parts

        # Check status labels
        status_dict = {s.chain_id: s for s in summary.chains_status}
        assert status_dict["NO_TARGETS"].wc_status_label == "⚪ Sans cible"
        assert status_dict["NO_TARGETS"].rss_status_label == "⚪ Sans cible"
        assert status_dict["NON_COMPLIANT"].wc_status_label == "❌ Non conforme"
        assert status_dict["NON_COMPLIANT"].rss_status_label == "❌ Non conforme"

    def test_serialization_roundtrip(self, project: MultiChainProject):
        json_str = project.to_json()
        restored = MultiChainProject.from_json(json_str)

        assert restored.name == project.name
        assert len(restored.parts) == len(project.parts)
        assert len(restored.chains) == len(project.chains)

        res_orig = project.evaluate_chain("JEU_AXIAL")
        res_restored = restored.evaluate_chain("JEU_AXIAL")

        assert approx(res_orig.nominal, res_restored.nominal)
        assert approx(res_orig.worst_case_plus, res_restored.worst_case_plus)
        assert approx(res_orig.rss_plus, res_restored.rss_plus)

    def test_invalid_deserialization(self):
        with pytest.raises(ValueError, match="JSON invalide"):
            MultiChainProject.from_json("corrupted json string {")
        with pytest.raises(ValueError, match="Données du projet multi-chaînes invalides"):
            MultiChainProject.from_dict("not a dict")  # type: ignore
