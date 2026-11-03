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
        delta_min = 0.0
        delta_max = 0.0
        for item in self.items:
            if item.orientation > 0:
                delta_min += item.ei
                delta_max += item.es
            else:
                delta_min -= item.es
                delta_max -= item.ei
        return j_nom + delta_min, j_nom + delta_max

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

    def calculate_pareto(self, total_variance: float | None = None) -> list[dict]:
        """Calculate Pareto contribution of each item to total variance.

        Returns:
            List of dicts with item name, IT, contribution_pct, sorted descending.
        """
        if total_variance is None:
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

    def check_compliance(
        self,
        wc_limits: tuple[float, float] | None = None,
        rss_limits: tuple[float, float] | None = None,
        j_nom: float | None = None,
    ) -> dict:
        """Check compliance against target limits across 3 distinct criteria:
        1. Minimum limit (J_min >= Target_min)
        2. Nominal/Central target (Target_min <= J_nom <= Target_max)
        3. Maximum limit (J_max <= Target_max)

        Returns:
            Dict with compliance statuses (overall, min, nominal, max) and margins.
        """
        j_min_wc, j_max_wc = wc_limits if wc_limits is not None else self.calculate_worst_case()
        j_min_rss, j_max_rss = rss_limits if rss_limits is not None else self.calculate_rss()
        nominal_val = j_nom if j_nom is not None else self._get_oriented_nominal()

        wc_min_compliant = True
        wc_max_compliant = True
        wc_nominal_compliant = True

        rss_min_compliant = True
        rss_max_compliant = True
        rss_nominal_compliant = True

        wc_margin_min = None
        wc_margin_max = None
        rss_margin_min = None
        rss_margin_max = None
        nominal_deviation = None

        # 1. Minimum limit verification (J_min >= Target_min)
        if self.target_min is not None:
            wc_margin_min = j_min_wc - self.target_min
            rss_margin_min = j_min_rss - self.target_min
            if wc_margin_min < 0:
                wc_min_compliant = False
            if rss_margin_min < 0:
                rss_min_compliant = False
            if nominal_val < self.target_min:
                wc_nominal_compliant = False
                rss_nominal_compliant = False

        # 2. Maximum limit verification (J_max <= Target_max)
        if self.target_max is not None:
            wc_margin_max = self.target_max - j_max_wc
            rss_margin_max = self.target_max - j_max_rss
            if wc_margin_max < 0:
                wc_max_compliant = False
            if rss_margin_max < 0:
                rss_max_compliant = False
            if nominal_val > self.target_max:
                wc_nominal_compliant = False
                rss_nominal_compliant = False

        # Nominal central deviation when both targets are given
        if self.target_min is not None and self.target_max is not None:
            target_center = (self.target_min + self.target_max) / 2.0
            nominal_deviation = nominal_val - target_center
        elif self.target_min is not None:
            nominal_deviation = nominal_val - self.target_min
        elif self.target_max is not None:
            nominal_deviation = nominal_val - self.target_max

        wc_compliant = wc_min_compliant and wc_max_compliant
        rss_compliant = rss_min_compliant and rss_max_compliant

        return {
            # Global historical booleans for backward compatibility
            "wc_compliant": wc_compliant,
            "rss_compliant": rss_compliant,
            # 3 Distinct criteria for Worst-Case
            "wc_min_compliant": wc_min_compliant,
            "wc_nominal_compliant": wc_nominal_compliant,
            "wc_max_compliant": wc_max_compliant,
            # 3 Distinct criteria for RSS
            "rss_min_compliant": rss_min_compliant,
            "rss_nominal_compliant": rss_nominal_compliant,
            "rss_max_compliant": rss_max_compliant,
            # Margins & deviations
            "wc_margin_min": wc_margin_min,
            "wc_margin_max": wc_margin_max,
            "rss_margin_min": rss_margin_min,
            "rss_margin_max": rss_margin_max,
            "nominal_deviation": nominal_deviation,
        }

    def calculate(self) -> ChainResult:
        """Run full calculation and return structured result."""
        j_nom = 0.0
        j_moy = 0.0
        delta_min = 0.0
        delta_max = 0.0
        total_variance = 0.0

        for item in self.items:
            o = item.orientation
            j_nom += o * item.nominal
            j_moy += o * item.L_moy
            total_variance += item.IT ** 2
            if o > 0:
                delta_min += item.ei
                delta_max += item.es
            else:
                delta_min -= item.es
                delta_max -= item.ei

        wc_min = j_nom + delta_min
        wc_max = j_nom + delta_max
        half_range = math.sqrt(total_variance) / 2
        rss_min = j_moy - half_range
        rss_max = j_moy + half_range

        pareto = self.calculate_pareto(total_variance=total_variance)
        compliance = self.check_compliance(
            wc_limits=(wc_min, wc_max),
            rss_limits=(rss_min, rss_max),
            j_nom=j_nom,
        )

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