"""CotaStack - Standards ISO : Ajustements ISO 286, Tolérances générales ISO 2768-1 & Tolérancement Géométrique ISO GPS (Ⓜ)."""

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
from backend.geometric_tolerances import (
    GeometricSpec,
    evaluate_geometric_spec,
    verify_assembly_interface,
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


def render_bonus_chart(res, current_size: float):
    """Render Plotly line chart of allowable geometric tolerance vs manufactured size under MMR."""
    fig = go.Figure()

    # Build points from minimum to maximum size
    d_min = min(res.mms, res.lms)
    d_max = max(res.mms, res.lms)

    points_x = [d_min, d_max]
    if res.spec.feature_type == "arbre":
        # Shaft: at d_max (MMS), tol = t0; at d_min (LMS), tol = t0 + IT
        points_y = [res.spec.base_tolerance + res.max_bonus, res.spec.base_tolerance] if res.spec.mmr else [res.spec.base_tolerance, res.spec.base_tolerance]
    else:
        # Hole: at d_min (MMS), tol = t0; at d_max (LMS), tol = t0 + IT
        points_y = [res.spec.base_tolerance, res.spec.base_tolerance + res.max_bonus] if res.spec.mmr else [res.spec.base_tolerance, res.spec.base_tolerance]

    # Allowance line
    fig.add_trace(go.Scatter(
        x=points_x,
        y=points_y,
        mode="lines+markers",
        name="Tolérance admissible",
        line=dict(color="#0284c7", width=3),
        marker=dict(size=8, color="#0284c7"),
    ))

    # Base tolerance reference line
    fig.add_hline(
        y=res.spec.base_tolerance,
        line_dash="dot",
        line_color="#94a3b8",
        annotation_text=f"Tolérance de base t₀ = {res.spec.base_tolerance:.3f} mm",
        annotation_position="bottom right",
    )

    # Current working point
    fig.add_trace(go.Scatter(
        x=[current_size],
        y=[res.total_geometric_tolerance],
        mode="markers",
        name="Dimension usinée actuelle",
        marker=dict(size=14, color="#ef4444", symbol="star"),
        hovertemplate=f"Cote actuelle : {current_size:.3f} mm<br>Tolérance autorisée : {res.total_geometric_tolerance:.3f} mm<extra></extra>",
    ))

    fig.update_layout(
        title=f"Diagramme de Bonus Ⓜ : Tolérance admissible selon la cote réelle ({res.spec.feature_type})",
        xaxis_title="Cote réelle usinée (mm)",
        yaxis_title="Tolérance géométrique autorisée (mm)",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        plot_bgcolor="#f8fafc",
    )
    return fig


def main() -> None:
    st.title("📋 Référentiel des Standards ISO")
    st.caption("Ajustements ISO 286-1/2, Tolérances générales ISO 2768-1 & Tolérancement Géométrique ISO GPS (Ⓜ)")

    tab_fits, tab_general, tab_gps = st.tabs([
        "🔧 Ajustements ISO 286 (Alésage / Arbre)",
        "📐 Tolérances Générales ISO 2768-1",
        "🎯 Tolérancement Géométrique ISO GPS (Ⓜ)",
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

    # ==========================================
    # TAB 3: ISO GPS GEOMETRIC TOLERANCES & MMR Ⓜ
    # ==========================================
    with tab_gps:
        st.subheader("🎯 Spécifications Géométriques ISO GPS & Exigence du Maximum de Matière (MMR Ⓜ)")
        st.markdown(
            "Conforme aux normes **ISO 2692**, **ISO 1101** et **ASME Y14.5**. "
            "Le modificateur **Ⓜ (Maximum Material Requirement)** autorise l'accroissement de la tolérance "
            "géométrique lorsque la dimension effective de la pièce s'éloigne de son état au maximum de matière ($MMS$)."
        )

        st.markdown("### 1. Simulateur de Spécification Géométrique & Bonus Ⓜ")

        col_gps_left, col_gps_right = st.columns([1, 1])

        with col_gps_left:
            feature_kind = st.radio(
                "Type d'élément tolérancé",
                options=["arbre", "alesage"],
                format_func=lambda x: "Arbre / Pièce mâle (matière max = cote maxi)" if x == "arbre" else "Alésage / Pièce femelle (matière max = cote mini)",
                horizontal=True,
                key="gps_feature_kind",
            )

            col_dim1, col_dim2 = st.columns(2)
            with col_dim1:
                gps_nominal = st.number_input(
                    "Diamètre nominal (mm)",
                    min_value=0.5,
                    max_value=500.0,
                    value=20.0,
                    step=1.0,
                    key="gps_nominal",
                )
            with col_dim2:
                gps_tol_type = st.selectbox(
                    "Tolérance géométrique",
                    options=["localisation", "perpendicularite", "parallelisme", "coaxialite", "battement", "symetrie"],
                    format_func=lambda x: {
                        "localisation": "⌖ Localisation",
                        "perpendicularite": "⟂ Perpendicularité",
                        "parallelisme": "∥ Parallélisme",
                        "coaxialite": "◎ Coaxialité",
                        "battement": "↗ Battement circulaire",
                        "symetrie": "⌯ Symétrie",
                    }[x],
                    key="gps_tol_type",
                )

            use_iso_symbol = st.checkbox("Définir les écarts dimensionnels via un symbole ISO 286", value=True, key="gps_use_iso")
            if use_iso_symbol:
                available_syms = symbols["shafts"] if feature_kind == "arbre" else symbols["holes"]
                default_sym = "h7" if feature_kind == "arbre" else "H7"
                sym_idx = available_syms.index(default_sym) if default_sym in available_syms else 0
                chosen_sym = st.selectbox("Classe de tolérance ISO 286", options=available_syms, index=sym_idx, key="gps_chosen_sym")
                calc_ei, calc_es = get_iso286_limits(gps_nominal, chosen_sym)
                gps_es = calc_es
                gps_ei = calc_ei
                st.caption(f"Écarts calculés : **ES = {gps_es:+.4f} mm**, **EI = {gps_ei:+.4f} mm** (IT = {gps_es-gps_ei:.4f} mm)")
            else:
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    gps_es = st.number_input("Écart Supérieur ES (mm)", value=0.000, step=0.005, format="%.4f", key="gps_es_manual")
                with col_e2:
                    gps_ei = st.number_input("Écart Inférieur EI (mm)", value=-0.021 if feature_kind == "arbre" else 0.000, step=0.005, format="%.4f", key="gps_ei_manual")

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                base_t0 = st.number_input(
                    "Tolérance de base t₀ (mm)",
                    min_value=0.001,
                    max_value=2.0,
                    value=0.050,
                    step=0.010,
                    format="%.3f",
                    key="gps_base_t0",
                    help="Tolérance géométrique spécifiée sur le dessin au pire cas matière (MMS)",
                )
            with col_t2:
                enable_mmr = st.checkbox("Modificateur Ⓜ (MMR)", value=True, key="gps_enable_mmr", help="Active l'exigence du maximum de matière (ISO 2692)")

            spec = GeometricSpec(
                name=f"{gps_tol_type.capitalize()} Ø{gps_nominal}",
                feature_type=feature_kind,  # type: ignore
                tolerance_type=gps_tol_type,  # type: ignore
                nominal_size=gps_nominal,
                es=gps_es,
                ei=gps_ei,
                base_tolerance=base_t0,
                mmr=enable_mmr,
            )

            # Manufactured size slider
            min_size = min(gps_nominal + gps_ei, gps_nominal + gps_es)
            max_size = max(gps_nominal + gps_ei, gps_nominal + gps_es)
            default_slider = (min_size + max_size) / 2.0

            actual_size_input = st.slider(
                "Dimension réelle usinée de la pièce (mm)",
                min_value=float(round(min_size, 4)),
                max_value=float(round(max_size, 4)),
                value=float(round(default_slider, 4)),
                step=0.001,
                format="%.3f mm",
                key="gps_actual_slider",
            )

        with col_gps_right:
            eval_res = evaluate_geometric_spec(spec, actual_size=actual_size_input)

            # Metric cards
            col_k1, col_k2, col_k3 = st.columns(3)
            with col_k1:
                st.metric("État Max Matière (MMS)", f"{eval_res.mms:.3f} mm")
                st.metric("Bonus effectif", f"+{eval_res.actual_bonus:.3f} mm")
            with col_k2:
                st.metric("État Min Matière (LMS)", f"{eval_res.lms:.3f} mm")
                st.metric("Tolérance totale autorisée", f"{eval_res.total_geometric_tolerance:.3f} mm")
            with col_k3:
                st.metric("État Virtuel (Vc)", f"{eval_res.virtual_condition:.3f} mm")
                st.metric("Bonus maximal possible", f"+{eval_res.max_bonus:.3f} mm")

            st.info(eval_res.explanation)
            st.plotly_chart(render_bonus_chart(eval_res, actual_size_input), use_container_width=True)

        st.divider()

        # ==========================================
        # 2. VÉRIFICATION D'ASSEMBLABILITÉ D'INTERFACE
        # ==========================================
        st.markdown("### 2. Vérification d'Assemblabilité & État Virtuel ($V_c$)")
        st.caption("Contrôle garanti 100% sans risque de collision entre alésage et arbre sous modificateurs Ⓜ (ISO 2692).")

        col_ass_h, col_ass_s = st.columns(2)
        with col_ass_h:
            st.markdown("#### 🔵 Alésage Récepteur (Femelle)")
            h_nom = st.number_input("Diamètre nominal Alésage (mm)", value=25.0, step=1.0, key="ass_h_nom")
            col_he1, col_he2 = st.columns(2)
            with col_he1:
                h_es = st.number_input("ES Alésage (mm)", value=0.021, step=0.005, format="%.4f", key="ass_h_es")
            with col_he2:
                h_ei = st.number_input("EI Alésage (mm)", value=0.000, step=0.005, format="%.4f", key="ass_h_ei")
            h_t0 = st.number_input("Tolérance géométrique Alésage t₀ (mm)", value=0.020, step=0.005, format="%.3f", key="ass_h_t0")
            h_spec = GeometricSpec("Alésage", "alesage", "localisation", h_nom, h_es, h_ei, h_t0, mmr=True)

        with col_ass_s:
            st.markdown("#### 🟢 Arbre Inséré (Mâle)")
            s_nom = st.number_input("Diamètre nominal Arbre (mm)", value=25.0, step=1.0, key="ass_s_nom")
            col_se1, col_se2 = st.columns(2)
            with col_se1:
                s_es = st.number_input("es Arbre (mm)", value=-0.020, step=0.005, format="%.4f", key="ass_s_es")
            with col_se2:
                s_ei = st.number_input("ei Arbre (mm)", value=-0.041, step=0.005, format="%.4f", key="ass_s_ei")
            s_t0 = st.number_input("Tolérance géométrique Arbre t₀ (mm)", value=0.020, step=0.005, format="%.3f", key="ass_s_t0")
            s_spec = GeometricSpec("Arbre", "arbre", "localisation", s_nom, s_es, s_ei, s_t0, mmr=True)

        try:
            ass_res = verify_assembly_interface(h_spec, s_spec)
            if ass_res.is_assemblable:
                st.success(
                    f"### {ass_res.verdict}\n\n"
                    f"- **État virtuel Alésage ($V_{{c,\\text{{alésage}}}} = D_{{\\min}} - t_{{0,\\text{{alésage}}}}$)** : `{ass_res.hole_vc:.4f} mm`\n"
                    f"- **État virtuel Arbre ($V_{{c,\\text{{arbre}}}} = d_{{\\max}} + t_{{0,\\text{{arbre}}}}$)** : `{ass_res.shaft_vc:.4f} mm`\n"
                    f"- **Jeu résiduel minimal garanti** : `{ass_res.guaranteed_min_clearance:+.4f} mm`"
                )
            else:
                st.error(
                    f"### {ass_res.verdict}\n\n"
                    f"- **État virtuel Alésage ($V_{{c,\\text{{alésage}}}}$)** : `{ass_res.hole_vc:.4f} mm`\n"
                    f"- **État virtuel Arbre ($V_{{c,\\text{{arbre}}}}$)** : `{ass_res.shaft_vc:.4f} mm`\n"
                    f"- **Interférence prévisible au pire cas** : `{-ass_res.guaranteed_min_clearance:.4f} mm`"
                )
        except Exception as err:
            st.error(f"Erreur de calcul d'assemblage : {err}")

    # --- Global Disclaimer ---
    st.divider()
    st.warning(
        "⚠️ **Avertissement** : Outil d'aide à la conception. "
        "L'utilisateur demeure seul responsable de la validation technique avant fabrication."
    )


if __name__ == "__main__":
    main()
