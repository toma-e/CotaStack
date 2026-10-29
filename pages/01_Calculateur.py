"""CotaStack - Calculateur de chaînes de cotes 1D."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from backend.models import Item
from backend.calculator import ChainCalculator


st.set_page_config(page_title="Calculateur", page_icon="🧮", layout="wide")


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

        nominal = float(row["Nominal (mm)"])
        es = float(row["ES (mm)"])
        ei = float(row["EI (mm)"])

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


def main():
    st.title("🧮 Calculateur de chaînes de cotes 1D")
    st.caption("Méthodes : Pire des cas (WC) & RSS (Root Sum Square) — Conforme pratiques ISO")

    # Initialize session state
    if "items_df" not in st.session_state:
        st.session_state.items_df = pd.DataFrame([create_empty_item()])
    if "target_min" not in st.session_state:
        st.session_state.target_min = None
    if "target_max" not in st.session_state:
        st.session_state.target_max = None

    # --- Sidebar: Targets ---
    with st.sidebar:
        st.header("🎯 Jeu Cible (optionnel)")
        target_min = st.number_input(
            "Jeu Min (J_min)",
            value=0.0,
            step=0.01,
            format="%.4f",
            help="Borne inférieure acceptable du jeu fonctionnel",
            key="target_min_input",
        )
        target_max = st.number_input(
            "Jeu Max (J_max)",
            value=0.0,
            step=0.01,
            format="%.4f",
            help="Borne supérieure acceptable du jeu fonctionnel",
            key="target_max_input",
        )

        use_targets = st.checkbox("Activer les cibles", value=False)
        if use_targets:
            st.session_state.target_min = target_min if target_min != 0.0 else None
            st.session_state.target_max = target_max if target_max != 0.0 else None
        else:
            st.session_state.target_min = None
            st.session_state.target_max = None

        st.divider()
        st.markdown("**Méthodes de calcul**")
        st.checkbox("Pire des cas (WC)", value=True, disabled=True)
        st.checkbox("RSS (Statistique)", value=True, disabled=True)

        st.divider()
        if st.button("🗑️ Réinitialiser", use_container_width=True):
            st.session_state.items_df = pd.DataFrame([create_empty_item()])
            st.session_state.target_min = None
            st.session_state.target_max = None
            st.rerun()

    # --- Main: Data Editor ---
    st.subheader("📋 Saisie des maillons")

    # Column configuration for data_editor
    column_config = {
        "Repère": st.column_config.TextColumn(
            "Repère",
            help="Nom/identifiant de la cote",
            required=True,
            width="medium",
        ),
        "Orientation": st.column_config.SelectboxColumn(
            "Orientation",
            help="Sens dans la chaîne : +1 (ajoute) ou -1 (soustrait)",
            options=[1, -1],
            required=True,
            width="small",
        ),
        "Nominal (mm)": st.column_config.NumberColumn(
            "Nominal (mm)",
            help="Valeur nominale de la cote",
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
        edited_df["IT (mm)"] = edited_df["ES (mm)"] - edited_df["EI (mm)"]

    # Update session state
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
        st.subheader("📊 Résultats")

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
            render_metric_card("IT Total (WC)", it_wc)
        with col_it2:
            render_metric_card("IT Total (RSS)", it_rss)

        # --- Compliance Badges ---
        if st.session_state.target_min is not None or st.session_state.target_max is not None:
            st.divider()
            st.subheader("✅ Conformité")

            wc_comp = result.compliance["wc_compliant"]
            rss_comp = result.compliance["rss_compliant"]

            col_badge1, col_badge2 = st.columns(2)
            with col_badge1:
                if wc_comp:
                    st.success("✅ **WC : GO** — Dans les tolérances")
                else:
                    st.error("❌ **WC : NO-GO** — Hors tolérances")
                if result.compliance["wc_margin_min"] is not None:
                    st.caption(f"Marge min: {result.compliance['wc_margin_min']:.4f} mm")
                if result.compliance["wc_margin_max"] is not None:
                    st.caption(f"Marge max: {result.compliance['wc_margin_max']:.4f} mm")

            with col_badge2:
                if rss_comp:
                    st.success("✅ **RSS : GO** — Dans les tolérances")
                else:
                    st.error("❌ **RSS : NO-GO** — Hors tolérances")
                if result.compliance["rss_margin_min"] is not None:
                    st.caption(f"Marge min: {result.compliance['rss_margin_min']:.4f} mm")
                if result.compliance["rss_margin_max"] is not None:
                    st.caption(f"Marge max: {result.compliance['rss_margin_max']:.4f} mm")

        # --- Pareto Chart ---
        if result.pareto:
            st.divider()
            st.subheader("📈 Analyse de Pareto (Contribution à la variance)")

            pareto_df = pd.DataFrame(result.pareto)
            fig_pareto = go.Figure(go.Bar(
                x=pareto_df["contribution_pct"],
                y=pareto_df["name"],
                orientation="h",
                marker_color=px.colors.sequential.Blues_r[:len(pareto_df)],
                text=[f"{v:.1f}%" for v in pareto_df["contribution_pct"]],
                textposition="auto",
                hovertemplate="<b>%{y}</b><br>IT: %{customdata:.4f} mm<br>Contribution: %{x:.1f}%<extra></extra>",
                customdata=pareto_df["IT"],
            ))
            fig_pareto.update_layout(
                xaxis_title="Contribution à la variance (%)",
                yaxis_title="Maillon",
                height=max(300, 50 * len(pareto_df)),
                margin=dict(l=120, r=20, t=20, b=40),
                showlegend=False,
            )
            fig_pareto.update_xaxes(range=[0, 100])
            st.plotly_chart(fig_pareto, use_container_width=True)

        # --- Gaussian Distribution Chart ---
        st.divider()
        st.subheader("📉 Distribution statistique (RSS)")

        # Create normal distribution curve
        import numpy as np
        x = np.linspace(result.mean - 4 * (it_rss / 2), result.mean + 4 * (it_rss / 2), 500)
        sigma = it_rss / 2
        from scipy.stats import norm
        y = norm.pdf(x, loc=result.mean, scale=sigma)

        fig_dist = go.Figure()

        # Gaussian curve
        fig_dist.add_trace(go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="Distribution RSS (3σ)",
            line=dict(color="#0284c7", width=2),
            fill="tozeroy",
            fillcolor="rgba(2, 132, 199, 0.1)",
        ))

        # Mean line
        fig_dist.add_vline(
            x=result.mean,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Moyenne = {result.mean:.4f}",
            annotation_position="top",
        )

        # WC bounds
        fig_dist.add_vline(
            x=result.worst_case_minus,
            line_dash="dot",
            line_color="red",
            annotation_text=f"WC Min = {result.worst_case_minus:.4f}",
            annotation_position="top left",
        )
        fig_dist.add_vline(
            x=result.worst_case_plus,
            line_dash="dot",
            line_color="red",
            annotation_text=f"WC Max = {result.worst_case_plus:.4f}",
            annotation_position="top right",
        )

        # RSS bounds (±3σ equivalent)
        fig_dist.add_vline(
            x=result.rss_minus,
            line_dash="dashdot",
            line_color="#0284c7",
            annotation_text=f"RSS Min = {result.rss_minus:.4f}",
            annotation_position="bottom left",
        )
        fig_dist.add_vline(
            x=result.rss_plus,
            line_dash="dashdot",
            line_color="#0284c7",
            annotation_text=f"RSS Max = {result.rss_plus:.4f}",
            annotation_position="bottom right",
        )

        # Target bounds
        if st.session_state.target_min is not None:
            fig_dist.add_vline(
                x=st.session_state.target_min,
                line_dash="solid",
                line_color="green",
                line_width=3,
                annotation_text=f"Cible Min = {st.session_state.target_min:.4f}",
                annotation_position="top",
            )
        if st.session_state.target_max is not None:
            fig_dist.add_vline(
                x=st.session_state.target_max,
                line_dash="solid",
                line_color="green",
                line_width=3,
                annotation_text=f"Cible Max = {st.session_state.target_max:.4f}",
                annotation_position="top",
            )

        fig_dist.update_layout(
            xaxis_title="Jeu (mm)",
            yaxis_title="Densité de probabilité",
            height=400,
            margin=dict(l=60, r=60, t=60, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    else:
        st.info("Ajoutez au moins un maillon pour voir les résultats.")

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