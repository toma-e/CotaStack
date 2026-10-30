"""Tolerance synthesis and inverse tolerance allocation engine for 1D chains.

Solves the inverse stack-up problem:
Given a target assembly tolerance (IT_target = J_max - J_min),
automatically allocates optimal individual component tolerances (IT_i)
based on proportional scaling, ISO tolerance grade sizing, or manufacturing cost weighting.
"""

from dataclasses import dataclass
from typing import Literal
from backend.models import Item


AllocationMethod = Literal["proportionnelle", "cout_usinage", "degré_iso"]
StackupMode = Literal["wc", "rss"]


@dataclass(slots=True)
class AllocatedLink:
    """Individual item tolerance allocation result."""
    name: str
    nominal: float
    orientation: int
    current_it: float
    new_it: float
    new_es: float
    new_ei: float
    delta_it: float
    delta_it_pct: float
    cost_weight: float


@dataclass(slots=True)
class AllocationResult:
    """Complete summary of inverse tolerance allocation."""
    target_it: float
    mode: StackupMode
    method: AllocationMethod
    allocated_links: list[AllocatedLink]
    total_it_wc: float
    total_it_rss: float
    achieved_it: float


def _compute_iso_factor(nominal: float) -> float:
    """Compute standard ISO tolerance factor i = 0.45 * D^(1/3) + 0.001 * D (µm unit)."""
    d = max(0.5, nominal)
    return 0.45 * (d ** (1.0 / 3.0)) + 0.001 * d


def allocate_tolerances(
    items: list[Item],
    target_it: float,
    mode: StackupMode = "wc",
    method: AllocationMethod = "proportionnelle",
    cost_weights: dict[str, float] | None = None,
) -> AllocationResult:
    """Perform inverse tolerance allocation on a list of Items.

    Args:
        items: List of tolerance chain Items.
        target_it: Desired total assembly tolerance interval (mm). Must be > 0.
        mode: Stack-up constraint rule: 'wc' (Worst-Case sum IT_i) or 'rss' (sqrt(sum IT_i^2)).
        method: Allocation strategy:
            - 'proportionnelle': scales current IT_i proportionally to match target.
            - 'cout_usinage': allocates according to manufacturing difficulty weights.
            - 'degré_iso': distributes proportionally to ISO size factors (larger parts get larger IT).
        cost_weights: Optional difficulty weights per item name (e.g. 1.0=standard, 0.5=easy, 2.0=costly).

    Returns:
        AllocationResult with newly calculated IT, ES and EI for each component.
    """
    if not items:
        raise ValueError("La liste des maillons ne peut pas être vide.")
    if target_it <= 0:
        raise ValueError(f"L'intervalle cible doit être strictement positif (> 0), reçu : {target_it}")

    n = len(items)
    cost_weights = cost_weights or {}

    # 1. Determine raw weighting factors w_i according to method
    factors: list[float] = []
    for it in items:
        w_user = cost_weights.get(it.name, 1.0)
        if w_user <= 0:
            w_user = 1.0

        if method == "proportionnelle":
            # Proportional to existing IT (fallback to 0.1 if current IT is 0)
            base_it = it.IT if it.IT > 0 else 0.1
            factors.append(base_it)
        elif method == "degré_iso":
            # Proportional to ISO cubic root sizing factor
            factors.append(_compute_iso_factor(it.nominal))
        elif method == "cout_usinage":
            # Cost-minimization principle:
            # Under reciprocal cost model C_i(IT_i) = w_i / IT_i,
            # for WC sum(IT_i) = IT_target, optimal IT_i is proportional to sqrt(w_i)
            # Higher weight w_i (costly to tighten) -> gets larger tolerance.
            factors.append(w_user ** 0.5)
        else:
            raise ValueError(f"Méthode d'allocation inconnue : '{method}'")

    # 2. Normalize factors to satisfy the stack-up constraint
    if mode == "wc":
        # Sum(IT_new) = target_it
        sum_factors = sum(factors)
        new_its = [(f / sum_factors) * target_it for f in factors]
    elif mode == "rss":
        # Sqrt(Sum(IT_new^2)) = target_it
        sum_sq_factors = sum(f ** 2 for f in factors)
        scale = target_it / (sum_sq_factors ** 0.5)
        new_its = [f * scale for f in factors]
    else:
        raise ValueError(f"Mode de cumul inconnu : '{mode}'. Choix possibles : 'wc', 'rss'")

    # 3. Construct individual results preserving tolerance centering
    allocated_links: list[AllocatedLink] = []
    for it, new_it in zip(items, new_its):
        curr_it = it.IT
        delta = new_it - curr_it
        delta_pct = (delta / curr_it * 100.0) if curr_it > 0 else 0.0

        # Preserve symmetry: half above, half below the mean
        mean_offset = (it.es + it.ei) / 2.0
        new_es = round(mean_offset + new_it / 2.0, 5)
        new_ei = round(mean_offset - new_it / 2.0, 5)

        allocated_links.append(AllocatedLink(
            name=it.name,
            nominal=it.nominal,
            orientation=it.orientation,
            current_it=round(curr_it, 5),
            new_it=round(new_it, 5),
            new_es=new_es,
            new_ei=new_ei,
            delta_it=round(delta, 5),
            delta_it_pct=round(delta_pct, 1),
            cost_weight=cost_weights.get(it.name, 1.0),
        ))

    # 4. Global resulting stack-ups
    tot_wc = sum(l.new_it for l in allocated_links)
    tot_rss = (sum(l.new_it ** 2 for l in allocated_links)) ** 0.5
    achieved = tot_wc if mode == "wc" else tot_rss

    return AllocationResult(
        target_it=round(target_it, 5),
        mode=mode,
        method=method,
        allocated_links=allocated_links,
        total_it_wc=round(tot_wc, 5),
        total_it_rss=round(tot_rss, 5),
        achieved_it=round(achieved, 5),
    )
