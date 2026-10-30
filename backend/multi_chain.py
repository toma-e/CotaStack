"""Multi-chain system module for CotaStack (Milestone 3.1).

Enables single-source-of-truth part cataloging and instant propagation across
multiple assembly tolerance chains in a complex mechanical system.
"""

from dataclasses import dataclass, field
import json
from typing import Any, Literal

from backend.models import Item, ChainResult
from backend.calculator import ChainCalculator


@dataclass(slots=True)
class CatalogPart:
    """Master component definition in the project unified repository."""
    id: str
    name: str
    nominal: float
    es: float
    ei: float
    material: str = "Acier (standard)"
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValueError("L'identifiant de la pièce (id) ne peut pas être vide.")
        if not self.name or not str(self.name).strip():
            raise ValueError("Le nom de la pièce ne peut pas être vide.")
        if self.es < self.ei:
            raise ValueError(f"es ({self.es}) doit être >= ei ({self.ei}) pour la pièce {self.id}")
        if self.nominal < 0:
            raise ValueError(f"La cote nominale doit être >= 0, reçu : {self.nominal}")

    @property
    def IT(self) -> float:
        return round(self.es - self.ei, 5)

    @property
    def upper_limit(self) -> float:
        return round(self.nominal + self.es, 5)

    @property
    def lower_limit(self) -> float:
        return round(self.nominal + self.ei, 5)

    @property
    def L_moy(self) -> float:
        return round(self.nominal + (self.es + self.ei) / 2.0, 5)


@dataclass(slots=True)
class ChainLink:
    """A link in an assembly chain. Can reference a master CatalogPart or be a local standalone item."""
    orientation: Literal[1, -1] = 1
    part_id: str | None = None
    custom_name: str = ""
    scale_factor: float = 1.0  # Projection factor or multiplier (default: 1.0)
    local_nominal: float | None = None
    local_es: float | None = None
    local_ei: float | None = None
    local_material: str = "Acier (standard)"

    def __post_init__(self) -> None:
        if self.orientation not in (1, -1):
            raise ValueError(f"L'orientation doit être 1 ou -1, reçu : {self.orientation}")
        if self.scale_factor <= 0:
            raise ValueError(f"Le facteur d'échelle doit être > 0, reçu : {self.scale_factor}")
        if self.part_id is None and (self.local_nominal is None or self.local_es is None or self.local_ei is None):
            raise ValueError("Un maillon doit soit référencer un part_id du catalogue, soit définir des cotes locales complètes.")
        if self.local_es is not None and self.local_ei is not None and self.local_es < self.local_ei:
            raise ValueError("Pour un maillon local, local_es doit être >= local_ei")
        if self.local_nominal is not None and self.local_nominal < 0:
            raise ValueError("Pour un maillon local, local_nominal doit être >= 0")


@dataclass(slots=True)
class AssemblyChain:
    """Definition of a 1D tolerance chain in the multi-chain system."""
    id: str
    name: str
    description: str = ""
    target_min: float | None = None
    target_max: float | None = None
    links: list[ChainLink] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValueError("L'identifiant de la chaîne (id) ne peut pas être vide.")
        if not self.name or not str(self.name).strip():
            raise ValueError("Le nom de la chaîne ne peut pas être vide.")
        if self.target_min is not None and self.target_max is not None and self.target_min > self.target_max:
            raise ValueError("target_min ne peut pas être strictement supérieur à target_max.")


@dataclass(slots=True)
class SystemChainStatus:
    """Evaluation status of a chain within the multi-chain assembly."""
    chain_id: str
    name: str
    result: ChainResult
    is_wc_compliant: bool | None
    is_rss_compliant: bool | None
    wc_status_label: str
    rss_status_label: str


@dataclass(slots=True)
class MultiChainSummary:
    """Global system health & cross-impact summary."""
    total_chains: int
    wc_compliant_count: int
    rss_compliant_count: int
    non_compliant_count: int
    shared_parts_matrix: dict[str, list[str]]  # part_id -> list[chain_id]
    critical_pivot_parts: list[str]  # parts used in 2 or more chains
    chains_status: list[SystemChainStatus]


class MultiChainProject:
    """Unified repository managing catalog parts, multiple assembly chains, and live propagation."""

    def __init__(self, name: str = "Système Mécanique Multi-Chaînes", description: str = "") -> None:
        self.name = name
        self.description = description
        self.parts: dict[str, CatalogPart] = {}
        self.chains: dict[str, AssemblyChain] = {}

    def add_part(self, part: CatalogPart) -> None:
        """Add or replace a catalog part."""
        self.parts[part.id] = part

    def get_part(self, part_id: str) -> CatalogPart:
        if part_id not in self.parts:
            raise KeyError(f"Pièce introuvable dans le catalogue : {part_id}")
        return self.parts[part_id]

    def remove_part(self, part_id: str) -> list[str]:
        """Remove a part from catalog and return the IDs of chains that referenced it."""
        if part_id not in self.parts:
            raise KeyError(f"Pièce introuvable : {part_id}")
        impacted_chains = self.get_part_impact(part_id)
        del self.parts[part_id]
        return impacted_chains

    def add_chain(self, chain: AssemblyChain) -> None:
        """Add or replace an assembly chain."""
        self.chains[chain.id] = chain

    def get_chain(self, chain_id: str) -> AssemblyChain:
        if chain_id not in self.chains:
            raise KeyError(f"Chaîne introuvable : {chain_id}")
        return self.chains[chain_id]

    def remove_chain(self, chain_id: str) -> None:
        if chain_id not in self.chains:
            raise KeyError(f"Chaîne introuvable : {chain_id}")
        del self.chains[chain_id]

    def update_chain(
        self,
        chain_id: str,
        name: str | None = None,
        description: str | None = None,
        target_min: float | None = None,
        target_max: float | None = None,
    ) -> AssemblyChain:
        """Update chain metadata and functional tolerance limits."""
        chain = self.get_chain(chain_id)
        new_name = str(name).strip() if name is not None else chain.name
        if not new_name:
            raise ValueError("Le nom de la chaîne ne peut pas être vide.")
        new_desc = str(description) if description is not None else chain.description
        new_tmin = target_min if target_min is not None else chain.target_min
        new_tmax = target_max if target_max is not None else chain.target_max

        if new_tmin is not None and new_tmax is not None and new_tmin > new_tmax:
            raise ValueError("target_min ne peut pas être strictement supérieur à target_max.")

        chain.name = new_name
        chain.description = new_desc
        chain.target_min = new_tmin
        chain.target_max = new_tmax
        return chain

    def remove_link_from_chain(self, chain_id: str, link_index: int) -> ChainLink:
        """Remove a link at link_index (0-indexed) from a chain."""
        chain = self.get_chain(chain_id)
        if link_index < 0 or link_index >= len(chain.links):
            raise IndexError(f"Index de maillon invalide : {link_index} (taille de la chaîne : {len(chain.links)})")
        return chain.links.pop(link_index)

    def clear_all(self) -> None:
        """Reset the whole project repository to empty state (0 parts, 0 chains)."""
        self.parts.clear()
        self.chains.clear()

    def add_link_to_chain(
        self,
        chain_id: str,
        part_id: str | None = None,
        orientation: Literal[1, -1] = 1,
        custom_name: str = "",
        scale_factor: float = 1.0,
        local_nominal: float | None = None,
        local_es: float | None = None,
        local_ei: float | None = None,
        local_material: str = "Acier (standard)",
    ) -> ChainLink:
        """Create and append a link to a specific chain."""
        chain = self.get_chain(chain_id)
        if part_id is not None and part_id not in self.parts:
            raise KeyError(f"Impossible de lier : la pièce '{part_id}' n'existe pas dans le catalogue.")

        link = ChainLink(
            orientation=orientation,
            part_id=part_id,
            custom_name=custom_name,
            scale_factor=scale_factor,
            local_nominal=local_nominal,
            local_es=local_es,
            local_ei=local_ei,
            local_material=local_material,
        )
        chain.links.append(link)
        return link

    def resolve_chain_items(self, chain_id: str) -> list[Item]:
        """Propagate current catalog dimensions into executable 1D Items for calculation."""
        chain = self.get_chain(chain_id)
        items: list[Item] = []

        for idx, link in enumerate(chain.links):
            if link.part_id is not None:
                if link.part_id not in self.parts:
                    raise KeyError(f"Chaîne '{chain_id}', maillon {idx+1} : Pièce '{link.part_id}' absente du catalogue.")
                part = self.parts[link.part_id]
                item_name = link.custom_name.strip() or f"{part.name} [{part.id}]"
                nom = part.nominal * link.scale_factor
                es = part.es * link.scale_factor
                ei = part.ei * link.scale_factor
                items.append(Item(
                    name=item_name,
                    nominal=round(nom, 5),
                    es=round(es, 5),
                    ei=round(ei, 5),
                    orientation=link.orientation,
                    material=part.material,
                ))
            else:
                item_name = link.custom_name.strip() or f"Cote_locale_{idx+1}"
                nom = (link.local_nominal or 0.0) * link.scale_factor
                es = (link.local_es or 0.0) * link.scale_factor
                ei = (link.local_ei or 0.0) * link.scale_factor
                items.append(Item(
                    name=item_name,
                    nominal=round(nom, 5),
                    es=round(es, 5),
                    ei=round(ei, 5),
                    orientation=link.orientation,
                    material=link.local_material,
                ))

        return items

    def evaluate_chain(self, chain_id: str) -> ChainResult:
        """Calculate Worst-Case, RSS, and compliance for a given chain using propagated catalog values."""
        chain = self.get_chain(chain_id)
        items = self.resolve_chain_items(chain_id)
        if not items:
            raise ValueError(f"La chaîne '{chain_id}' ne contient aucun maillon.")
        calc = ChainCalculator(items, target_min=chain.target_min, target_max=chain.target_max)
        return calc.calculate()

    def evaluate_all(self) -> dict[str, ChainResult]:
        """Recalculate all chains in the project instantly."""
        results: dict[str, ChainResult] = {}
        for chain_id in self.chains:
            if self.chains[chain_id].links:
                results[chain_id] = self.evaluate_chain(chain_id)
        return results

    def get_part_impact(self, part_id: str) -> list[str]:
        """Return list of chain IDs where this part is involved."""
        impacted: list[str] = []
        for c_id, chain in self.chains.items():
            for link in chain.links:
                if link.part_id == part_id:
                    impacted.append(c_id)
                    break
        return impacted

    def get_system_summary(self) -> MultiChainSummary:
        """Produce a comprehensive health summary of the entire multi-chain system."""
        shared_matrix: dict[str, list[str]] = {}
        for p_id in self.parts:
            shared_matrix[p_id] = self.get_part_impact(p_id)

        pivot_parts = [p_id for p_id, chains in shared_matrix.items() if len(chains) >= 2]

        chains_status: list[SystemChainStatus] = []
        wc_ok_count = 0
        rss_ok_count = 0
        non_compliant_count = 0

        for c_id, chain in self.chains.items():
            if not chain.links:
                continue
            res = self.evaluate_chain(c_id)
            has_targets = chain.target_min is not None or chain.target_max is not None
            wc_comp = res.compliance.get("wc_compliant") if has_targets else None
            rss_comp = res.compliance.get("rss_compliant") if has_targets else None

            if wc_comp is True:
                wc_status = "✅ Conforme"
                wc_ok_count += 1
            elif wc_comp is False:
                wc_status = "❌ Non conforme"
            else:
                wc_status = "⚪ Sans cible"

            if rss_comp is True:
                rss_status = "✅ Conforme"
                rss_ok_count += 1
            elif rss_comp is False:
                rss_status = "❌ Non conforme"
            else:
                rss_status = "⚪ Sans cible"

            if wc_comp is False or rss_comp is False:
                non_compliant_count += 1

            chains_status.append(SystemChainStatus(
                chain_id=c_id,
                name=chain.name,
                result=res,
                is_wc_compliant=wc_comp,
                is_rss_compliant=rss_comp,
                wc_status_label=wc_status,
                rss_status_label=rss_status,
            ))

        return MultiChainSummary(
            total_chains=len(chains_status),
            wc_compliant_count=wc_ok_count,
            rss_compliant_count=rss_ok_count,
            non_compliant_count=non_compliant_count,
            shared_parts_matrix=shared_matrix,
            critical_pivot_parts=pivot_parts,
            chains_status=chains_status,
        )

    def to_dict(self) -> dict[str, Any]:
        """Export system to dict."""
        parts_data = {}
        for p_id, p in self.parts.items():
            parts_data[p_id] = {
                "id": p.id,
                "name": p.name,
                "nominal": p.nominal,
                "es": p.es,
                "ei": p.ei,
                "material": p.material,
                "description": p.description,
            }

        chains_data = {}
        for c_id, c in self.chains.items():
            links_data = []
            for l in c.links:
                links_data.append({
                    "orientation": l.orientation,
                    "part_id": l.part_id,
                    "custom_name": l.custom_name,
                    "scale_factor": l.scale_factor,
                    "local_nominal": l.local_nominal,
                    "local_es": l.local_es,
                    "local_ei": l.local_ei,
                    "local_material": l.local_material,
                })
            chains_data[c_id] = {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "target_min": c.target_min,
                "target_max": c.target_max,
                "links": links_data,
            }

        return {
            "format": "cotastack_multi_chain",
            "version": "1.0",
            "name": self.name,
            "description": self.description,
            "parts": parts_data,
            "chains": chains_data,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MultiChainProject":
        if not isinstance(data, dict):
            raise ValueError("Données du projet multi-chaînes invalides.")
        name = str(data.get("name", "Système Mécanique Multi-Chaînes"))
        description = str(data.get("description", ""))
        proj = cls(name=name, description=description)

        for p_id, p_raw in data.get("parts", {}).items():
            part = CatalogPart(
                id=str(p_raw.get("id", p_id)),
                name=str(p_raw.get("name", p_id)),
                nominal=float(p_raw["nominal"]),
                es=float(p_raw["es"]),
                ei=float(p_raw["ei"]),
                material=str(p_raw.get("material", "Acier (standard)")),
                description=str(p_raw.get("description", "")),
            )
            proj.add_part(part)

        for c_id, c_raw in data.get("chains", {}).items():
            chain = AssemblyChain(
                id=str(c_raw.get("id", c_id)),
                name=str(c_raw.get("name", c_id)),
                description=str(c_raw.get("description", "")),
                target_min=c_raw.get("target_min"),
                target_max=c_raw.get("target_max"),
            )
            for l_raw in c_raw.get("links", []):
                chain.links.append(ChainLink(
                    orientation=int(l_raw.get("orientation", 1)),  # type: ignore
                    part_id=l_raw.get("part_id"),
                    custom_name=str(l_raw.get("custom_name", "")),
                    scale_factor=float(l_raw.get("scale_factor", 1.0)),
                    local_nominal=float(l_raw["local_nominal"]) if l_raw.get("local_nominal") is not None else None,
                    local_es=float(l_raw["local_es"]) if l_raw.get("local_es") is not None else None,
                    local_ei=float(l_raw["local_ei"]) if l_raw.get("local_ei") is not None else None,
                    local_material=str(l_raw.get("local_material", "Acier (standard)")),
                ))
            proj.add_chain(chain)

        return proj

    @classmethod
    def from_json(cls, json_str: str) -> "MultiChainProject":
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON invalide : {e}")
        return cls.from_dict(data)
