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


st.set_page_config(page_title="Calculateur — CotaStack", page_icon="🧮", layout="wide")


def create_empty_item() -> dict:
    """Create an empty item dict for the data editor."""
    return {
        "Repère": "",
        "Orientation": 1,
        "Nominal (mm)": 0.0,
        "ES (mm)": 0.0,
        "EI (mm)": 0.0,
        "IT (mm)": 0.0,
    }


def items_to_dataframe(items: list[Item]) -> pd.DataFrame:
    """Convert list of Items to DataFrame for editing."""
    data = []
    for item in items:
        data.append({
            "Repère": item.name,
            "Orientation": item.orientation,
            "Nominal (mm)": item.nominal,
            "ES (mm)": item.es,
            "EI (mm)": item.ei,
            "IT (mm)": item.IT,
        })
    if not data:
        data = [create_empty_item()]
    return pd.DataFrame(data)


def dataframe_to_items(df: pd.DataFrame) -> list[Item]:
    """Convert edited DataFrame back to list of Items."""
    items = []
    for _, row in df.iterrows():
        name = str(row["Repère"]).strip()
        if not name:
            continue
        try:
            orientation = int(row["Orientation"])
            if orientation not in (1, -1):
                orientation = 1
        except (ValueError, TypeError):
            orientation = 1

        try:
            nominal = float(row["Nominal (mm)"])
            es = float(row["ES (mm)"])
            ei = float(row["EI (mm)"])
        except (ValueError, TypeError):
            continue

        # Ensure ES >= EI
        if es < ei:
            es, ei = ei, es

        items.append(Item(
            name=name,
            nominal=nominal,
            es=es,
            ei=ei,
            orientation=orientation,
        ))
    return items


def render_metric_card(label: str, value: float, unit: str = "mm", delta: str | None = None):
    """Render a metric card with consistent styling."""
    st.metric(label, f"{value:.4f} {unit}", delta=delta)


def generate_markdown_summary(items: list[Item], result: ChainResult) -> str:
    """Generate Markdown calculation summary ready to copy for emails or reports."""
    lines = [
        "# Note de calcul de chaîne de cotes 1D — CotaStack",
        "",
        "## 1. Tableau des maillons",
        "| Repère | Sens | Nominal (mm) | EI (mm) | ES (mm) | IT (mm) | L_moy (mm) |",
        "|:-------|:----:|:------------:|:-------:|:-------:|:-------:|:----------:|",
    ]
    for it in items:
        sign = "+1" if it.orientation > 0 else "-1"
        lines.append(f"| {it.name} | {sign} | {it.nominal:.4f} | {it.ei:+.4f} | {it.es:+.4f} | {it.IT:.4f} | {it.L_moy:.4f} |")

    lines.extend([
        "",
        "## 2. Synthèse des résultats",
        f"- **Jeu nominal ($J_{{nom}}$)** : `{result.nominal:.4f} mm`",
        f"- **Jeu moyen ($J_{{moy}}$)** : `{result.mean:.4f} mm`",
        f"- **Pire des cas (WC)** : `[{result.worst_case_minus:.4f} ; {result.worst_case_plus:.4f}] mm` (IT = {sum(i.IT for i in items):.4f} mm)",
        f"- **Statistique RSS (3σ)** : `[{result.rss_minus:.4f} ; {result.rss_plus:.4f}] mm` (IT = {sum(i.IT**2 for i in items)**0.5:.4f} mm)",
    ])

    if result.target_min is not None or result.target_max is not None:
        lines.append("")
        lines.append("## 3. Conformité vis-à-vis des cibles")
        if result.target_min is not None:
            lines.append(f"- Cible minimale : `{result.target_min:.4f} mm`")
        if result.target_max is not None:
            lines.append(f"- Cible maximale : `{result.target_max:.4f} mm`")
        wc_status = "CONFORME (GO)" if result.compliance["wc_compliant"] else "NON CONFORME (NO-GO)"
        rss_status = "CONFORME (GO)" if result.compliance["rss_compliant"] else "NON CONFORME (NO-GO)"
        lines.append(f"- Verdict Pire des Cas (WC) : **{wc_status}**")
        lines.append(f"- Verdict Statistique (RSS) : **{rss_status}**")

    lines.append("")
    lines.append("*Généré automatiquement par CotaStack — Conforme pratiques ISO.*")
    return "\n".join(lines)


def main():
    st.title("🧮 Calculateur de chaînes de cotes 1D")
    st.caption("Méthodes : Pire des cas (WC) & RSS (Root Sum Square) — Conforme pratiques ISO")

    # Initialize session state
    if "items_df" not in st.session_state:
        st.session_state.items_df = pd.DataFrame([
            {"Repère": "Cote A (Carter)", "Orientation": 1, "Nominal (mm)": 50.0, "ES (mm)": 0.05, "EI (mm)": -0.05, "IT (mm)": 0.1},
            {"Repère": "Cote B (Arbre)", "Orientation": -1, "Nominal (mm)": 30.0, "ES (mm)": 0.02, "EI (mm)": -0.02, "IT (mm)": 0.04},
            {"Repère": "Cote C (Bague)", "Orientation": -1, "Nominal (mm)": 18.0, "ES (mm)": 0.03, "EI (mm)": -0.03, "IT (mm)": 0.06},
        ])
    if "target_min" not in st.session_state:
        st.session_state.target_min = 1.8
    if "target_max" not in st.session_state:
        st.session_state.target_max = 2.2

    # --- Sidebar: Targets & Controls ---
    with st.sidebar:
        st.header("🎯 Jeu Cible (optionnel)")
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
        st.markdown("**Méthodes de calcul**")
        st.checkbox("Pire des cas (WC)", value=True, disabled=True)
        st.checkbox("RSS (Statistique)", value=True, disabled=True)

        st.divider()
        if st.button("🗑️ Vider le tableau", use_container_width=True):
            st.session_state.items_df = pd.DataFrame([create_empty_item()])
            st.rerun()

    # --- Assistant insertion ISO 286 / 2768 ---
    with st.expander("🔧 Assistant d'injection de tolérances normées (ISO 286 / ISO 2768-1)", expanded=False):
        tab_iso286, tab_iso2768 = st.tabs(["Ajustement ISO 286 (H7, g6, etc.)", "Tolérance générale ISO 2768-1 (f, m, c, v)"])

        with tab_iso286:
            col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns([2, 1, 1.5, 1.5, 1.5])
            with col_a1:
                iso_name = st.text_input("Repère", value="Alésage guidage", key="iso_name_input")
            with col_a2:
                iso_orient = st.selectbox("Sens", options=[1, -1], format_func=lambda x: "+1" if x > 0 else "-1", key="iso_orient_input")
            with col_a3:
                iso_nominal = st.number_input("Nominal (mm)", min_value=0.5, max_value=500.0, value=20.0, step=1.0, key="iso_nom_input")
            with col_a4:
                all_symbols = get_available_iso286_symbols()
                merged_syms = [f"Alésage {h}" for h in all_symbols["holes"]] + [f"Arbre {s}" for s in all_symbols["shafts"]]
                selected_sym_label = st.selectbox("Symbole ISO 286", options=merged_syms, index=1, key="iso_sym_input")
                sym_clean = selected_sym_label.split()[-1]
            with col_a5:
                st.write("")
                st.write("")
                if st.button("➕ Injecter la cote", use_container_width=True, key="btn_inject_iso286"):
                    ei_calc, es_calc = get_iso286_limits(iso_nominal, sym_clean)
                    new_row = {
                        "Repère": f"{iso_name} ({sym_clean})",
                        "Orientation": iso_orient,
                        "Nominal (mm)": iso_nominal,
                        "ES (mm)": es_calc,
                        "EI (mm)": ei_calc,
                        "IT (mm)": round(es_calc - ei_calc, 5),
                    }
                    cur_df = st.session_state.items_df
                    # Filter out purely blank row if solitary
                    if len(cur_df) == 1 and not str(cur_df.iloc[0]["Repère"]).strip():
                        st.session_state.items_df = pd.DataFrame([new_row])
                    else:
                        st.session_state.items_df = pd.concat([cur_df, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"Cote {sym_clean} injectée avec ES={es_calc:+.4f}, EI={ei_calc:+.4f} mm")
                    st.rerun()

        with tab_iso2768:
            col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns([2, 1, 1.5, 1.5, 1.5])
            with col_b1:
                gen_name = st.text_input("Repère", value="Cote brute", key="gen_name_input")
            with col_b2:
                gen_orient = st.selectbox("Sens", options=[1, -1], format_func=lambda x: "+1" if x > 0 else "-1", key="gen_orient_input")
            with col_b3:
                gen_nominal = st.number_input("Nominal (mm)", min_value=0.5, max_value=4000.0, value=35.0, step=1.0, key="gen_nom_input")
            with col_b4:
                gen_grade = st.selectbox("Classe ISO 2768-1", options=["f", "m", "c", "v"], index=1, key="gen_grade_input")
            with col_b5:
                st.write("")
                st.write("")
                if st.button("➕ Injecter la cote", use_container_width=True, key="btn_inject_iso2768"):
                    tol = get_iso2768_linear_tolerance(gen_nominal, gen_grade)  # type: ignore
                    new_row = {
                        "Repère": f"{gen_name} (ISO 2768-{gen_grade})",
                        "Orientation": gen_orient,
                        "Nominal (mm)": gen_nominal,
                        "ES (mm)": tol,
                        "EI (mm)": -tol,
                        "IT (mm)": round(2 * tol, 5),
                    }
                    cur_df = st.session_state.items_df
                    if len(cur_df) == 1 and not str(cur_df.iloc[0]["Repère"]).strip():
                        st.session_state.items_df = pd.DataFrame([new_row])
                    else:
                        st.session_state.items_df = pd.concat([cur_df, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"Cote injectée avec ±{tol:.2f} mm")
                    st.rerun()

    # --- Main: Data Editor ---
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
            help="Sens vectoriel : +1 (augmente le jeu) ou -1 (réduit le jeu)",
            options=[1, -1],
            required=True,
            width="small",
        ),
        "Nominal (mm)": st.column_config.NumberColumn(
            "Nominal (mm)",
            help="Dimension nominale en mm",
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
            help="Intervalle de tolérance = ES - EI (calculé auto)",
            disabled=True,
            format="%.4f",
            width="small",
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

    # Auto-update IT column
    if not edited_df.empty:
        try:
            edited_df["IT (mm)"] = edited_df["ES (mm)"] - edited_df["EI (mm)"]
        except Exception:
            pass

    st.session_state.items_df = edited_df

    # Convert to Items and calculate
    items = dataframe_to_items(edited_df)

    if items:
        calc = ChainCalculator(
            items,
            target_min=st.session_state.target_min,
            target_max=st.session_state.target_max,
        )
        result = calc.calculate()

        # --- Results Dashboard ---
        st.divider()
        st.subheader("📊 Résultats du calcul")

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            render_metric_card("Jeu Nominal", result.nominal)
        with col2:
            render_metric_card("Jeu Moyen", result.mean)
        with col3:
            render_metric_card("WC Min", result.worst_case_minus)
        with col4:
            render_metric_card("WC Max", result.worst_case_plus)
        with col5:
            render_metric_card("RSS Min", result.rss_minus)
        with col6:
            render_metric_card("RSS Max", result.rss_plus)

        # IT Totals
        it_wc = sum(item.IT for item in items)
        it_rss = (sum(item.IT ** 2 for item in items)) ** 0.5
        col_it1, col_it2 = st.columns(2)
        with col_it1:
            render_metric_card("IT Total Pire des Cas (WC)", it_wc)
        with col_it2:
            render_metric_card("IT Total Statistique (RSS)", it_rss)

        # --- Compliance Badges ---
        if st.session_state.target_min is not None or st.session_state.target_max is not None:
            st.divider()
            st.subheader("✅ Conformité aux Cibles Fonctionnelles")

            wc_comp = result.compliance["wc_compliant"]
            rss_comp = result.compliance["rss_compliant"]

            col_badge1, col_badge2 = st.columns(2)
            with col_badge1:
                if wc_comp:
                    st.success("✅ **WC : CONFORME (GO)** — 100% de la dispersion dans la cible")
                else:
                    st.error("❌ **WC : NON CONFORME (NO-GO)** — Dépassement aux extrêmes")
                if result.compliance["wc_margin_min"] is not None:
                    st.caption(f"Marge inférieure : `{result.compliance['wc_margin_min']:+.4f} mm`")
                if result.compliance["wc_margin_max"] is not None:
                    st.caption(f"Marge supérieure : `{result.compliance['wc_margin_max']:+.4f} mm`")

            with col_badge2:
                if rss_comp:
                    st.success("✅ **RSS : CONFORME (GO)** — Conforme sous hypothèse normale à 3σ")
                else:
                    st.error("❌ **RSS : NON CONFORME (NO-GO)** — Dispersion statistique hors cible")
                if result.compliance["rss_margin_min"] is not None:
                    st.caption(f"Marge inférieure : `{result.compliance['rss_margin_min']:+.4f} mm`")
                if result.compliance["rss_margin_max"] is not None:
                    st.caption(f"Marge supérieure : `{result.compliance['rss_margin_max']:+.4f} mm`")

        # --- Visualizations ---
        st.divider()
        col_viz1, col_viz2 = st.columns(2)

        # Chart 1: Pareto
        with col_viz1:
            st.subheader("📉 Analyse de Pareto des Tolérances")
            pareto_data = result.pareto
            df_pareto = pd.DataFrame(pareto_data)

            fig_pareto = px.bar(
                df_pareto,
                x="contribution_pct",
                y="name",
                orientation="h",
                labels={"contribution_pct": "Contribution à la variance (%)", "name": "Cote"},
                color="contribution_pct",
                color_continuous_scale="Blues",
            )
            fig_pareto.update_layout(
                yaxis={"categoryorder": "total ascending"},
                height=380,
                margin=dict(l=40, r=40, t=20, b=40),
                showlegend=False,
            )
            st.plotly_chart(fig_pareto, use_container_width=True)

        # Chart 2: Gauss Distribution
        with col_viz2:
            st.subheader("📈 Distribution Statistique (RSS à 3σ)")

            mu = result.mean
            sigma = it_rss / 6.0

            if sigma > 0:
                x_vals = np.linspace(mu - 4 * sigma, mu + 4 * sigma, 300)
                y_vals = stats.norm.pdf(x_vals, mu, sigma)

                fig_dist = go.Figure()
                fig_dist.add_trace(go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode="lines",
                    name="Densité normale",
                    line=dict(color="#0284c7", width=2.5),
                    fill="tozeroy",
                    fillcolor="rgba(2, 132, 199, 0.1)",
                ))

                # RSS Bounds
                fig_dist.add_vline(x=result.rss_minus, line_dash="dash", line_color="#10b981", annotation_text="RSS Min")
                fig_dist.add_vline(x=result.rss_plus, line_dash="dash", line_color="#10b981", annotation_text="RSS Max")

                # Target Bounds
                if st.session_state.target_min is not None:
                    fig_dist.add_vline(x=st.session_state.target_min, line_dash="dot", line_color="#ef4444", annotation_text="Cible Min")
                if st.session_state.target_max is not None:
                    fig_dist.add_vline(x=st.session_state.target_max, line_dash="dot", line_color="#ef4444", annotation_text="Cible Max")

                fig_dist.update_layout(
                    xaxis_title="Jeu résultant (mm)",
                    yaxis_title="Densité de probabilité",
                    height=380,
                    margin=dict(l=40, r=40, t=20, b=40),
                    showlegend=False,
                )
                st.plotly_chart(fig_dist, use_container_width=True)
            else:
                st.info("Intervalle de tolérance nul.")

        # --- Lightweight Exports (Phase 2.3) ---
        st.divider()
        st.subheader("💾 Exports légers de l'analyse")

        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            csv_data = edited_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Télécharger le tableau des cotes (CSV)",
                data=csv_data,
                file_name="cotastack_chain_data.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col_exp2:
            md_summary = generate_markdown_summary(items, result)
            st.download_button(
                label="📥 Télécharger la note de calcul (Markdown)",
                data=md_summary,
                file_name="cotastack_note_de_calcul.md",
                mime="text/markdown",
                use_container_width=True,
            )

        with st.expander("📝 Aperçu de la synthèse Markdown prête pour email / CR"):
            st.code(md_summary, language="markdown")

    else:
        st.info("Ajoutez au moins un maillon avec une dimension nominale pour lancer l'analyse.")

    # --- Disclaimer ---
    st.divider()
    st.warning(
        "⚠️ **Avertissement** : Outil d'aide à la conception. "
        "L'utilisateur demeure seul responsable de la validation technique de ses chaînes avant fabrication."
    )

    # --- Fake Door Test: PDF Export ---
    st.divider()
    col_export1, col_export2, col_export3 = st.columns([1, 2, 1])
    with col_export2:
        if st.button("📄 Exporter le rapport PDF complet", use_container_width=True, type="primary"):
            @st.dialog("📄 Export PDF — Bientôt disponible")
            def pdf_modal():
                st.markdown("""
                **Fonctionnalité en cours de développement (Phase 3)**

                Le générateur de rapports PDF normés inclura :
                - Cartouche d'identification du projet
                - Tableau complet des maillons avec tolérances
                - Résultats WC & RSS avec verdicts Go/No-Go
                - Diagrammes de Pareto et distribution Gauss
                - Bilan de conformité horodaté
                - Bloc d'approbation (signature/date)

                **Intéressé(e) ?** Laissez votre email pour être notifié(e) à la sortie :
                """)
                email = st.text_input("Email", placeholder="votre@email.com")
                if st.button("Me tenir informé(e)", type="primary"):
                    if email:
                        st.success("Merci ! Vous serez notifié(e) dès la disponibilité.")
                    else:
                        st.error("Veuillez entrer une adresse email valide.")

            pdf_modal()


if __name__ == "__main__":
    main()
