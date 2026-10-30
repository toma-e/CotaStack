"""Thermal expansion module for differential temperature analysis in tolerance chains.

Reference standard: ISO 1 (Standard reference temperature for geometrical product specification is 20 °C).
Formulas:
    delta_T = T_service - T_ref
    delta_L = L_0 * alpha * delta_T
    L(T) = L_0 + delta_L = L_0 * (1 + alpha * delta_T)
"""

from dataclasses import dataclass
from backend.models import Item
from backend.calculator import ChainCalculator


# Linear thermal expansion coefficients (alpha) in K^-1 (or °C^-1)
# Expressed in standard SI units: value * 1e-6
THERMAL_COEFFICIENTS: dict[str, float] = {
    "Acier (standard)": 11.5e-6,
    "Acier Inox (austénitique 304/316)": 16.0e-6,
    "Aluminium (alliage 6000/7000)": 23.0e-6,
    "Laiton / Bronze": 18.0e-6,
    "Fonte (grise / GS)": 10.5e-6,
    "Titane (Grade 5)": 8.6e-6,
    "Polymère POM (Delrin / Acétal)": 110.0e-6,
    "Polymère PEEK": 47.0e-6,
    "Polymère PTFE (Téflon)": 130.0e-6,
}

# Alias mapping for friendly user inputs
MATERIAL_ALIASES: dict[str, str] = {
    "acier": "Acier (standard)",
    "acier standard": "Acier (standard)",
    "steel": "Acier (standard)",
    "inox": "Acier Inox (austénitique 304/316)",
    "inoxydable": "Acier Inox (austénitique 304/316)",
    "aluminium": "Aluminium (alliage 6000/7000)",
    "alu": "Aluminium (alliage 6000/7000)",
    "laiton": "Laiton / Bronze",
    "bronze": "Laiton / Bronze",
    "fonte": "Fonte (grise / GS)",
    "titane": "Titane (Grade 5)",
    "pom": "Polymère POM (Delrin / Acétal)",
    "delrin": "Polymère POM (Delrin / Acétal)",
    "peek": "Polymère PEEK",
    "ptfe": "Polymère PTFE (Téflon)",
}


@dataclass(slots=True)
class ThermalResult:
    """Detailed result of thermal expansion on a tolerance chain."""
    t_ref: float
    t_service: float
    delta_t: float
    nominal_at_t: float
    mean_at_t: float
    worst_case_minus_at_t: float
    worst_case_plus_at_t: float
    rss_minus_at_t: float
    rss_plus_at_t: float
    delta_j_nominal: float  # Difference vs 20 °C
    delta_j_mean: float
    items_detail: list[dict]


def get_available_materials() -> list[str]:
    """Return list of standard materials available in the thermal catalog."""
    return list(THERMAL_COEFFICIENTS.keys())


def get_material_alpha(material_name: str) -> float:
    """Retrieve thermal expansion coefficient alpha for a material name or alias.

    Args:
        material_name: Name or alias of material (e.g. 'Alu', 'Acier (standard)').

    Returns:
        alpha in K^-1.
    """
    clean_name = material_name.strip()
    if clean_name in THERMAL_COEFFICIENTS:
        return THERMAL_COEFFICIENTS[clean_name]

    alias_key = clean_name.lower()
    if alias_key in MATERIAL_ALIASES:
        canonical = MATERIAL_ALIASES[alias_key]
        return THERMAL_COEFFICIENTS[canonical]

    raise ValueError(
        f"Matériau inconnu '{material_name}'. Matériaux disponibles : {list(THERMAL_COEFFICIENTS.keys())}"
    )


def calculate_thermal_expansion(
    nominal: float,
    material: str,
    t_service: float,
    t_ref: float = 20.0,
) -> float:
    """Calculate linear dimensional change delta_L due to temperature change.

    Args:
        nominal: Basic size at reference temperature (mm).
        material: Material identifier.
        t_service: Operating temperature (°C).
        t_ref: Reference temperature (°C, standard 20.0).

    Returns:
        delta_L in mm.
    """
    alpha = get_material_alpha(material)
    delta_t = t_service - t_ref
    return nominal * alpha * delta_t


def calculate_thermal_chain(
    items: list[Item],
    t_service: float,
    t_ref: float = 20.0,
) -> ThermalResult:
    """Calculate the tolerance chain results taking thermal expansion into account.

    Each item's nominal and mean values are expanded according to its material alpha.
    Tolerances (ES, EI, IT) are preserved, translated onto the expanded nominal size.

    Args:
        items: List of tolerance chain Items.
        t_service: Service operating temperature in °C.
        t_ref: Reference calibration temperature in °C (default: 20 °C).

    Returns:
        ThermalResult containing expanded chain metrics and item details.
    """
    delta_t = t_service - t_ref

    # 1. Base calculation at reference temperature (20 °C)
    calc_ref = ChainCalculator(items)
    res_ref = calc_ref.calculate()

    # 2. Expanded items at service temperature
    expanded_items: list[Item] = []
    items_detail: list[dict] = []

    for item in items:
        mat = item.material if item.material else "Acier (standard)"
        alpha = get_material_alpha(mat)
        delta_l = item.nominal * alpha * delta_t
        nominal_t = item.nominal + delta_l

        expanded_item = Item(
            name=item.name,
            nominal=nominal_t,
            es=item.es,
            ei=item.ei,
            orientation=item.orientation,
            material=mat,
        )
        expanded_items.append(expanded_item)

        items_detail.append({
            "name": item.name,
            "material": mat,
            "alpha": alpha,
            "nominal_ref": item.nominal,
            "delta_l": delta_l,
            "nominal_at_t": nominal_t,
            "orientation": item.orientation,
        })

    # 3. Chain calculation with expanded dimensions
    calc_t = ChainCalculator(expanded_items)
    res_t = calc_t.calculate()

    delta_j_nom = res_t.nominal - res_ref.nominal
    delta_j_moy = res_t.mean - res_ref.mean

    return ThermalResult(
        t_ref=t_ref,
        t_service=t_service,
        delta_t=delta_t,
        nominal_at_t=round(res_t.nominal, 5),
        mean_at_t=round(res_t.mean, 5),
        worst_case_minus_at_t=round(res_t.worst_case_minus, 5),
        worst_case_plus_at_t=round(res_t.worst_case_plus, 5),
        rss_minus_at_t=round(res_t.rss_minus, 5),
        rss_plus_at_t=round(res_t.rss_plus, 5),
        delta_j_nominal=round(delta_j_nom, 5),
        delta_j_mean=round(delta_j_moy, 5),
        items_detail=items_detail,
    )


def simulate_thermal_sensitivity(
    items: list[Item],
    t_min: float = -20.0,
    t_max: float = 120.0,
    num_points: int = 50,
    t_ref: float = 20.0,
) -> list[dict]:
    """Simulate chain game evolution J(T) over a temperature range.

    Returns:
        List of dicts with: temperature, nominal, wc_min, wc_max, rss_min, rss_max.
    """
    if t_min >= t_max:
        raise ValueError(f"t_min ({t_min}) must be < t_max ({t_max})")

    step = (t_max - t_min) / max(1, num_points - 1)
    curve_data: list[dict] = []

    for i in range(num_points):
        temp = t_min + i * step
        res = calculate_thermal_chain(items, t_service=temp, t_ref=t_ref)
        curve_data.append({
            "temperature": round(temp, 1),
            "nominal": res.nominal_at_t,
            "mean": res.mean_at_t,
            "wc_min": res.worst_case_minus_at_t,
            "wc_max": res.worst_case_plus_at_t,
            "rss_min": res.rss_minus_at_t,
            "rss_max": res.rss_plus_at_t,
        })

    return curve_data
