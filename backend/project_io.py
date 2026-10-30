"""Project serialization module for CotaStack (.cotastack JSON format).

Provides privacy-first local project save and load functionality.
No remote database required.
"""

import json
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

    metadata = data.get("metadata", {})
    targets = data.get("targets", {})
    thermal = data.get("thermal", {})
    raw_items = data.get("items", [])

    if not isinstance(raw_items, list):
        raise ValueError("La liste des maillons est invalide.")

    items: list[Item] = []
    distributions: dict[str, str] = {}

    for idx, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue
        try:
            name = str(raw.get("name", f"Cote_{idx+1}")).strip()
            nominal = float(raw["nominal"])
            es = float(raw["es"])
            ei = float(raw["ei"])
            orientation = int(raw.get("orientation", 1))
            if orientation not in (1, -1):
                orientation = 1
            material = str(raw.get("material", "Acier (standard)"))
            dist = str(raw.get("distribution", "normale"))

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
        "target_min": targets.get("target_min"),
        "target_max": targets.get("target_max"),
        "t_service": float(thermal.get("t_service", 20.0)),
        "distributions": distributions,
    }
