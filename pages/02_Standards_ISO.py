"""CotaStack - Standards ISO : Ajustements ISO 286 et Tolérances générales ISO 2768-1."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from backend.iso_standards import (
    get_available_iso286_symbols,
    get_iso286_limits,
    calculate_fit,
    get_iso2768_linear_tolerance,
    get_iso2768_broken_edges_tolerance,
    get_iso2768_angular_tolerance,
    ISO_2768_1_LINEAR,
    ISO_2768_1_BROKEN_EDGES,
    ISO_2768_1_ANGULAR,
)

st.set_page_config(
    page_title="Standards ISO — CotaStack",
    page_icon="📋",
    layout="wide",
)


def render_fit_chart(res):
    """Render Plotly bar chart visualizing hole vs shaft tolerance zones."""
    fig = go.Figure()

    # Convert mm to µm for readable chart units
    hole_ei_um = res.hole_ei * 1000.0
    hole_es_um = res.hole_es * 1000.0
    shaft_ei_um = res.shaft_ei * 1000.0
    shaft_es_um = res.shaft_es * 1000.0

    hole_width_um = hole_es_um - hole_ei_um
    shaft_width_um = shaft_es_um - shaft_ei_um

    # Zero nominal line
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#64748b",
        annotation_text="Ligne Zéro (Nominal)",
        annotation_position="bottom right",
    )

    # Hole tolerance bar
    fig.add_trace(go.Bar(
        name=f"Alésage {res.hole_symbol}",
        x=["Alésage"],
        y=[hole_width_um],
        base=[hole_ei_um],
        marker=dict(color="#0284c7"),
        hovertemplate=f"<b>Alésage {res.hole_symbol}</b><br>EI: {res.hole_ei:+.3f} mm<br>ES: {res.hole_es:+.3f} mm<br>IT: {res.hole_es - res.hole_ei:.3f} mm<extra></extra>",
    ))

    # Shaft tolerance bar
    shaft_color = "#10b981" if res.fit_type == "jeu" else ("#ef4444" if res.fit_type == "serrage" else "#f59e0b")
    fig.add_trace(go.Bar(
        name=f"Arbre {res.shaft_symbol}",
        x=["Arbre"],
        y=[shaft_width_um],
        base=[shaft_ei_um],
        marker=dict(color=shaft_color),
        hovertemplate=f"<b>Arbre {res.shaft_symbol}</b><br>ei: {res.shaft_ei:+.3f} mm<br>es: {res.shaft_es:+.3f} mm<br>IT: {res.shaft_es - res.shaft_ei:.3f} mm<extra></extra>",
    ))

    fig.update_layout(
        title=f"Positionnement relatif des IT — Ø{res.nominal:.2f} {res.hole_symbol}/{res.shaft_symbol}",
        yaxis_title="Écart par rapport au nominal (µm)",
        xaxis_title="Composant",
        height=400,
        margin=dict(l=40, r=40, t=50, b=40),
        barmode="group",
        plot_bgcolor="#f8fafc",
    )
    return fig


def main() -> None:
    st.title("📋 Référentiel des Standards ISO")
    st.caption("Ajustements ISO 286-1/2 et Tolérances générales ISO 2768-1")

    tab_fits, tab_general = st.tabs([
        "🔧 Ajustements ISO 286 (Alésage / Arbre)",
        "📐 Tolérances Générales ISO 2768-1",
    ])

    # ==========================================
    # TAB 1: ISO 286 FITS
    # ==========================================
    with tab_fits:
        st.subheader("Calculateur d'ajustements mécaniques (ISO 286)")

        symbols = get_available_iso286_symbols()

        col_input1, col_input2, col_input3 = st.columns(3)
        with col_input1:
            nominal = st.number_input(
                "Diamètre nominal (mm)",
                min_value=0.1,
                max_value=500.0,
                value=20.0,
                step=1.0,
                format="%.2f",
                help="Diamètre nominal de la liaison cylindrique (≤ 500 mm)",
            )

        with col_input2:
            default_hole_idx = symbols["holes"].index("H7") if "H7" in symbols["holes"] else 0
            hole_symbol = st.selectbox(
                "Alésage (Pièce femelle)",
                options=symbols["holes"],
                index=default_hole_idx,
                help="Tolérance de l'alésage (lettre majuscule)",
            )

        with col_input3:
            default_shaft_idx = symbols["shafts"].index("g6") if "g6" in symbols["shafts"] else 0
            shaft_symbol = st.selectbox(
                "Arbre (Pièce mâle)",
                options=symbols["shafts"],
                index=default_shaft_idx,
                help="Tolérance de l'arbre (lettre minuscule)",
            )

        # Calculation
        try:
            res = calculate_fit(nominal, hole_symbol, shaft_symbol)
        except Exception as e:
            st.error(f"Erreur lors du calcul : {e}")
            return

        # Fit Type Banner
        st.divider()
        if res.fit_type == "jeu":
            st.success(
                f"### 🟢 Ajustement avec JEU : Ø{res.nominal:.2f} {res.hole_symbol}/{res.shaft_symbol}\n"
                f"- **Jeu minimal ($J_{{min}}$)** : `{res.min_clearance * 1000:+.1f} µm` ({res.min_clearance:+.4f} mm)\n"
                f"- **Jeu maximal ($J_{{max}}$)** : `{res.max_clearance * 1000:+.1f} µm` ({res.max_clearance:+.4f} mm)"
            )
        elif res.fit_type == "serrage":
            st.error(
                f"### 🔴 Ajustement avec SERRAGE : Ø{res.nominal:.2f} {res.hole_symbol}/{res.shaft_symbol}\n"
                f"- **Serrage minimal ($S_{{min}}$)** : `{-res.max_clearance * 1000:+.1f} µm` ({-res.max_clearance:+.4f} mm)\n"
                f"- **Serrage maximal ($S_{{max}}$)** : `{-res.min_clearance * 1000:+.1f} µm` ({-res.min_clearance:+.4f} mm)"
            )
        else:
            st.warning(
                f"### 🟠 Ajustement INCERTAIN (Transition) : Ø{res.nominal:.2f} {res.hole_symbol}/{res.shaft_symbol}\n"
                f"- **Serrage maximal ($S_{{max}}$)** : `{-res.min_clearance * 1000:+.1f} µm` ({-res.min_clearance:+.4f} mm)\n"
                f"- **Jeu maximal ($J_{{max}}$)** : `{res.max_clearance * 1000:+.1f} µm` ({res.max_clearance:+.4f} mm)"
            )

        # Metric cards
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown(f"#### Alésage **{res.hole_symbol}**")
            st.markdown(f"- Écart inférieur ($EI$) : `{res.hole_ei:+.4f} mm` ({res.hole_ei*1000:+.0f} µm)")
            st.markdown(f"- Écart supérieur ($ES$) : `{res.hole_es:+.4f} mm` ({res.hole_es*1000:+.0f} µm)")
            st.markdown(f"- Intervalle de tolérance ($IT$) : `{(res.hole_es - res.hole_ei)*1000:.1f} µm`")
            st.markdown(f"- Cote effective : **[{res.hole_min:.4f} ; {res.hole_max:.4f}] mm**")

        with col_m2:
            st.markdown(f"#### Arbre **{res.shaft_symbol}**")
            st.markdown(f"- Écart inférieur ($ei$) : `{res.shaft_ei:+.4f} mm` ({res.shaft_ei*1000:+.0f} µm)")
            st.markdown(f"- Écart supérieur ($es$) : `{res.shaft_es:+.4f} mm` ({res.shaft_es*1000:+.0f} µm)")
            st.markdown(f"- Intervalle de tolérance ($it$) : `{(res.shaft_es - res.shaft_ei)*1000:.1f} µm`")
            st.markdown(f"- Cote effective : **[{res.shaft_min:.4f} ; {res.shaft_max:.4f}] mm**")

        # Interactive chart
        st.plotly_chart(render_fit_chart(res), use_container_width=True)

        # Action: Quick insert hint
        st.info(
            f"💡 **Astuce d'intégration** : Vous pouvez réutiliser directement les écarts calculés "
            f"(Alésage : `ES={res.hole_es:+.4f}`, `EI={res.hole_ei:+.4f}` | Arbre : `es={res.shaft_es:+.4f}`, `ei={res.shaft_ei:+.4f}`) "
            f"dans la page **🧮 Calculateur** pour vos chaînes de cotes."
        )

    # ==========================================
    # TAB 2: ISO 2768-1 GENERAL TOLERANCES
    # ==========================================
    with tab_general:
        st.subheader("Tolérances générales d'usinage (ISO 2768-1)")
        st.markdown(
            "La norme **ISO 2768-1** s'applique aux dimensions linéaires et angulaires "
            "ne comportant pas d'indication individuelle de tolérance."
        )

        col_g1, col_g2 = st.columns([1, 2])
        with col_g1:
            grade = st.radio(
                "Classe de précision",
                options=["f", "m", "c", "v"],
                format_func=lambda x: {
                    "f": "f — Fine (mécanique de précision)",
                    "m": "m — Moyenne (usinage général courant)",
                    "c": "c — Grosse (tôlerie, mécano-soudure)",
                    "v": "v — Très grosse (fonderie, pièces brutes)",
                }[x],
                index=1,
            )

            test_dim = st.number_input(
                "Tester une dimension (mm)",
                min_value=0.1,
                max_value=4000.0,
                value=25.0,
                step=1.0,
                format="%.1f",
            )
            tol_lin = get_iso2768_linear_tolerance(test_dim, grade)  # type: ignore
            tol_edge = get_iso2768_broken_edges_tolerance(test_dim, grade)  # type: ignore

            st.metric(f"Tolérance linéaire (± mm) pour {test_dim:.1f} mm", f"± {tol_lin:.2f} mm")
            st.metric(f"Tolérance chanfreins/arrondis pour {test_dim:.1f} mm", f"± {tol_edge:.2f} mm")

        with col_g2:
            st.markdown("#### Table complète des tolérances linéaires (± mm)")
            lin_data = []
            for (low, high) in ISO_2768_1_LINEAR["m"].keys():
                lin_data.append({
                    "Palier (mm)": f"> {low} à {high}",
                    "f (fine)": f"± {ISO_2768_1_LINEAR['f'][(low, high)]:.2f}",
                    "m (moyenne)": f"± {ISO_2768_1_LINEAR['m'][(low, high)]:.2f}",
                    "c (grosse)": f"± {ISO_2768_1_LINEAR['c'][(low, high)]:.2f}",
                    "v (très grosse)": f"± {ISO_2768_1_LINEAR['v'][(low, high)]:.2f}",
                })
            st.dataframe(pd.DataFrame(lin_data), use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("### 🔔 Veille normative : Transition vers ISO 22081:2021")
        st.info(r"""
        **Remplacement de l'ancienne norme ISO 2768-2 :**  
        Depuis 2021, la norme **ISO 22081** remplace l'ancienne norme de tolérancement géométrique général ISO 2768-2.  
        Elle préconise l'utilisation d'une **spécification par profil de surface généralisé** rattaché à un système de références spécifié dans le cartouche (ex: `Tolérancement général : ISO 22081 | ⌒ 0.5 | A | B | C`).  
        Dans vos chaînes de cotes 1D, un défaut de profil ou de localisation se projette vectoriellement sur l'axe fonctionnel comme une contribution symétrique $\pm IT/2$.
        """)

    # --- Global Disclaimer ---
    st.divider()
    st.warning(
        "⚠️ **Avertissement** : Outil d'aide à la conception. "
        "L'utilisateur demeure seul responsable de la validation technique avant fabrication."
    )


if __name__ == "__main__":
    main()
