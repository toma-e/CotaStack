"""CotaStack - Calculateur de chaînes de cotes 1D."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats

from backend.models import Item, ChainResult
from backend.calculator import ChainCalculator
from backend.iso_standards import (
    get_available_iso286_symbols,
    get_iso286_limits,
    get_iso2768_linear_tolerance,
)
from backend.thermal import (
    get_available_materials,
    calculate_thermal_chain,
    simulate_thermal_sensitivity,
)
from backend.monte_carlo import run_monte_carlo
from backend.project_io import serialize_project, deserialize_project
from backend.report_generator import generate_pdf_report


st.set_page_config(page_title="Calculateur — CotaStack", page_icon="🧮", layout="wide")


def create_empty_item() -> dict:
    """Create an empty item dict for the data editor."""
    return {
        "Repère": "",
        "Orientation": "+",
        "Nominal (mm)": 0.0,
        "ES (mm)": 0.0,
        "EI (mm)": 0.0,
        "IT (mm)": 0.0,
        "Matériau": "Acier (standard)",
    }


def items_to_dataframe(items: list[Item]) -> pd.DataFrame:
    """Convert list of Items to DataFrame for editing."""
    data = []
    for item in items:
        data.append({
            "Repère": item.name,
            "Orientation": "+" if item.orientation > 0 else "-",
            "Nominal (mm)": item.nominal,
            "ES (mm)": item.es,
            "EI (mm)": item.ei,
            "IT (mm)": item.IT,
            "Matériau": item.material or "Acier (standard)",
        })
    if not data:
        data = [create_empty_item()]
    return pd.DataFrame(data)


def dataframe_to_items(df: pd.DataFrame) -> list[Item]:
    """Convert edited DataFrame back to list of Items."""
    items = []
    for _, row in df.iterrows():
        name = str(row.get("Repère", "")).strip()
        if not name:
            continue

        raw_orient = row.get("Orientation", "+")
        if isinstance(raw_orient, str):
            orientation = -1 if raw_orient.strip() == "-" else 1
        else:
            try:
                orientation = -1 if int(raw_orient) < 0 else 1
            except (ValueError, TypeError):
                orientation = 1

        try:
            nominal = float(row.get("Nominal (mm)", 0.0))
            es = float(row.get("ES (mm)", 0.0))
            ei = float(row.get("EI (mm)", 0.0))
        except (ValueError, TypeError):
            continue

        if es < ei:
            es, ei = ei, es

        material = str(row.get("Matériau", "Acier (standard)"))

        items.append(Item(
            name=name,
            nominal=nominal,
            es=es,
            ei=ei,
            orientation=orientation,  # type: ignore
            material=material,
        ))
    return items


def render_metric_card(label: str, value: float, unit: str = "mm", delta: str | None = None):
    """Render a metric card with consistent styling."""
    st.metric(label, f"{value:.4f} {unit}", delta=delta)


def main():
    st.title("🧮 Calculateur de chaînes de cotes 1D")
    st.caption("Pire des cas (WC), Statistique (RSS), Dilatations thermiques (ΔT) & Monte Carlo — ISO GPS")

    # Available materials catalog
    mat_options = get_available_materials()

    # Initialize session state
    if "items_df" not in st.session_state:
        st.session_state.items_df = pd.DataFrame([
            {"Repère": "Carter (Femelle)", "Orientation": "+", "Nominal (mm)": 100.0, "ES (mm)": 0.05, "EI (mm)": -0.05, "IT (mm)": 0.1, "Matériau": "Aluminium (alliage 6000/7000)"},
            {"Repère": "Arbre (Mâle)", "Orientation": "-", "Nominal (mm)": 98.0, "ES (mm)": 0.03, "EI (mm)": -0.03, "IT (mm)": 0.06, "Matériau": "Acier (standard)"},
        ])
    else:
        if "Orientation" in st.session_state.items_df.columns:
            st.session_state.items_df["Orientation"] = st.session_state.items_df["Orientation"].replace(
                {1: "+", -1: "-", 1.0: "+", -1.0: "-", "+1": "+", "-1": "-"}
            )
        if "Matériau" not in st.session_state.items_df.columns:
            st.session_state.items_df["Matériau"] = "Acier (standard)"

    if "target_min" not in st.session_state:
        st.session_state.target_min = 1.85
    if "target_max" not in st.session_state:
        st.session_state.target_max = 2.15
    if "t_service" not in st.session_state:
        st.session_state.t_service = 20.0
    if "enable_thermal" not in st.session_state:
        st.session_state.enable_thermal = False

    # --- Project Persistence (File Uploader .cotastack) ---
    with st.expander("📂 Sauvegarder ou Ouvrir un projet (.cotastack JSON)", expanded=False):
        col_io1, col_io2 = st.columns(2)
        with col_io1:
            uploaded_proj = st.file_uploader("Restaurer un fichier .cotastack", type=["json", "cotastack"], key="proj_upload")
            if uploaded_proj is not None:
                try:
                    content_str = uploaded_proj.read().decode("utf-8")
                    proj_data = deserialize_project(content_str)
                    st.session_state.items_df = items_to_dataframe(proj_data["items"])
                    st.session_state.target_min = proj_data.get("target_min")
                    st.session_state.target_max = proj_data.get("target_max")
                    st.session_state.t_service = proj_data.get("t_service", 20.0)
                    st.success("Projet chargé avec succès !")
                    st.rerun()
                except Exception as err:
                    st.error(f"Erreur lors du chargement : {err}")

        with col_io2:
            st.write("**Exporter le projet en cours**")
            cur_items = dataframe_to_items(st.session_state.items_df)
            json_blob = serialize_project(
                items=cur_items,
                target_min=st.session_state.target_min,
                target_max=st.session_state.target_max,
                t_service=st.session_state.t_service,
            )
            st.download_button(
                label="💾 Télécharger le fichier projet (.cotastack)",
                data=json_blob,
                file_name="projet_chaine.cotastack",
                mime="application/json",
                use_container_width=True,
            )

    # --- Sidebar: Controls ---
    with st.sidebar:
        st.header("🎯 Cibles Fonctionnelles")
        target_min = st.number_input(
            "Jeu Min (J_min)",
            value=float(st.session_state.target_min) if st.session_state.target_min is not None else 0.0,
            step=0.01,
            format="%.4f",
            help="Borne inférieure acceptable du jeu fonctionnel",
            key="target_min_input",
        )
        target_max = st.number_input(
            "Jeu Max (J_max)",
            value=float(st.session_state.target_max) if st.session_state.target_max is not None else 0.0,
            step=0.01,
            format="%.4f",
            help="Borne supérieure acceptable du jeu fonctionnel",
            key="target_max_input",
        )

        use_targets = st.checkbox("Activer les cibles", value=st.session_state.target_min is not None)
        if use_targets:
            st.session_state.target_min = target_min
            st.session_state.target_max = target_max
        else:
            st.session_state.target_min = None
            st.session_state.target_max = None

        st.divider()
        st.header("🌡️ Dilatation Thermique (ΔT)")
        enable_thermal = st.checkbox("Activer l'analyse thermique", value=st.session_state.enable_thermal)
        st.session_state.enable_thermal = enable_thermal

        if enable_thermal:
            t_service = st.slider(
                "Température de service (°C)",
                min_value=-40.0,
                max_value=150.0,
                value=float(st.session_state.t_service),
                step=1.0,
                help="Température ambiante de fonctionnement (Référence normalisée ISO 1 : 20 °C)",
            )
            st.session_state.t_service = t_service
            st.caption(f"Écart thermique : ΔT = {t_service - 20.0:+.1f} °C")

        st.divider()
        if st.button("🗑️ Vider le tableau", use_container_width=True):
            st.session_state.items_df = pd.DataFrame([create_empty_item()])
            st.rerun()

    # --- Assistant injection ISO 286 / 2768 ---
    with st.expander("🔧 Assistant d'injection de tolérances normées (ISO 286 / ISO 2768-1)", expanded=False):
        tab_iso286, tab_iso2768 = st.tabs(["Ajustement ISO 286 (H7, g6, etc.)", "Tolérance générale ISO 2768-1 (f, m, c, v)"])

        with tab_iso286:
            col_a1, col_a2, col_a3, col_a4, col_a5, col_a6 = st.columns([2, 1, 1.2, 1.3, 1.5, 1.3])
            with col_a1:
                iso_name = st.text_input("Repère", value="Alésage guidage", key="iso_name_input")
            with col_a2:
                iso_orient = st.selectbox("Sens", options=["+", "-"], key="iso_orient_input")
            with col_a3:
                iso_nominal = st.number_input("Nominal (mm)", min_value=0.5, max_value=500.0, value=20.0, step=1.0, key="iso_nom_input")
            with col_a4:
                all_symbols = get_available_iso286_symbols()
                merged_syms = [f"Alésage {h}" for h in all_symbols["holes"]] + [f"Arbre {s}" for s in all_symbols["shafts"]]
                selected_sym_label = st.selectbox("Symbole ISO 286", options=merged_syms, index=1, key="iso_sym_input")
                sym_clean = selected_sym_label.split()[-1]
            with col_a5:
                iso_mat = st.selectbox("Matériau", options=mat_options, index=0, key="iso_mat_input")
            with col_a6:
                st.write("")
                st.write("")
                if st.button("➕ Injecter", use_container_width=True, key="btn_inject_iso286"):
                    ei_calc, es_calc = get_iso286_limits(iso_nominal, sym_clean)
                    new_row = {
                        "Repère": f"{iso_name} ({sym_clean})",
                        "Orientation": iso_orient,
                        "Nominal (mm)": iso_nominal,
                        "ES (mm)": es_calc,
                        "EI (mm)": ei_calc,
                        "IT (mm)": round(es_calc - ei_calc, 5),
                        "Matériau": iso_mat,
                    }
                    cur_df = st.session_state.items_df
                    if len(cur_df) == 1 and not str(cur_df.iloc[0]["Repère"]).strip():
                        st.session_state.items_df = pd.DataFrame([new_row])
                    else:
                        st.session_state.items_df = pd.concat([cur_df, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"Cote {sym_clean} injectée avec ES={es_calc:+.4f}, EI={ei_calc:+.4f} mm")
                    st.rerun()

        with tab_iso2768:
            col_b1, col_b2, col_b3, col_b4, col_b5, col_b6 = st.columns([2, 1, 1.2, 1.3, 1.5, 1.3])
            with col_b1:
                gen_name = st.text_input("Repère", value="Cote brute", key="gen_name_input")
            with col_b2:
                gen_orient = st.selectbox("Sens", options=["+", "-"], key="gen_orient_input")
            with col_b3:
                gen_nominal = st.number_input("Nominal (mm)", min_value=0.5, max_value=4000.0, value=35.0, step=1.0, key="gen_nom_input")
            with col_b4:
                gen_grade = st.selectbox("Classe ISO 2768-1", options=["f", "m", "c", "v"], index=1, key="gen_grade_input")
            with col_b5:
                gen_mat = st.selectbox("Matériau", options=mat_options, index=0, key="gen_mat_input")
            with col_b6:
                st.write("")
                st.write("")
                if st.button("➕ Injecter", use_container_width=True, key="btn_inject_iso2768"):
                    tol = get_iso2768_linear_tolerance(gen_nominal, gen_grade)  # type: ignore
                    new_row = {
                        "Repère": f"{gen_name} (ISO 2768-{gen_grade})",
                        "Orientation": gen_orient,
                        "Nominal (mm)": gen_nominal,
                        "ES (mm)": tol,
                        "EI (mm)": -tol,
                        "IT (mm)": round(2 * tol, 5),
                        "Matériau": gen_mat,
                    }
                    cur_df = st.session_state.items_df
                    if len(cur_df) == 1 and not str(cur_df.iloc[0]["Repère"]).strip():
                        st.session_state.items_df = pd.DataFrame([new_row])
                    else:
                        st.session_state.items_df = pd.concat([cur_df, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"Cote injectée avec ±{tol:.2f} mm")
                    st.rerun()

    # --- Main Data Editor ---
    st.subheader("📋 Saisie des maillons de la chaîne")

    column_config = {
        "Repère": st.column_config.TextColumn(
            "Repère",
            help="Nom / Désignation de la cote",
            required=True,
            width="medium",
        ),
        "Orientation": st.column_config.SelectboxColumn(
            "Orientation",
            help="Sens vectoriel : + (augmente le jeu) ou - (réduit le jeu)",
            options=["+", "-"],
            required=True,
            width="small",
        ),
        "Nominal (mm)": st.column_config.NumberColumn(
            "Nominal (mm)",
            help="Dimension nominale à 20 °C (mm)",
            min_value=0.0,
            step=0.01,
            format="%.4f",
            required=True,
            width="medium",
        ),
        "ES (mm)": st.column_config.NumberColumn(
            "ES (mm)",
            help="Écart supérieur (ES ≥ EI)",
            step=0.001,
            format="%.4f",
            required=True,
            width="medium",
        ),
        "EI (mm)": st.column_config.NumberColumn(
            "EI (mm)",
            help="Écart inférieur (EI ≤ ES)",
            step=0.001,
            format="%.4f",
            required=True,
            width="medium",
        ),
        "IT (mm)": st.column_config.NumberColumn(
            "IT (mm)",
            help="Intervalle de tolérance = ES - EI",
            disabled=True,
            format="%.4f",
            width="small",
        ),
        "Matériau": st.column_config.SelectboxColumn(
            "Matériau",
            help="Matériau pour le coefficient de dilatation thermique α",
            options=mat_options,
            required=True,
            width="medium",
        ),
    }

    edited_df = st.data_editor(
        st.session_state.items_df,
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="items_editor",
    )

    if not edited_df.empty:
        try:
            edited_df["IT (mm)"] = edited_df["ES (mm)"] - edited_df["EI (mm)"]
        except Exception:
            pass

    st.session_state.items_df = edited_df
    items = dataframe_to_items(edited_df)

    if items:
        calc = ChainCalculator(
            items,
            target_min=st.session_state.target_min,
            target_max=st.session_state.target_max,
        )
        result = calc.calculate()

        # Thermal calculation if enabled
        thermal_res = None
        if st.session_state.enable_thermal:
            thermal_res = calculate_thermal_chain(items, t_service=st.session_state.t_service)

        # --- Dashboard Results ---
        st.divider()
        st.subheader("📊 Résultats du calcul")

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            render_metric_card("Jeu Nominal (20°C)", result.nominal)
        with col2:
            render_metric_card("Jeu Moyen (20°C)", result.mean)
        with col3:
            render_metric_card("WC Min", result.worst_case_minus)
        with col4:
            render_metric_card("WC Max", result.worst_case_plus)
        with col5:
            render_metric_card("RSS Min", result.rss_minus)
        with col6:
            render_metric_card("RSS Max", result.rss_plus)

        # Thermal metrics if active
        if thermal_res:
            st.info(f"🌡️ **Comportement thermique à {thermal_res.t_service:.1f} °C (ΔT = {thermal_res.delta_t:+.1f} °C) :**")
            col_t1, col_t2, col_t3, col_t4 = st.columns(4)
            with col_t1:
                render_metric_card("Jeu Nominal à chaud", thermal_res.nominal_at_t, delta=f"{thermal_res.delta_j_nominal:+.4f} mm")
            with col_t2:
                render_metric_card("Jeu Moyen à chaud", thermal_res.mean_at_t, delta=f"{thermal_res.delta_j_mean:+.4f} mm")
            with col_t3:
                render_metric_card("WC Min à chaud", thermal_res.worst_case_minus_at_t)
            with col_t4:
                render_metric_card("WC Max à chaud", thermal_res.worst_case_plus_at_t)

        # --- Compliance Section ---
        if st.session_state.target_min is not None or st.session_state.target_max is not None:
            st.divider()
            st.subheader("✅ Conformité aux Cibles Fonctionnelles")

            wc_comp = result.compliance["wc_compliant"]
            rss_comp = result.compliance["rss_compliant"]

            col_badge1, col_badge2 = st.columns(2)
            with col_badge1:
                if wc_comp:
                    st.success("✅ **WC : CONFORME (GO)** — 100% dans la cible à 20°C")
                else:
                    st.error("❌ **WC : NON CONFORME (NO-GO)** — Dépassement aux extrêmes")
                if result.compliance["wc_margin_min"] is not None:
                    st.caption(f"Marge inf: `{result.compliance['wc_margin_min']:+.4f} mm` | Marge sup: `{result.compliance['wc_margin_max']:+.4f} mm`")

            with col_badge2:
                if rss_comp:
                    st.success("✅ **RSS : CONFORME (GO)** — Conforme sous hypothèse normale (3σ)")
                else:
                    st.error("❌ **RSS : NON CONFORME (NO-GO)** — Dispersion statistique hors cible")
                if result.compliance["rss_margin_min"] is not None:
                    st.caption(f"Marge inf: `{result.compliance['rss_margin_min']:+.4f} mm` | Marge sup: `{result.compliance['rss_margin_max']:+.4f} mm`")

        # --- Visualizations Tabs ---
        st.divider()
        tab_pareto, tab_gauss, tab_thermal_curve, tab_mc = st.tabs([
            "📉 Analyse de Pareto",
            "📈 Distribution Gauss (RSS)",
            "🌡️ Sensibilité Thermique J(T)",
            "🎲 Simulation Monte Carlo (PPM)",
        ])

        # TAB 1: Pareto
        with tab_pareto:
            st.caption("Contribution de chaque cote à la variance totale du jeu")
            df_pareto = pd.DataFrame(result.pareto)
            fig_pareto = px.bar(
                df_pareto,
                x="contribution_pct",
                y="name",
                orientation="h",
                labels={"contribution_pct": "Contribution (%)", "name": "Cote"},
                color="contribution_pct",
                color_continuous_scale="Blues",
            )
            fig_pareto.update_layout(yaxis={"categoryorder": "total ascending"}, height=350, margin=dict(l=40, r=40, t=20, b=40))
            st.plotly_chart(fig_pareto, use_container_width=True)

        # TAB 2: Gauss
        with tab_gauss:
            it_rss = (sum(item.IT ** 2 for item in items)) ** 0.5
            mu = result.mean
            sigma = it_rss / 6.0
            if sigma > 0:
                x_vals = np.linspace(mu - 4 * sigma, mu + 4 * sigma, 300)
                y_vals = stats.norm.pdf(x_vals, mu, sigma)

                fig_dist = go.Figure()
                fig_dist.add_trace(go.Scatter(x=x_vals, y=y_vals, mode="lines", name="Densité RSS", line=dict(color="#0284c7", width=2.5), fill="tozeroy", fillcolor="rgba(2, 132, 199, 0.1)"))
                fig_dist.add_vline(x=result.rss_minus, line_dash="dash", line_color="#10b981", annotation_text="RSS Min")
                fig_dist.add_vline(x=result.rss_plus, line_dash="dash", line_color="#10b981", annotation_text="RSS Max")
                if st.session_state.target_min is not None:
                    fig_dist.add_vline(x=st.session_state.target_min, line_dash="dot", line_color="#ef4444", annotation_text="Cible Min")
                if st.session_state.target_max is not None:
                    fig_dist.add_vline(x=st.session_state.target_max, line_dash="dot", line_color="#ef4444", annotation_text="Cible Max")

                fig_dist.update_layout(xaxis_title="Jeu résultant (mm)", yaxis_title="Densité", height=350, margin=dict(l=40, r=40, t=20, b=40))
                st.plotly_chart(fig_dist, use_container_width=True)
            else:
                st.info("Intervalle de tolérance nul.")

        # TAB 3: Thermal Curve J(T)
        with tab_thermal_curve:
            st.caption("Évolution continue du jeu fonctionnel entre -40 °C et +120 °C")
            curve_data = simulate_thermal_sensitivity(items, t_min=-40.0, t_max=120.0, num_points=60)
            df_curve = pd.DataFrame(curve_data)

            fig_therm = go.Figure()
            fig_therm.add_trace(go.Scatter(x=df_curve["temperature"], y=df_curve["nominal"], mode="lines", name="Jeu Nominal J(T)", line=dict(color="#0284c7", width=2.5)))
            fig_therm.add_trace(go.Scatter(x=df_curve["temperature"], y=df_curve["wc_max"], mode="lines", name="WC Max", line=dict(color="#94a3b8", dash="dash")))
            fig_therm.add_trace(go.Scatter(x=df_curve["temperature"], y=df_curve["wc_min"], mode="lines", name="WC Min", line=dict(color="#94a3b8", dash="dash"), fill="tonexty", fillcolor="rgba(148, 163, 184, 0.1)"))

            if st.session_state.target_min is not None:
                fig_therm.add_hline(y=st.session_state.target_min, line_dash="dot", line_color="#ef4444", annotation_text="Cible Min")
            if st.session_state.target_max is not None:
                fig_therm.add_hline(y=st.session_state.target_max, line_dash="dot", line_color="#ef4444", annotation_text="Cible Max")

            fig_therm.update_layout(xaxis_title="Température (°C)", yaxis_title="Jeu (mm)", height=350, margin=dict(l=40, r=40, t=20, b=40))
            st.plotly_chart(fig_therm, use_container_width=True)

        # TAB 4: Monte Carlo
        with tab_mc:
            st.caption("Simulation stochastique vectorisée de 100 000 assemblages réels")
            col_mc1, col_mc2 = st.columns([1, 2])
            with col_mc1:
                nb_runs = st.select_slider("Nombre de tirages", options=[10_000, 50_000, 100_000], value=100_000)
                btn_run_mc = st.button("🎲 Lancer la simulation", type="primary", use_container_width=True)

            if btn_run_mc or "mc_res" in st.session_state:
                if btn_run_mc:
                    with st.spinner("Exécution de la simulation stochastique..."):
                        mc_result = run_monte_carlo(
                            items,
                            num_simulations=nb_runs,
                            target_min=st.session_state.target_min,
                            target_max=st.session_state.target_max,
                        )
                        st.session_state.mc_res = mc_result
                else:
                    mc_result = st.session_state.mc_res

                st.markdown("#### Indicateurs de Capabilité et Rebut")
                col_k1, col_k2, col_k3, col_k4 = st.columns(4)
                with col_k1:
                    st.metric("Taux de non-conformité", f"{mc_result.defect_ppm:.1f} PPM", delta=f"{mc_result.defect_rate_pct:.3f} %", delta_color="inverse")
                with col_k2:
                    st.metric("Cp (Capabilité procédé)", f"{mc_result.cp:.2f}" if mc_result.cp else "N/A")
                with col_k3:
                    st.metric("Cpk (Centrage procédé)", f"{mc_result.cpk:.2f}" if mc_result.cpk else "N/A")
                with col_k4:
                    st.metric("Écart-type réel σ", f"{mc_result.std_dev:.4f} mm")

                # Histogram
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Histogram(
                    x=mc_result.samples_summary,
                    nbinsx=60,
                    name="Tirages réels",
                    marker_color="#0284c7",
                    opacity=0.75,
                ))
                if st.session_state.target_min is not None:
                    fig_hist.add_vline(x=st.session_state.target_min, line_dash="dot", line_color="#ef4444", annotation_text="Cible Min")
                if st.session_state.target_max is not None:
                    fig_hist.add_vline(x=st.session_state.target_max, line_dash="dot", line_color="#ef4444", annotation_text="Cible Max")

                fig_hist.update_layout(xaxis_title="Jeu simulé (mm)", yaxis_title="Effectif", height=320, margin=dict(l=40, r=40, t=20, b=40))
                st.plotly_chart(fig_hist, use_container_width=True)

        # --- Official PDF Export & Lightweight Exports ---
        st.divider()
        st.subheader("📑 Certification Documentaire & Rapports")

        col_pdf, col_csv = st.columns(2)
        with col_pdf:
            # Generate official PDF Report
            thermal_dict = {
                "t_service": st.session_state.t_service,
                "delta_j_nominal": thermal_res.delta_j_nominal if thermal_res else 0.0,
                "nominal_at_t": thermal_res.nominal_at_t if thermal_res else result.nominal,
            } if st.session_state.enable_thermal else None

            mc_dict = {
                "defect_ppm": st.session_state.mc_res.defect_ppm if "mc_res" in st.session_state else 0.0,
                "cp": st.session_state.mc_res.cp if "mc_res" in st.session_state else None,
                "cpk": st.session_state.mc_res.cpk if "mc_res" in st.session_state else None,
            } if "mc_res" in st.session_state else None

            pdf_bytes = generate_pdf_report(
                items=items,
                result=result,
                project_metadata={"title": "Étude Tolérancement 1D", "author": "Bureau d'Études", "revision": "A"},
                thermal_summary=thermal_dict,
                monte_carlo_summary=mc_dict,
            )

            st.download_button(
                label="📄 Télécharger la Note de Calcul Officielle (PDF A4)",
                data=pdf_bytes,
                file_name="cotastack_note_de_calcul.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

        with col_csv:
            csv_data = edited_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Télécharger le tableau des cotes (CSV)",
                data=csv_data,
                file_name="cotastack_chain_data.csv",
                mime="text/csv",
                use_container_width=True,
            )

    else:
        st.info("Ajoutez au moins un maillon avec une dimension nominale pour lancer l'analyse.")

    st.divider()
    st.warning(
        "⚠️ **Avertissement** : Outil d'aide à la conception. "
        "L'utilisateur demeure seul responsable de la validation technique de ses chaînes avant fabrication."
    )


if __name__ == "__main__":
    main()
