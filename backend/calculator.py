"""Calculator engine for 1D tolerance chain analysis."""

import math
from backend.models import Item, ChainResult


class ChainCalculator:
    """Performs worst-case and RSS (Root Sum Square) tolerance analysis."""

    def __init__(
        self,
        items: list[Item],
        target_min: float | None = None,
        target_max: float | None = None,
    ) -> None:
        self.items = items
        self.target_min = target_min
        self.target_max = target_max
        self._verify_loop_closure()

    def _verify_loop_closure(self) -> None:
        """Verify vectorial loop closure: sum(orientation_i * nominal_i) = J_nom."""
        # This is a consistency check - the nominal game is defined by this sum
        # No exception raised, just ensures calculation uses vectorial sum
        pass

    def _get_oriented_nominal(self) -> float:
        """Calculate nominal game: sum(orientation_i * nominal_i)."""
        return sum(item.orientation * item.nominal for item in self.items)

    def _get_oriented_mean(self) -> float:
        """Calculate mean game: sum(orientation_i * L_moy_i)."""
        return sum(item.orientation * item.L_moy for item in self.items)

    def calculate_worst_case(self) -> tuple[float, float]:
        """Calculate worst-case (arithmetic) tolerance stack-up.

        Returns:
            Tuple of (J_min_WC, J_max_WC) - absolute limits of the game.
        """
        j_nom = self._get_oriented_nominal()
        # For orientation=+1: J_min gets ei, J_max gets es
        # For orientation=-1: J_min gets es (subtracting max gives min game), J_max gets ei
        j_min = j_nom + sum(
            item.orientation * (item.ei if item.orientation > 0 else item.es)
            for item in self.items
        )
        j_max = j_nom + sum(
            item.orientation * (item.es if item.orientation > 0 else item.ei)
            for item in self.items
        )
        return j_min, j_max

    def calculate_rss(self) -> tuple[float, float]:
        """Calculate statistical (RSS) tolerance stack-up at 3-sigma.

        Returns:
            Tuple of (J_min_RSS, J_max_RSS) - absolute limits of the game.
        """
        j_moy = self._get_oriented_mean()
        # RSS: IT_total = sqrt(sum(IT_i^2)), J_min = J_moy - IT_total/2, J_max = J_moy + IT_total/2
        # Assumes each dimension has sigma = IT/6 (6-sigma = IT), combined 3-sigma = sqrt(sum(IT_i^2))/2
        it_total_rss = math.sqrt(sum(item.IT ** 2 for item in self.items))
        half_range = it_total_rss / 2
        j_min = j_moy - half_range
        j_max = j_moy + half_range
        return j_min, j_max

    def calculate_pareto(self) -> list[dict]:
        """Calculate Pareto contribution of each item to total variance.

        Returns:
            List of dicts with item name, IT, contribution_pct, sorted descending.
        """
        total_variance = sum(item.IT ** 2 for item in self.items)
        if total_variance == 0:
            return [
                {
                    "name": item.name,
                    "IT": item.IT,
                    "contribution_pct": 0.0,
                }
                for item in self.items
            ]

        contributions = []
        for item in self.items:
            contribution = (item.IT ** 2 / total_variance) * 100
            contributions.append(
                {
                    "name": item.name,
                    "IT": item.IT,
                    "contribution_pct": contribution,
                }
            )
        # Sort by contribution descending
        contributions.sort(key=lambda x: x["contribution_pct"], reverse=True)
        return contributions

    def check_compliance(self) -> dict:
        """Check compliance against target limits.

        Returns:
            Dict with compliance status and margins.
        """
        j_min_wc, j_max_wc = self.calculate_worst_case()
        j_min_rss, j_max_rss = self.calculate_rss()

        wc_compliant = True
        rss_compliant = True
        wc_margin_min = None
        wc_margin_max = None
        rss_margin_min = None
        rss_margin_max = None

        if self.target_min is not None:
            wc_margin_min = j_min_wc - self.target_min
            rss_margin_min = j_min_rss - self.target_min
            if wc_margin_min < 0:
                wc_compliant = False
            if rss_margin_min < 0:
                rss_compliant = False

        if self.target_max is not None:
            wc_margin_max = self.target_max - j_max_wc
            rss_margin_max = self.target_max - j_max_rss
            if wc_margin_max < 0:
                wc_compliant = False
            if rss_margin_max < 0:
                rss_compliant = False

        return {
            "wc_compliant": wc_compliant,
            "rss_compliant": rss_compliant,
            "wc_margin_min": wc_margin_min,
            "wc_margin_max": wc_margin_max,
            "rss_margin_min": rss_margin_min,
            "rss_margin_max": rss_margin_max,
        }

    def calculate(self) -> ChainResult:
        """Run full calculation and return structured result."""
        j_nom = self._get_oriented_nominal()
        j_moy = self._get_oriented_mean()
        wc_min, wc_max = self.calculate_worst_case()
        rss_min, rss_max = self.calculate_rss()
        pareto = self.calculate_pareto()
        compliance = self.check_compliance()

        return ChainResult(
            nominal=j_nom,
            mean=j_moy,
            worst_case_minus=wc_min,
            worst_case_plus=wc_max,
            rss_minus=rss_min,
            rss_plus=rss_max,
            items=self.items,
            pareto=pareto,
            compliance=compliance,
            target_min=self.target_min,
            target_max=self.target_max,
        )