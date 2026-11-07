# Bolt's Journal - Critical Performance Learnings

## 2026-11-08 - Default UUID4 Generation Overhead in Item Instantiation
**Learning:**
1. In `backend/models.py`, `Item` specifies `id: str = field(default_factory=lambda: str(uuid.uuid4()))`. When `MultiChainProject.resolve_chain_items()` converts assembly links into executable calculation items, omitting `id` triggered `uuid.uuid4()`, executing 16 bytes of OS CSPRNG reads (`posix.urandom`) and string formatting for every single link.
2. Profiling demonstrated that `uuid.uuid4()` consumed >50% of the CPU runtime in `resolve_chain_items()` and multi-chain evaluations (`evaluate_chain`, `evaluate_all`, `get_system_summary`).
3. Explicitly providing deterministic identifiers `id=f"{chain_id}_{idx}"` eliminates UUID generation overhead completely, yielding a ~65% speedup on `resolve_chain_items()` and ~46-52% speedup on multi-chain evaluation suites while preserving 100% backend test compatibility.
**Action:** When dynamically instantiating items in hot propagation or resolution paths, always pass deterministic IDs (`f"{context}_{index}"`) instead of letting dataclass field default factories generate cryptographic UUIDs.

## 2026-11-04 - Sorting Comparator Overhead and Division in ChainCalculator.calculate_pareto()
**Learning:**
1. In `backend/calculator.py`, `calculate_pareto` converted float percentages to strings and back (`lambda x: float(str(x["contribution_pct"]))`) during list sorting. This redundant string formatting and parsing added ~4x overhead to sorting within every single `calculate()` call.
2. In addition, computing `(item.IT ** 2 / total_variance) * 100` in the loop repeatedly performed float division instead of precomputing `inv_total_variance = 100.0 / total_variance`.
3. Precomputing `inv_total_variance`, caching `item.IT` into a local variable, and sorting directly on `x["contribution_pct"]` reduced `calculate_pareto` runtime by ~75% (from 1.23s to 0.29s for 100k calls) and sped up full `calculate()` execution by ~40-50% while preserving exact numerical output.
**Action:** In frequently evaluated mathematical sorting methods, never convert numeric values through `str(...)` in sorting key comparators, and prefer multiplying by a precalculated reciprocal rather than repeatedly dividing inside the loop.

## 2026-11-03 - Single-Pass Aggregation & Loop Elimination in ChainCalculator.calculate()
**Learning:**
1. In `backend/calculator.py`, calling `calculate()` executed redundant nested passes: `calculate_worst_case()` (which iterated 3 times over `items`), `calculate_rss()` (2 iterations), `calculate_pareto()` (re-summing `IT ** 2`), and `check_compliance()` (which re-called both `calculate_worst_case()` and `calculate_rss()`), accumulating up to 13 separate generator/loop passes over `items` per stack-up resolution.
2. By fusing nominal, mean, directional tolerances ($d_{\min}, d_{\max}$), and variance accumulation into a single $O(N)$ linear pass inside `calculate()`, and propagating precalculated bounds to `calculate_pareto` and `check_compliance`, evaluation time drops from 8.6 µs to 3.6 µs (~2.4x speedup, -58% CPU time) with strict bit-for-bit numerical parity across Worst-Case and RSS models.
**Action:** Always fuse multi-property aggregations of 1D chain items into a single linear loop and memoize/pass intermediate stack bounds to compliance checks rather than re-triggering sub-method calculations.

## 2026-11-01 - ISO 286 Range Lookup and Intermediate Float Rounding in Chains
**Learning:**
1. In `backend/iso_standards.py`, size step ranges `(low, high]` for ISO 286 fits form a strictly monotonically increasing partition up to 500 mm. Sequential linear scanning of tuples on every tolerance query incurs unnecessary iteration overhead. By precomputing a monotonic tuple of upper bounds `ISO_286_HIGH_BOUNDS`, `bisect.bisect_left` performs the boundary lookup in $O(\log N)$ with ~3x speedup while guaranteeing identical behavior across all intervals.
2. In `backend/models.py`, `Item.L_moy` explicitly applies `round(self.nominal + (self.es + self.ei) / 2.0, 5)` per item. Attempting a global closed-form vectorization of `simulate_thermal_sensitivity` by computing $J_{\text{moy}}(T) = J_{\text{nom}}(T) + \sum \text{orientation}_i \cdot \frac{ES_i + EI_i}{2}$ induces minute $10^{-5}$ float truncation divergence due to item-level intermediate rounding. Performance optimizations in CotaStack calculations must respect per-item intermediate rounding boundaries to preserve numerical parity.
**Action:** When optimizing tolerance lookups, prefer bisect/direct indexing over linear iteration. When optimizing chained calculations, verify whether dataclasses apply rounding properties (`round(..., 5)`) to avoid breaking float equality contracts.

## 2025-05-18 - Factorisation linéaire pour les balayages thermiques paramétriques 1D
**Learning:** Les tolérances dimensionnelles (ES, EI, IT) selon la norme ISO 1 ne dépendent pas de la température dans le modèle 1D standard ; seule la dimension nominale varie linéairement. Ré-instancier `ChainCalculator` et réallouer les objets `Item` pour chaque point d'un balayage paramétrique introduit $2 \times K$ instanciations inutiles et dégrade la réactivité Streamlit.
**Action:** Dans les balayages paramétriques (comme la sensibilité thermique continue $J(T)$), évaluer la chaîne de référence à $T_{\text{ref}}$ une seule fois, précalculer la pente globale $S_\alpha = \sum (\text{orientation}_i \cdot \text{nominal}_i \cdot \alpha_i)$, et translater les bornes arithmétiquement au lieu de recalculer la chaîne à chaque pas.
