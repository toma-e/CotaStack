"""Geometric Product Specifications (ISO GPS) module: 1D geometric tolerances & Maximum Material Requirement (MMR Ⓜ).

Reference standards:
    - ISO 2692: Geometrical Product Specifications (GPS) - Maximum material requirement (MMR),
      least material requirement (LMR) and reciprocity requirement (RPR).
    - ISO 1101: Geometrical Product Specifications (GPS) - Geometrical tolerancing.
    - ASME Y14.5: Dimensioning and Tolerancing (MMC modifier).

Key concepts:
    - Maximum Material State (MMS):
        * Shaft (male feature of size): MMS = nominal + es = d_max
        * Hole (female feature of size): MMS = nominal + ei = D_min
    - Bonus tolerance (delta_t):
        * Shaft: Bonus = max(0, d_max - d_actual)
        * Hole: Bonus = max(0, D_actual - D_min)
        * Max Bonus = IT_size = es - ei
    - Total allowable geometric tolerance:
        * t_total = t_base + Bonus
    - Virtual Condition (assembly boundary):
        * Shaft: Vc = d_max + t_base
        * Hole: Vc = D_min - t_base
"""

from dataclasses import dataclass
from typing import Literal


FeatureType = Literal["alesage", "arbre", "plan"]
GeometricToleranceType = Literal[
    "localisation",
    "parallelisme",
    "perpendicularite",
    "coaxialite",
    "battement",
    "symetrie",
]


@dataclass(slots=True)
class GeometricSpec:
    """Specification of a geometrical tolerance with optional Maximum Material Requirement (MMR Ⓜ)."""
    name: str
    feature_type: FeatureType
    tolerance_type: GeometricToleranceType
    nominal_size: float  # mm
    es: float            # mm
    ei: float            # mm
    base_tolerance: float  # t0 in mm (e.g. 0.05)
    mmr: bool = True     # True if Ⓜ modifier is present


@dataclass(slots=True)
class GeometricResult:
    """Calculated metrics for a geometrical tolerance under ISO GPS rules."""
    spec: GeometricSpec
    mms: float           # Maximum Material State (mm)
    lms: float           # Least Material State (mm)
    size_it: float       # Dimensional IT = es - ei (mm)
    max_bonus: float     # Maximum possible bonus (mm)
    virtual_condition: float  # Boundary dimension Vc (mm)
    actual_size: float | None # Evaluated actual dimension if given
    actual_bonus: float       # Bonus at actual_size (0 if at MMS or MMR disabled)
    total_geometric_tolerance: float  # t0 + actual_bonus (mm)
    equivalent_1d_it: float   # 1D tolerance interval contribution (mm)
    explanation: str


@dataclass(slots=True)
class AssemblyVerificationResult:
    """Verification of assemblability under combined size and geometric MMC tolerances."""
    hole_vc: float
    shaft_vc: float
    guaranteed_min_clearance: float
    is_assemblable: bool
    verdict: str


def calculate_mms_lms(
    feature_type: FeatureType,
    nominal: float,
    es: float,
    ei: float,
) -> tuple[float, float]:
    """Calculate Maximum Material State (MMS) and Least Material State (LMS) in mm."""
    if nominal <= 0:
        raise ValueError(f"La cote nominale doit être > 0, reçu : {nominal}")
    if es < ei:
        raise ValueError(f"es ({es}) doit être >= ei ({ei})")

    d_max = nominal + es
    d_min = nominal + ei

    if feature_type == "arbre":
        # Shaft maximum material = largest size
        return round(d_max, 5), round(d_min, 5)
    elif feature_type == "alesage":
        # Hole maximum material = smallest hole
        return round(d_min, 5), round(d_max, 5)
    else:  # "plan" / surface
        return round(nominal, 5), round(nominal, 5)


def calculate_virtual_condition(
    feature_type: FeatureType,
    nominal: float,
    es: float,
    ei: float,
    base_tolerance: float,
) -> float:
    """Calculate Virtual Condition (envelope boundary) under MMR (ISO 2692).

    Shaft Vc = d_max + t0 (outer envelope boundary)
    Hole Vc = D_min - t0 (inner mating boundary)
    """
    if base_tolerance < 0:
        raise ValueError(f"La tolérance géométrique de base doit être >= 0, reçu : {base_tolerance}")

    mms, _ = calculate_mms_lms(feature_type, nominal, es, ei)
    if feature_type == "arbre":
        return round(mms + base_tolerance, 5)
    elif feature_type == "alesage":
        return round(mms - base_tolerance, 5)
    else:
        return round(nominal + base_tolerance, 5)


def evaluate_geometric_spec(
    spec: GeometricSpec,
    actual_size: float | None = None,
) -> GeometricResult:
    """Evaluate full geometric tolerance, bonus tolerance and 1D equivalent stack-up.

    Args:
        spec: GeometricSpec dataclass.
        actual_size: Optional actual manufactured dimension in mm. If None, evaluated at MMS (worst case).

    Returns:
        GeometricResult dataclass.
    """
    if spec.base_tolerance < 0:
        raise ValueError(f"La tolérance de base doit être >= 0, reçu : {spec.base_tolerance}")

    mms, lms = calculate_mms_lms(spec.feature_type, spec.nominal_size, spec.es, spec.ei)
    size_it = round(spec.es - spec.ei, 5)
    vc = calculate_virtual_condition(
        spec.feature_type,
        spec.nominal_size,
        spec.es,
        spec.ei,
        spec.base_tolerance,
    )

    max_bonus = size_it if (spec.mmr and spec.feature_type in ("arbre", "alesage")) else 0.0

    # Actual size evaluation
    eval_size = actual_size if actual_size is not None else mms

    actual_bonus = 0.0
    if spec.mmr and spec.feature_type in ("arbre", "alesage"):
        if spec.feature_type == "arbre":
            # As shaft becomes smaller than d_max, bonus increases
            actual_bonus = max(0.0, min(max_bonus, mms - eval_size))
        elif spec.feature_type == "alesage":
            # As hole becomes larger than D_min, bonus increases
            actual_bonus = max(0.0, min(max_bonus, eval_size - mms))

    actual_bonus = round(actual_bonus, 5)
    total_geom = round(spec.base_tolerance + actual_bonus, 5)

    # In 1D tolerance chain: geometric tolerance contributes as a symmetric interval +/- (t/2) -> IT = total_geom
    equiv_1d = total_geom

    # Explanation construction
    mod_symbol = " Ⓜ" if spec.mmr else ""
    if spec.mmr:
        expl = (
            f"Spécification {spec.tolerance_type.upper()} de {spec.base_tolerance:.3f} mm{mod_symbol} sur {spec.feature_type}. "
            f"Au pire des cas matière (MMS = {mms:.3f} mm), t = {spec.base_tolerance:.3f} mm. "
            f"À la dimension évaluée ({eval_size:.3f} mm), bonus de +{actual_bonus:.3f} mm accordé, "
            f"portant la tolérance géométrique admissible à {total_geom:.3f} mm. "
            f"État virtuel d'assemblage Vc = {vc:.3f} mm."
        )
    else:
        expl = (
            f"Spécification {spec.tolerance_type.upper()} stricte (RFS) de {spec.base_tolerance:.3f} mm sur {spec.feature_type}. "
            f"Aucun bonus matière admissible. Tolérance constante = {total_geom:.3f} mm."
        )

    return GeometricResult(
        spec=spec,
        mms=mms,
        lms=lms,
        size_it=size_it,
        max_bonus=max_bonus,
        virtual_condition=vc,
        actual_size=actual_size,
        actual_bonus=actual_bonus,
        total_geometric_tolerance=total_geom,
        equivalent_1d_it=equiv_1d,
        explanation=expl,
    )


def verify_assembly_interface(
    hole_spec: GeometricSpec,
    shaft_spec: GeometricSpec,
) -> AssemblyVerificationResult:
    """Verify guaranteed assembly of a mating pair under ISO 2692 MMR rules.

    Assembly is 100% physically guaranteed in the worst-case condition if:
        Vc_hole >= Vc_shaft
        i.e. (D_min - t0_hole) - (d_max + t0_shaft) >= 0
    """
    if hole_spec.feature_type != "alesage":
        raise ValueError("hole_spec doit avoir feature_type='alesage'")
    if shaft_spec.feature_type != "arbre":
        raise ValueError("shaft_spec doit avoir feature_type='arbre'")

    hole_vc = calculate_virtual_condition(
        "alesage", hole_spec.nominal_size, hole_spec.es, hole_spec.ei, hole_spec.base_tolerance
    )
    shaft_vc = calculate_virtual_condition(
        "arbre", shaft_spec.nominal_size, shaft_spec.es, shaft_spec.ei, shaft_spec.base_tolerance
    )

    clearance = round(hole_vc - shaft_vc, 5)
    is_ok = clearance >= 0.0

    if is_ok:
        verdict = (
            f"✅ Assemblage 100% garanti sous exigence du maximum de matière (MMR Ⓜ). "
            f"Marge minimale à l'état virtuel : {clearance:+.4f} mm."
        )
    else:
        verdict = (
            f"❌ Risque de collision à l'état virtuel pire cas matière ! "
            f"Interférence potentielle de {abs(clearance):.4f} mm. "
            f"Resserrer la tolérance géométrique ou dimensionnelle."
        )

    return AssemblyVerificationResult(
        hole_vc=hole_vc,
        shaft_vc=shaft_vc,
        guaranteed_min_clearance=clearance,
        is_assemblable=is_ok,
        verdict=verdict,
    )
