"""Monte Carlo stochastic simulation engine for advanced tolerance stack-up analysis.

Simulates tolerance chains over large sample populations (e.g. 100,000 runs)
using parameterized probability distributions (Normal, Uniform, Triangular).
Computes real defect rates in PPM (parts per million) and process capability indices (Cp, Cpk).
"""

from dataclasses import dataclass
from typing import Literal
import numpy as np
from backend.models import Item


DistributionType = Literal["normale", "uniforme", "triangulaire"]


@dataclass(slots=True)
class MonteCarloResult:
    """Statistical summary of Monte Carlo simulation runs."""
    num_simulations: int
    mean: float
    std_dev: float
    min_simulated: float
    max_simulated: float
    p001: float  # 0.135th percentile (-3 sigma equivalent)
    p50: float   # Median
    p999: float  # 99.865th percentile (+3 sigma equivalent)
    target_min: float | None
    target_max: float | None
    defect_count: int
    defect_rate_pct: float
    defect_ppm: float
    cp: float | None
    cpk: float | None
    samples_summary: np.ndarray  # Reduced array for fast histogram plotting


def _draw_item_samples(
    item: Item,
    num_simulations: int,
    distribution: DistributionType = "normale",
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Generate sample array for a single item dimension according to distribution."""
    if rng is None:
        rng = np.random.default_rng()

    lower = item.lower_limit  # nominal + ei
    upper = item.upper_limit  # nominal + es
    it = item.IT

    if it <= 0:
        return np.full(num_simulations, item.nominal)

    dist = distribution.lower()
    if dist == "normale":
        # Process centered on mean with 6-sigma = IT (Cp = 1.0)
        mean = item.L_moy
        sigma = it / 6.0
        return rng.normal(mean, sigma, size=num_simulations)
    elif dist == "uniforme":
        return rng.uniform(lower, upper, size=num_simulations)
    elif dist == "triangulaire":
        # Mode at nominal size
        mode = item.nominal
        return rng.triangular(lower, mode, upper, size=num_simulations)
    else:
        raise ValueError(
            f"Distribution inconnue '{distribution}'. Distributions supportées : 'normale', 'uniforme', 'triangulaire'"
        )


def run_monte_carlo(
    items: list[Item],
    num_simulations: int = 100_000,
    target_min: float | None = None,
    target_max: float | None = None,
    distributions: dict[str, DistributionType] | None = None,
    seed: int | None = 42,
) -> MonteCarloResult:
    """Run vectorised Monte Carlo simulation on the 1D tolerance chain.

    Args:
        items: List of tolerance chain Items.
        num_simulations: Number of synthetic assemblies (default: 100,000).
        target_min: Optional lower functional game limit.
        target_max: Optional upper functional game limit.
        distributions: Optional mapping of item name to distribution type.
        seed: Random generator seed for repeatable runs.

    Returns:
        MonteCarloResult with statistical KPIs, PPM and capability indices.
    """
    if not items:
        raise ValueError("La liste des maillons ne peut pas être vide.")
    if num_simulations < 100:
        raise ValueError("Le nombre de simulations doit être au moins de 100.")

    rng = np.random.default_rng(seed)
    distributions = distributions or {}

    # Initialize total game vector
    total_game = np.zeros(num_simulations, dtype=np.float64)

    for item in items:
        dist_type = distributions.get(item.name, "normale")
        samples = _draw_item_samples(item, num_simulations, dist_type, rng)
        total_game += item.orientation * samples

    # Statistical properties
    mean_val = float(np.mean(total_game))
    std_val = float(np.std(total_game, ddof=1))
    min_val = float(np.min(total_game))
    max_val = float(np.max(total_game))

    # Percentiles
    p001 = float(np.percentile(total_game, 0.135))
    p50 = float(np.percentile(total_game, 50.0))
    p999 = float(np.percentile(total_game, 99.865))

    # Non-compliance & PPM
    defect_mask = np.zeros(num_simulations, dtype=bool)
    if target_min is not None:
        defect_mask |= (total_game < target_min)
    if target_max is not None:
        defect_mask |= (total_game > target_max)

    defect_count = int(np.sum(defect_mask))
    defect_rate_pct = (defect_count / num_simulations) * 100.0
    defect_ppm = (defect_count / num_simulations) * 1_000_000.0

    # Capability indices Cp and Cpk
    cp: float | None = None
    cpk: float | None = None

    if target_min is not None and target_max is not None and std_val > 0:
        tolerance_interval = target_max - target_min
        cp = tolerance_interval / (6.0 * std_val)
        cpu = (target_max - mean_val) / (3.0 * std_val)
        cpl = (mean_val - target_min) / (3.0 * std_val)
        cpk = min(cpu, cpl)

    # For fast frontend plotting, retain a 5,000-point representative subsample
    subsample_size = min(5000, num_simulations)
    samples_subsample = rng.choice(total_game, size=subsample_size, replace=False)

    return MonteCarloResult(
        num_simulations=num_simulations,
        mean=round(mean_val, 5),
        std_dev=round(std_val, 5),
        min_simulated=round(min_val, 5),
        max_simulated=round(max_val, 5),
        p001=round(p001, 5),
        p50=round(p50, 5),
        p999=round(p999, 5),
        target_min=target_min,
        target_max=target_max,
        defect_count=defect_count,
        defect_rate_pct=round(defect_rate_pct, 4),
        defect_ppm=round(defect_ppm, 1),
        cp=round(cp, 3) if cp is not None else None,
        cpk=round(cpk, 3) if cpk is not None else None,
        samples_summary=samples_subsample,
    )
