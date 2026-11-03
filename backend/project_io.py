"""Project serialization module for CotaStack (.cotastack JSON format).

Provides privacy-first local project save and load functionality.
No remote database required.
"""

import json
import math
from typing import Any
from backend.models import Item


COTASTACK_FORMAT_VERSION = "1.0"


def serialize_project(
    items: list[Item],
    project_metadata: dict[str, Any] | None = None,
    target_min: float | None = None,
    target_max: float | None = None,
    t_service: float = 20.0,
    distributions: dict[str, str] | None = None,
) -> str:
    """Serialize full project state into formatted .cotastack JSON string."""
    project_metadata = project_metadata or {
        "title": "Projet de tolérancement 1D",
        "author": "Bureau d'Études Mécanique",
        "revision": "A",
        "notes": "",
    }

    items_data = []
    for it in items:
        items_data.append({
            "name": it.name,
            "nominal": it.nominal,
            "es": it.es,
            "ei": it.ei,
            "orientation": it.orientation,
            "material": it.material,
            "distribution": (distributions or {}).get(it.name, "normale"),
        })

    payload = {
        "format": "cotastack",
        "version": COTASTACK_FORMAT_VERSION,
        "metadata": project_metadata,
        "targets": {
            "target_min": target_min,
            "target_max": target_max,
        },
        "thermal": {
            "t_service": t_service,
        },
        "items": items_data,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def deserialize_project(json_content: str) -> dict[str, Any]:
    """Parse and validate a .cotastack JSON project file.

    Returns:
        dict with keys: 'items' (list[Item]), 'metadata', 'target_min', 'target_max',
        't_service', 'distributions'.
    """
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Fichier JSON invalide : {e}")

    if not isinstance(data, dict):
        raise ValueError("Structure de fichier .cotastack invalide.")

    if data.get("format") != "cotastack":
        raise ValueError("Le fichier fourni n'est pas un fichier de projet CotaStack valide.")

    raw_meta = data.get("metadata")
    metadata = raw_meta if isinstance(raw_meta, dict) else {}

    raw_targets = data.get("targets")
    targets = raw_targets if isinstance(raw_targets, dict) else {}

    raw_thermal = data.get("thermal")
    thermal = raw_thermal if isinstance(raw_thermal, dict) else {}

    raw_items = data.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("La liste des maillons est invalide.")

    def _parse_target(val: Any) -> float | None:
        if val is None:
            return None
        try:
            f = float(val)
            if not math.isfinite(f):
                raise ValueError()
            return f
        except (ValueError, TypeError):
            raise ValueError(f"Valeur de cible dimensionnelle invalide : {val}")

    target_min = _parse_target(targets.get("target_min"))
    target_max = _parse_target(targets.get("target_max"))
    if target_min is not None and target_max is not None and target_min > target_max:
        raise ValueError("target_min ne peut pas être strictement supérieur à target_max.")

    raw_t_serv = thermal.get("t_service", 20.0)
    try:
        t_service = float(raw_t_serv if raw_t_serv is not None else 20.0)
        if not math.isfinite(t_service) or t_service < -273.15:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError(f"Température de service invalide : {raw_t_serv}")

    items: list[Item] = []
    distributions: dict[str, str] = {}
    allowed_dists = {"normale", "uniforme", "triangulaire"}

    for idx, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue
        try:
            name = str(raw.get("name", f"Cote_{idx+1}")).strip()
            nominal = float(raw["nominal"])
            es = float(raw["es"])
            ei = float(raw["ei"])
            if not (math.isfinite(nominal) and math.isfinite(es) and math.isfinite(ei)):
                raise ValueError("Les cotes doivent être des valeurs numériques finies.")

            orientation = int(raw.get("orientation", 1))
            if orientation not in (1, -1):
                orientation = 1
            material = str(raw.get("material", "Acier (standard)"))
            dist = str(raw.get("distribution", "normale")).strip().lower()
            if dist not in allowed_dists:
                dist = "normale"

            item = Item(
                name=name,
                nominal=nominal,
                es=es,
                ei=ei,
                orientation=orientation,  # type: ignore
                material=material,
            )
            items.append(item)
            distributions[name] = dist
        except (KeyError, ValueError, TypeError) as err:
            raise ValueError(f"Erreur lors de la lecture du maillon {idx+1} : {err}")

    return {
        "items": items,
        "metadata": metadata,
        "target_min": target_min,
        "target_max": target_max,
        "t_service": t_service,
        "distributions": distributions,
    }
