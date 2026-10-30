"""CotaStack - Répertoire Unifié Multi-Chaînes (Jalon 3.1).

Gestion centralisée des pièces maîtresses, Schéma vectoriel 1D & Calculs arithmétiques au Pire des Cas (Worst-Case).
Interface ergonomique et visuelle enrichie pour les bureaux d'études.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from backend.multi_chain import (
    CatalogPart,
    ChainLink,
    AssemblyChain,
    MultiChainProject,
)
from backend.iso_standards import get_available_iso286_symbols, get_iso286_limits
from backend.thermal import get_available_materials

st.set_page_config(
    page_title="Multi-Chaînes Système — CotaStack",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Masquage complet de la barre latérale et styling moderne
st.markdown(
    """
    <style>
    [data-testid="stSidebar"], 
    [data-testid="stSidebarCollapsedControl"], 
    [data-testid="collapsedControl"],
    section[data-testid="stSidebar"] {
        display: none !important;
        visibility: hidden !important;
        width: 0px !important;
    }
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px;
    }
    .status-badge-ok {
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .status-badge-nok {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .vector-badge-pos {
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: bold;
    }
    .vector-badge-neg {
        background-color: #ffedd5;
        color: #c2410c;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_default_project() -> MultiChainProject:
    """Initialize a realistic multi-chain mechanical transmission demo project."""
    proj = MultiChainProject(
        name="Réducteur Mécanique - Boîte de Vitesses",
        description="Assemblage complet : carter, arbre secondaire, roulements, circlips et cales d'épaisseur.",
    )

    # 1. Catalog master parts
    proj.add_part(CatalogPart(
        id="CARTER",
        name="Carter principal",
        nominal=140.0,
        es=0.040,
        ei=-0.040,
        material="Aluminium",
        description="Alésage intérieur de loge d'arbre",
    ))
    proj.add_part(CatalogPart(
        id="ARBRE",
        name="Arbre secondaire",
        nominal=100.0,
        es=0.020,
        ei=-0.020,
        material="Acier (standard)",
        description="Longueur entre portées d'épaulement",
    ))
    proj.add_part(CatalogPart(
        id="ROULEMENT",
        name="Roulement à billes 6205",
        nominal=15.0,
        es=0.012,
        ei=-0.012,
        material="Acier (standard)",
        description="Largeur de bague extérieure standard",
    ))
    proj.add_part(CatalogPart(
        id="CIRCLIPS",
        name="Circlips d'arrêt",
        nominal=2.5,
        es=0.008,
        ei=-0.008,
        material="Acier (standard)",
        description="Épaisseur standard DIN 471",
    ))
    proj.add_part(CatalogPart(
        id="CALE",
        name="Cale de précharge",
        nominal=6.0,
        es=0.015,
        ei=-0.015,
        material="Acier (standard)",
        description="Cale rectifiée d'ajustement axial",
    ))

    # 2. Chain 1: Jeu axial principal (CARTER (+) - ARBRE (-) - 2*ROULEMENT (-) - CALE (-))
    c1 = AssemblyChain(
        id="CH_AXIAL_PRINCIPAL",
        name="Jeu axial global d'arbre",
        description="Garantit l'absence de bridage axial à chaud et le libre jeu des roulements.",
        target_min=0.300,
        target_max=1.800,
    )
    proj.add_chain(c1)
    proj.add_link_to_chain("CH_AXIAL_PRINCIPAL", part_id="CARTER", orientation=1)
    proj.add_link_to_chain("CH_AXIAL_PRINCIPAL", part_id="ARBRE", orientation=-1)
    proj.add_link_to_chain("CH_AXIAL_PRINCIPAL", part_id="ROULEMENT", orientation=-1, custom_name="Roulement gauche")
    proj.add_link_to_chain("CH_AXIAL_PRINCIPAL", part_id="ROULEMENT", orientation=-1, custom_name="Roulement droit")
    proj.add_link_to_chain("CH_AXIAL_PRINCIPAL", part_id="CALE", orientation=-1)

    # 3. Chain 2: Jeu gorge circlips (GORGE (+) - CIRCLIPS (-))
    c2 = AssemblyChain(
        id="CH_GORGE_CIRCLIPS",
        name="Jeu dans gorge circlips",
        description="Vérifie le montage aisé de l'anneau élastique dans sa rainure d'arbre.",
        target_min=0.050,
        target_max=0.350,
    )
    proj.add_chain(c2)
    proj.add_link_to_chain("CH_GORGE_CIRCLIPS", part_id="CIRCLIPS", orientation=-1)
    proj.add_link_to_chain("CH_GORGE_CIRCLIPS", orientation=1, local_nominal=2.70, local_es=0.05, local_ei=0.0, custom_name="Largeur gorge usinée")

    # 4. Chain 3: Garde étanchéité carter/arbre (CARTER (+) - ARBRE (-) - CALE (-))
    c3 = AssemblyChain(
        id="CH_GARDE_JOINT",
        name="Garde axiale joint d'étanchéité",
        description="Positionnement relatif du joint à lèvre par rapport au carter.",
        target_min=32.0,
        target_max=36.0,
    )
    proj.add_chain(c3)
    proj.add_link_to_chain("CH_GARDE_JOINT", part_id="CARTER", orientation=1)
    proj.add_link_to_chain("CH_GARDE_JOINT", part_id="ARBRE", orientation=-1)
    proj.add_link_to_chain("CH_GARDE_JOINT", part_id="CALE", orientation=-1)

    return proj


def render_1d_stack_diagram(chain: AssemblyChain, project: MultiChainProject):
    """Generate an interactive 1D vector stack-up engineering diagram for the active chain."""
    fig = go.Figure()

    if not chain.links:
        fig.add_annotation(
            text="Aucun maillon dans cette chaîne.<br>Ajoutez des maillons pour visualiser la boucle 1D.",
            showarrow=False,
            font=dict(size=14, color="#64748b"),
        )
        fig.update_layout(height=260, plot_bgcolor="#f8fafc")
        return fig

    # Cumulative positions
    current_x = 0.0
    y_pos = 0.0
    y_labels = []

    pos_color = "#0284c7"   # Blue for positive vectors (+)
    neg_color = "#f97316"   # Orange for negative vectors (-)

    for idx, link in enumerate(chain.links):
        if link.part_id:
            p = project.parts.get(link.part_id)
            nom = (p.nominal * link.scale_factor) if p else 0.0
            name = link.custom_name or (p.name if p else f"Pièce [{link.part_id}]")
            source_tag = f"[{link.part_id}]"
        else:
            nom = (link.local_nominal or 0.0) * link.scale_factor
            name = link.custom_name or f"Cote locale {idx+1}"
            source_tag = "Locale"

        start_x = current_x
        step_val = link.orientation * nom
        end_x = start_x + step_val
        current_x = end_x

        line_color = pos_color if link.orientation > 0 else neg_color
        orient_sym = "+" if link.orientation > 0 else "-"
        y_val = len(chain.links) - idx

        y_labels.append(f"#{idx+1} {name[:18]}")

        # Vector line
        fig.add_trace(go.Scatter(
            x=[start_x, end_x],
            y=[y_val, y_val],
            mode="lines+markers",
            line=dict(color=line_color, width=4),
            marker=dict(symbol="arrow-bar-right" if link.orientation > 0 else "arrow-bar-left", size=10, color=line_color),
            name=f"#{idx+1} {name}",
            hovertemplate=(
                f"<b>#{idx+1} : {name}</b> ({source_tag})<br>"
                f"Orientation: {orient_sym}1<br>"
                f"Nominal: {nom:.3f} mm<br>"
                f"Cumul: [{start_x:.3f} &rarr; {end_x:.3f}] mm<extra></extra>"
            ),
        ))

        # Vector midpoint text annotation
        mid_x = (start_x + end_x) / 2
        fig.add_annotation(
            x=mid_x,
            y=y_val + 0.35,
            text=f"<b>{orient_sym}{nom:.2f}</b> ({name[:16]})",
            showarrow=False,
            font=dict(size=11, color=line_color),
        )

    # Closing Game Vector (Jeu résultant)
    res_game = current_x
    fig.add_trace(go.Scatter(
        x=[0.0, res_game],
        y=[0, 0],
        mode="lines+markers",
        line=dict(color="#10b981", width=5, dash="solid"),
        marker=dict(symbol="diamond", size=10, color="#10b981"),
        name="Jeu résultant J_nom",
        hovertemplate=f"<b>Jeu nominal de fermeture (J_nom)</b> : {res_game:.4f} mm<extra></extra>",
    ))
    fig.add_annotation(
        x=res_game / 2,
        y=-0.4,
        text=f"<b>FERMETURE : Jeu J_nom = {res_game:.3f} mm</b>",
        showarrow=False,
        font=dict(size=12, color="#059669"),
    )

    # Reference origin vertical line
    fig.add_vline(x=0.0, line_dash="dot", line_color="#94a3b8")

    fig.update_layout(
        title=f"📐 Boucle vectorielle 1D de la chaîne : {chain.name}",
        xaxis_title="Position dimensionnelle cumulée (mm)",
        yaxis=dict(
            showticklabels=False,
            range=[-0.8, len(chain.links) + 0.8],
        ),
        height=max(280, 50 * len(chain.links) + 120),
        margin=dict(l=30, r=30, t=50, b=30),
        plot_bgcolor="#f8fafc",
        showlegend=False,
    )
    return fig


def render_wc_range_chart(res, target_min: float | None, target_max: float | None, chain_name: str):
    """Plot visual range of calculated Worst-Case stack-up vs functional targets."""
    fig = go.Figure()

    wc_min = res.worst_case_minus
    wc_max = res.worst_case_plus
    j_nom = res.nominal

    # Target functional area background if limits are specified
    if target_min is not None and target_max is not None and target_max > target_min:
        fig.add_shape(
            type="rect",
            xref="x", yref="paper",
            x0=target_min, x1=target_max,
            y0=0, y1=1,
            fillcolor="#dcfce7",
            opacity=0.5,
            layer="below",
            line_width=0,
        )

    # Calculated WC bar
    is_compliant = True
    if target_min is not None and wc_min < target_min:
        is_compliant = False
    if target_max is not None and wc_max > target_max:
        is_compliant = False

    bar_color = "#0284c7" if is_compliant else "#ef4444"

    fig.add_trace(go.Bar(
        name="Plage Pire des Cas (WC)",
        y=["Jeu fonctionnel"],
        x=[wc_max - wc_min],
        base=[wc_min],
        orientation="h",
        marker=dict(color=bar_color),
        hovertemplate=(
            f"<b>Jeu Pire des Cas (Worst-Case)</b><br>"
            f"J_min (WC): {wc_min:.4f} mm<br>"
            f"J_max (WC): {wc_max:.4f} mm<br>"
            f"Dispersion IT: {wc_max - wc_min:.4f} mm<extra></extra>"
        ),
    ))

    # Nominal marker
    fig.add_trace(go.Scatter(
        name="Jeu nominal",
        x=[j_nom],
        y=["Jeu fonctionnel"],
        mode="markers",
        marker=dict(color="#0f172a", size=16, symbol="line-ns", line=dict(width=3, color="#0f172a")),
        hovertemplate=f"Jeu nominal (J_nom): {j_nom:.4f} mm<extra></extra>",
    ))

    # Target lines
    if target_min is not None:
        fig.add_vline(
            x=target_min,
            line_dash="dash",
            line_color="#059669" if wc_min >= target_min else "#dc2626",
            line_width=2,
            annotation_text=f"Cible Min ({target_min:.3f})",
            annotation_position="top left",
        )
    if target_max is not None:
        fig.add_vline(
            x=target_max,
            line_dash="dash",
            line_color="#059669" if wc_max <= target_max else "#dc2626",
            line_width=2,
            annotation_text=f"Cible Max ({target_max:.3f})",
            annotation_position="top right",
        )

    fig.update_layout(
        title=f"Positionnement arithmétique Pire des Cas (WC) — {chain_name}",
        xaxis_title="Jeu résultant (mm)",
        height=210,
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor="#f8fafc",
        showlegend=False,
    )
    return fig


def render_impact_heatmap(project: MultiChainProject, summary):
    """Plot an interactive 2D cross-impact matrix (Parts x Chains) highlighting pivot parts."""
    parts_ids = list(project.parts.keys())
    chains_ids = list(project.chains.keys())

    if not parts_ids or not chains_ids:
        fig = go.Figure()
        fig.add_annotation(
            text="Catalogue ou chaînes insuffisants pour tracer la matrice.",
            showarrow=False,
            font=dict(size=14, color="#64748b"),
        )
        fig.update_layout(height=260, plot_bgcolor="#f8fafc")
        return fig

    z_matrix = []
    text_matrix = []

    for c_id in chains_ids:
        c = project.get_chain(c_id)
        row_z = []
        row_txt = []
        # Count orientation contributions
        for p_id in parts_ids:
            matching_links = [l for l in c.links if l.part_id == p_id]
            if not matching_links:
                row_z.append(0)
                row_txt.append("")
            else:
                orient_sum = sum(l.orientation for l in matching_links)
                if orient_sum > 0:
                    row_z.append(1)
                    row_txt.append(f"+{len(matching_links)}" if len(matching_links) > 1 else "+")
                elif orient_sum < 0:
                    row_z.append(-1)
                    row_txt.append(f"-{len(matching_links)}" if len(matching_links) > 1 else "-")
                else:
                    row_z.append(0.5)
                    row_txt.append("±")
        z_matrix.append(row_z)
        text_matrix.append(row_txt)

    chain_labels = [f"{project.chains[cid].name[:22]} [{cid}]" for cid in chains_ids]
    part_labels = []
    for pid in parts_ids:
        count_used = len(summary.shared_parts_matrix.get(pid, []))
        pivot_tag = "🔥 " if count_used >= 2 else ""
        part_labels.append(f"{pivot_tag}{project.parts[pid].name[:16]} [{pid}]")

    # Custom colorscale: Orange (-1), White (0), Blue (+1)
    colorscale = [
        [0.0, "#ffedd5"],   # -1: Orange light
        [0.45, "#ffffff"],  # 0: Blanc
        [0.55, "#ffffff"],  # 0: Blanc
        [1.0, "#e0f2fe"],   # +1: Bleu light
    ]

    fig = go.Figure(data=go.Heatmap(
        z=z_matrix,
        x=part_labels,
        y=chain_labels,
        text=text_matrix,
        texttemplate="<b>%{text}</b>",
        textfont={"size": 15, "color": "#0f172a"},
        colorscale=colorscale,
        showscale=False,
        xgap=4,
        ygap=4,
        hovertemplate="Pièce: %{x}<br>Chaîne: %{y}<br>Sens: %{text}<extra></extra>",
    ))

    fig.update_layout(
        title="🕸️ Matrice d'Incidence & d'Impact Croisé (Pièces Maîtresses &times; Chaînes)",
        xaxis_title="Pièces du Catalogue (🔥 = Pièce Pivot multi-chaînes)",
        yaxis_title="Chaînes d'Assemblage",
        height=max(260, 45 * len(chains_ids) + 120),
        margin=dict(l=50, r=40, t=50, b=40),
        plot_bgcolor="#f8fafc",
    )
    return fig


def main() -> None:
    # -------------------------------------------------------------------------
    # Initialisation Session State
    # -------------------------------------------------------------------------
    if "multi_project" not in st.session_state:
        st.session_state.multi_project = init_default_project()
    if "uploader_counter" not in st.session_state:
        st.session_state.uploader_counter = 0

    project: MultiChainProject = st.session_state.multi_project
    materials = get_available_materials()
    summary = project.get_system_summary()
    is_empty_project = (len(project.parts) == 0 and len(project.chains) == 0)

    # -------------------------------------------------------------------------
    # En-tête Moderne & Barre de Statut Système (KPIs)
    # -------------------------------------------------------------------------
    with st.container(border=True):
        col_h1, col_h2, col_h3 = st.columns([2.5, 1.2, 1.3])

        with col_h1:
            st.markdown(f"## 🏢 {project.name}")
            desc_text = project.description or "Système mécanique multi-chaînes"
            st.caption(f"{desc_text} • **{len(project.parts)}** pièces maîtresses • **{len(project.chains)}** chaînes d'assemblage")

        with col_h2:
            # System Health Badge
            if summary.total_chains == 0:
                st.markdown("<div class='metric-card'><b>Statut Système</b><br><span style='color:#64748b;'>0 chaîne configurée</span></div>", unsafe_allow_html=True)
            elif summary.wc_compliant_count == summary.total_chains:
                st.markdown(
                    f"<div class='metric-card'><b>Santé Globale (WC)</b><br>"
                    f"<span class='status-badge-ok'>✅ 100% Conforme ({summary.wc_compliant_count}/{summary.total_chains})</span></div>",
                    unsafe_allow_html=True,
                )
            else:
                nok = summary.total_chains - summary.wc_compliant_count
                st.markdown(
                    f"<div class='metric-card'><b>Santé Globale (WC)</b><br>"
                    f"<span class='status-badge-nok'>❌ {nok} chaîne(s) critique(s)</span></div>",
                    unsafe_allow_html=True,
                )

        with col_h3:
            # Action Toolset: Save/Load Popover, Demo, Reset
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                with st.popover("💾 Projet", use_container_width=True):
                    st.markdown("##### 📂 Charger un fichier")
                    up_file = st.file_uploader(
                        "Fichier projet (.cotastack_multi.json)",
                        type=["json"],
                        key=f"pop_up_{st.session_state.uploader_counter}",
                    )
                    if up_file is not None:
                        try:
                            raw_txt = up_file.getvalue().decode("utf-8")
                            loaded = MultiChainProject.from_json(raw_txt)
                            st.session_state.multi_project = loaded
                            st.session_state.uploader_counter += 1
                            st.toast(f"Projet '{loaded.name}' chargé !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fichier invalide : {e}")

                    st.divider()
                    st.markdown("##### 📥 Télécharger le projet")
                    st.download_button(
                        label="Télécharger le fichier .json",
                        data=project.to_json(),
                        file_name=f"{project.name.lower().replace(' ', '_')}.cotastack_multi.json",
                        mime="application/json",
                        use_container_width=True,
                        disabled=is_empty_project,
                    )

            with col_b2:
                with st.popover("⚙️ Actions", use_container_width=True):
                    st.markdown("##### Exemples & Réinitialisation")
                    if st.button("🔄 Démo (Boîte de vitesses)", use_container_width=True):
                        st.session_state.multi_project = init_default_project()
                        st.session_state.uploader_counter += 1
                        st.toast("Exemple complet réinitialisé !")
                        st.rerun()

                    st.divider()
                    st.caption("Zone de réinitialisation complète :")
                    if st.button("🗑️ Repartir à zéro (Vierge)", use_container_width=True, type="secondary"):
                        project.clear_all()
                        project.name = "Nouveau Système Mécanique"
                        project.description = "Projet vierge"
                        st.session_state.uploader_counter += 1
                        st.toast("Projet vidé (0 pièce, 0 chaîne) !")
                        st.rerun()

    # -------------------------------------------------------------------------
    # Onglets Métier
    # -------------------------------------------------------------------------
    tab_catalog, tab_chains, tab_dashboard = st.tabs([
        "📦 Répertoire & Pièces Maîtresses",
        "🔗 Chaînes d'Assemblage & Schéma 1D",
        "📊 Tableau de Bord Système",
    ])

    # =========================================================================
    # ONGLET 1 : CATALOGUE DES PIÈCES MAÎTRESSES
    # =========================================================================
    with tab_catalog:
        st.markdown("### 📦 Catalogue Centralisé des Pièces (Single Source of Truth)")
        st.markdown(
            "Chaque composant physique est modélisé **une seule fois**. "
            "Toute modification de cote ou de tolérance est **propagée et recalculée instantanément** "
            "sur toutes les chaînes d'assemblage du mécanisme."
        )

        col_cat_left, col_cat_right = st.columns([1.6, 1.2])

        with col_cat_left:
            # 1. Parts Table with enhanced visual styling
            parts_rows = []
            for p_id, p in project.parts.items():
                chains_used = project.get_part_impact(p_id)
                is_pivot = len(chains_used) >= 2
                parts_rows.append({
                    "ID Pièce": p.id,
                    "Désignation": p.name,
                    "Nominal (mm)": p.nominal,
                    "ES (mm)": p.es,
                    "EI (mm)": p.ei,
                    "IT (mm)": p.IT,
                    "Matériau": p.material,
                    "Impact": f"🔥 Pivot ({len(chains_used)})" if is_pivot else (f"{len(chains_used)} chaîne" if chains_used else "Non liée"),
                })

            if parts_rows:
                df_parts = pd.DataFrame(parts_rows)
                st.dataframe(
                    df_parts,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Nominal (mm)": st.column_config.NumberColumn(format="%.3f"),
                        "ES (mm)": st.column_config.NumberColumn(format="%+.4f"),
                        "EI (mm)": st.column_config.NumberColumn(format="%+.4f"),
                        "IT (mm)": st.column_config.ProgressColumn(
                            format="%.4f mm",
                            min_value=0.0,
                            max_value=max(0.1, df_parts["IT (mm)"].max() if not df_parts.empty else 0.1),
                        ),
                        "Impact": st.column_config.TextColumn(help="Chaînes d'assemblage utilisant cette cote"),
                    },
                )
            else:
                st.info("Le catalogue de pièces est vide. Définissez votre première pièce maîtresse dans le formulaire ci-contre.")

            # 2. Fast Propagation Simulator with real-time feedback
            st.markdown("---")
            with st.container(border=True):
                st.markdown("#### ⚡ Simulateur de Propagation Directe")
                st.caption("Ajustez instantanément la tolérance d'une pièce pour observer le recalcul automatique sur toutes ses chaînes.")

                shared_p_options = list(project.parts.keys())
                if shared_p_options:
                    col_p1, col_p2 = st.columns([1.8, 1.2])
                    with col_p1:
                        selected_sim_p = st.selectbox(
                            "Pièce maîtresse à tester :",
                            options=shared_p_options,
                            format_func=lambda x: f"{project.parts[x].name} [{x}] (utilisée dans {len(project.get_part_impact(x))} chaîne(s))",
                            key="sim_p_sel",
                        )
                    sim_part = project.parts[selected_sim_p]
                    impacted_chains = project.get_part_impact(selected_sim_p)

                    with col_p2:
                        st.caption(f"**Chaînes affectées ({len(impacted_chains)}) :**")
                        if impacted_chains:
                            st.write(", ".join([f"`{c}`" for c in impacted_chains]))
                        else:
                            st.write("Aucune chaîne liée.")

                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        new_es = st.number_input("Nouveau ES (mm)", value=sim_part.es, step=0.005, format="%.4f", key="sim_new_es")
                    with col_s2:
                        new_ei = st.number_input("Nouveau EI (mm)", value=sim_part.ei, step=0.005, format="%.4f", key="sim_new_ei")
                    with col_s3:
                        st.write("")
                        st.write("")
                        if st.button("🚀 Appliquer & Propager", type="primary", use_container_width=True, key="btn_apply_propagate"):
                            if new_es < new_ei:
                                st.error("Incohérence : ES doit être supérieur ou égal à EI.")
                            else:
                                sim_part.es = new_es
                                sim_part.ei = new_ei
                                st.toast(f"Propagation réussie sur {len(impacted_chains)} chaîne(s) !")
                                st.rerun()

        with col_cat_right:
            # 3. Add / Edit Part Form in clear card
            with st.container(border=True):
                st.markdown("#### ✏️ Gestion des Pièces Maîtresses")

                part_action = st.radio(
                    "Action",
                    options=["➕ Créer une nouvelle pièce", "📝 Modifier une pièce existante"],
                    horizontal=True,
                    label_visibility="collapsed",
                )

                target_part = None
                if part_action.startswith("📝") and project.parts:
                    edit_id = st.selectbox(
                        "Sélectionner la pièce à éditer :",
                        options=list(project.parts.keys()),
                        format_func=lambda x: f"{project.parts[x].name} [{x}]",
                        key="edit_p_sel",
                    )
                    target_part = project.parts[edit_id]

                p_id_input = st.text_input(
                    "Identifiant unique (ID Code)",
                    value=target_part.id if target_part else "PIGNON",
                    disabled=(part_action.startswith("📝")),
                    help="Code d'identification en majuscules (ex: CARTER, ARBRE, ROULEMENT)",
                )
                p_name_input = st.text_input(
                    "Désignation de la pièce",
                    value=target_part.name if target_part else "Pignon d'entraînement",
                )
                p_nom_input = st.number_input(
                    "Cote nominale (mm)",
                    min_value=0.0,
                    value=target_part.nominal if target_part else 45.0,
                    step=1.0,
                    format="%.3f",
                )

                # Standard ISO helper
                use_iso = st.toggle("Associer un ajustement ISO 286", value=False, key="part_toggle_iso")
                if use_iso:
                    all_syms = get_available_iso286_symbols()
                    merged_syms = [f"Alésage {h}" for h in all_syms["holes"]] + [f"Arbre {s}" for s in all_syms["shafts"]]
                    iso_choice = st.selectbox("Symbole ISO 286", options=merged_syms, index=1, key="part_iso_select")
                    sym_clean = iso_choice.split()[-1]
                    calc_ei, calc_es = get_iso286_limits(max(0.1, p_nom_input), sym_clean)
                    p_es_val = calc_es
                    p_ei_val = calc_ei
                    st.caption(f"Écarts ISO calculés pour {sym_clean} : **EI = {p_ei_val:+.4f} mm**, **ES = {p_es_val:+.4f} mm**")
                else:
                    col_tol1, col_tol2 = st.columns(2)
                    with col_tol1:
                        p_es_val = st.number_input(
                            "Écart Supérieur ES (mm)",
                            value=target_part.es if target_part else 0.025,
                            step=0.005,
                            format="%.4f",
                        )
                    with col_tol2:
                        p_ei_val = st.number_input(
                            "Écart Inférieur EI (mm)",
                            value=target_part.ei if target_part else -0.025,
                            step=0.005,
                            format="%.4f",
                        )

                mat_idx = materials.index(target_part.material) if (target_part and target_part.material in materials) else 0
                p_mat_val = st.selectbox("Matériau (Dilatation thermique)", options=materials, index=mat_idx)
                p_desc_val = st.text_input("Notes / Description", value=target_part.description if target_part else "")

                col_save_btn, col_del_btn = st.columns([1.5, 1])
                with col_save_btn:
                    save_label = "💾 Sauvegarder la pièce" if part_action.startswith("📝") else "➕ Enregistrer au catalogue"
                    if st.button(save_label, type="primary", use_container_width=True, key="btn_save_catalog_part"):
                        try:
                            new_part = CatalogPart(
                                id=p_id_input.strip().upper(),
                                name=p_name_input.strip(),
                                nominal=p_nom_input,
                                es=p_es_val,
                                ei=p_ei_val,
                                material=p_mat_val,
                                description=p_desc_val,
                            )
                            project.add_part(new_part)
                            st.toast(f"Pièce '{new_part.name}' enregistrée avec succès !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")

                with col_del_btn:
                    if part_action.startswith("📝") and target_part:
                        if st.button("🗑️ Supprimer", use_container_width=True, key="btn_delete_catalog_part"):
                            impacted = project.remove_part(target_part.id)
                            msg = f"Pièce '{target_part.name}' retirée du catalogue."
                            if impacted:
                                msg += f" Liens retirés dans {len(impacted)} chaîne(s)."
                            st.warning(msg)
                            st.rerun()

    # =========================================================================
    # ONGLET 2 : CHAÎNES D'ASSEMBLAGE & SCHÉMA 1D
    # =========================================================================
    with tab_chains:
        chain_keys = list(project.chains.keys())

        if not chain_keys:
            st.info("Aucune chaîne d'assemblage n'est définie dans le projet.")
            with st.container(border=True):
                st.markdown("#### ➕ Créer votre première chaîne d'assemblage")
                c_id_init = st.text_input("Identifiant unique (ex: CH_JEU_AXIAL)", value="CH_JEU_AXIAL")
                c_name_init = st.text_input("Nom fonctionnel de la chaîne", value="Jeu axial principal")
                c_desc_init = st.text_input("Description", value="Garantit le jeu axial d'assemblage")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    c_tmin_init = st.number_input("Cible Minimale J_min (mm)", value=0.100, step=0.050, format="%.3f")
                with col_t2:
                    c_tmax_init = st.number_input("Cible Maximale J_max (mm)", value=0.800, step=0.050, format="%.3f")
                if st.button("Créer la chaîne", type="primary", key="btn_init_first_chain"):
                    try:
                        new_c = AssemblyChain(
                            id=c_id_init.strip().upper(),
                            name=c_name_init.strip(),
                            description=c_desc_init.strip(),
                            target_min=c_tmin_init,
                            target_max=c_tmax_init,
                        )
                        project.add_chain(new_c)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
        else:
            # 1. Chain Selector via Modern st.pills with status badges
            pill_options = []
            pill_labels = {}
            for cid in chain_keys:
                c = project.chains[cid]
                status_icon = "⚪"
                if c.links:
                    try:
                        r = project.evaluate_chain(cid)
                        c_min = r.worst_case_minus
                        c_max = r.worst_case_plus
                        ok = True
                        if c.target_min is not None and c_min < c.target_min:
                            ok = False
                        if c.target_max is not None and c_max > c.target_max:
                            ok = False
                        status_icon = "🟢" if ok else "🔴"
                    except Exception:
                        status_icon = "⚠️"
                pill_options.append(cid)
                pill_labels[cid] = f"{status_icon} {c.name} ({len(c.links)} m.)"

            col_pills, col_new_c = st.columns([3.5, 1.2])
            with col_pills:
                active_chain_id = st.pills(
                    "Sélectionner la chaîne d'assemblage active :",
                    options=pill_options,
                    format_func=lambda x: pill_labels[x],
                    default=pill_options[0],
                    key="pills_active_chain",
                )
            with col_new_c:
                st.write("")
                with st.popover("➕ Nouvelle Chaîne", use_container_width=True):
                    st.markdown("##### Créer une nouvelle chaîne")
                    add_c_id = st.text_input("ID Chaîne", value=f"CH_{len(chain_keys)+1}")
                    add_c_name = st.text_input("Désignation", value=f"Nouvelle chaîne {len(chain_keys)+1}")
                    col_nc1, col_nc2 = st.columns(2)
                    with col_nc1:
                        add_c_tmin = st.number_input("Cible Min (mm)", value=0.100, step=0.05, format="%.3f", key="add_c_tmin")
                    with col_nc2:
                        add_c_tmax = st.number_input("Cible Max (mm)", value=0.900, step=0.05, format="%.3f", key="add_c_tmax")
                    if st.button("Créer cette chaîne", type="primary", use_container_width=True, key="btn_confirm_add_c"):
                        try:
                            created_c = AssemblyChain(
                                id=add_c_id.strip().upper(),
                                name=add_c_name.strip(),
                                target_min=add_c_tmin,
                                target_max=add_c_tmax,
                            )
                            project.add_chain(created_c)
                            st.toast(f"Chaîne '{created_c.name}' créée !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")

            if not active_chain_id:
                active_chain_id = pill_options[0]

            active_chain = project.get_chain(active_chain_id)

            # Chain Meta bar with Edit Popover
            with st.container(border=True):
                col_cm1, col_cm2, col_cm3 = st.columns([2.5, 1.5, 0.8])
                with col_cm1:
                    st.markdown(f"#### 🔗 {active_chain.name} `[{active_chain.id}]`")
                    st.caption(active_chain.description or "Aucune description renseignée.")
                with col_cm2:
                    t_min_disp = f"{active_chain.target_min:.3f} mm" if active_chain.target_min is not None else "Non spécifié"
                    t_max_disp = f"{active_chain.target_max:.3f} mm" if active_chain.target_max is not None else "Non spécifié"
                    st.markdown(f"**Cibles requises :** `J_min = {t_min_disp}` | `J_max = {t_max_disp}`")
                with col_cm3:
                    with st.popover("⚙️ Paramètres", use_container_width=True):
                        st.markdown("##### ⚙️ Modifier les limites cibles")
                        ed_c_name = st.text_input("Nom de la chaîne", value=active_chain.name, key="pop_c_name")
                        ed_c_desc = st.text_input("Description", value=active_chain.description, key="pop_c_desc")
                        col_ed_t1, col_ed_t2 = st.columns(2)
                        with col_ed_t1:
                            ed_c_tmin = st.number_input("Cible Min (mm)", value=active_chain.target_min if active_chain.target_min is not None else 0.0, step=0.05, format="%.3f", key="pop_c_tmin")
                        with col_ed_t2:
                            ed_c_tmax = st.number_input("Cible Max (mm)", value=active_chain.target_max if active_chain.target_max is not None else 1.0, step=0.05, format="%.3f", key="pop_c_tmax")
                        if st.button("💾 Enregistrer les limites", type="primary", use_container_width=True, key="btn_save_c_limits"):
                            project.update_chain(
                                active_chain.id,
                                name=ed_c_name,
                                description=ed_c_desc,
                                target_min=ed_c_tmin,
                                target_max=ed_c_tmax,
                            )
                            st.toast("Limites mises à jour !")
                            st.rerun()

                        st.divider()
                        st.caption("Zone de suppression :")
                        if st.button("🗑️ Supprimer cette chaîne", use_container_width=True, key="pop_btn_del_chain"):
                            project.remove_chain(active_chain.id)
                            st.warning(f"Chaîne '{active_chain.id}' supprimée.")
                            st.rerun()

            # 2. Side-by-Side: Links Composition on Left, 1D Vector Stack Diagram on Right
            col_links, col_chart = st.columns([1.5, 1.5])

            with col_links:
                st.markdown("##### 📑 Composition Vectorielle des Maillons")

                if active_chain.links:
                    # Table of links with modern card rows
                    for idx, link in enumerate(active_chain.links):
                        if link.part_id:
                            p = project.parts.get(link.part_id)
                            nom = (p.nominal * link.scale_factor) if p else 0.0
                            es = (p.es * link.scale_factor) if p else 0.0
                            ei = (p.ei * link.scale_factor) if p else 0.0
                            source_badge = f"<span style='color:#0369a1; background:#e0f2fe; padding:2px 6px; border-radius:4px; font-size:0.8rem;'>📦 [{link.part_id}]</span>"
                            rep_name = link.custom_name or (p.name if p else f"Maillon {idx+1}")
                        else:
                            nom = (link.local_nominal or 0.0) * link.scale_factor
                            es = (link.local_es or 0.0) * link.scale_factor
                            ei = (link.local_ei or 0.0) * link.scale_factor
                            source_badge = "<span style='color:#475569; background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:0.8rem;'>⚪ Locale</span>"
                            rep_name = link.custom_name or f"Cote locale {idx+1}"

                        orient_badge = "<span class='vector-badge-pos'>+1</span>" if link.orientation > 0 else "<span class='vector-badge-neg'>-1</span>"

                        with st.container(border=True):
                            c_r1, c_r2, c_r3, c_r4 = st.columns([2.2, 1.2, 1.6, 0.6])
                            with c_r1:
                                st.markdown(f"**#{idx+1} {rep_name}**")
                                st.markdown(f"{orient_badge} &nbsp; {source_badge}", unsafe_allow_html=True)
                            with c_r2:
                                st.caption("Nominal")
                                st.markdown(f"**{nom:.3f}** mm")
                            with c_r3:
                                st.caption("Tolérances [EI ; ES]")
                                st.markdown(f"`[{ei:+.3f} ; {es:+.3f}]`")
                                st.caption(f"IT: {es-ei:.3f} mm")
                            with c_r4:
                                st.write("")
                                if st.button("🗑️", key=f"del_link_{active_chain.id}_{idx}", help=f"Retirer le maillon #{idx+1}"):
                                    project.remove_link_from_chain(active_chain.id, idx)
                                    st.rerun()
                else:
                    st.info("Cette chaîne ne contient aucun maillon pour l'instant.")

                # Add link expander
                with st.expander("➕ Ajouter un maillon à cette chaîne", expanded=not bool(active_chain.links)):
                    kind = st.radio("Origine de la cote", options=["📦 Pièce du Catalogue", "✏️ Cote Locale Spécifique"], horizontal=True, key="rad_kind_link")
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        orient_label = st.selectbox(
                            "Orientation vectorielle",
                            options=["+ (Augmente le jeu)", "- (Diminue le jeu)"],
                            key="sel_orient_link",
                        )
                        orient_val = 1 if orient_label.startswith("+") else -1

                    if kind.startswith("📦"):
                        cat_keys = list(project.parts.keys())
                        with col_a2:
                            if cat_keys:
                                sel_part_for_link = st.selectbox(
                                    "Choisir la pièce maîtresse",
                                    options=cat_keys,
                                    format_func=lambda x: f"{project.parts[x].name} [{x}]",
                                    key="sel_p_for_link",
                                )
                            else:
                                st.warning("Aucune pièce au catalogue.")
                                sel_part_for_link = None
                        custom_alias = st.text_input("Désignation contextuelle (optionnel, ex: Roulement droit)", key="alias_cat_link")

                        if sel_part_for_link and st.button("➕ Ajouter ce maillon catalogue", type="primary", use_container_width=True, key="btn_add_link_cat"):
                            project.add_link_to_chain(
                                active_chain.id,
                                part_id=sel_part_for_link,
                                orientation=orient_val,  # type: ignore
                                custom_name=custom_alias,
                            )
                            st.toast("Maillon lié au catalogue ajouté !")
                            st.rerun()
                    else:
                        with col_a2:
                            loc_name = st.text_input("Nom de la cote locale", value="Gorge ou jeu d'usinage", key="loc_name_link")
                        col_l1, col_l2, col_l3 = st.columns(3)
                        with col_l1:
                            loc_nom = st.number_input("Nominal (mm)", min_value=0.0, value=5.0, step=1.0, key="loc_nom_link")
                        with col_l2:
                            loc_es = st.number_input("ES (mm)", value=0.03, step=0.005, format="%.4f", key="loc_es_link")
                        with col_l3:
                            loc_ei = st.number_input("EI (mm)", value=-0.03, step=0.005, format="%.4f", key="loc_ei_link")

                        if st.button("➕ Ajouter la cote locale", type="primary", use_container_width=True, key="btn_add_link_loc"):
                            project.add_link_to_chain(
                                active_chain.id,
                                orientation=orient_val,  # type: ignore
                                custom_name=loc_name,
                                local_nominal=loc_nom,
                                local_es=loc_es,
                                local_ei=loc_ei,
                            )
                            st.toast("Cote locale autonome ajoutée !")
                            st.rerun()

            with col_chart:
                # Interactive 1D Vector Stack Diagram
                st.plotly_chart(
                    render_1d_stack_diagram(active_chain, project),
                    use_container_width=True,
                )

            # 3. Calculation Results: Worst-Case (Pire des Cas) Only
            if active_chain.links:
                try:
                    res = project.evaluate_chain(active_chain.id)
                    st.divider()

                    st.markdown("#### 📐 Bilan Arithmétique au Pire des Cas (Worst-Case)")

                    # 4 Metric Cards
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("Jeu Nominal ($J_{\\text{nom}}$)", f"{res.nominal:.4f} mm")
                    with m2:
                        st.metric("Jeu Minimal ($J_{\\min,\\text{WC}}$)", f"{res.worst_case_minus:.4f} mm")
                    with m3:
                        st.metric("Jeu Maximal ($J_{\\max,\\text{WC}}$)", f"{res.worst_case_plus:.4f} mm")
                    with m4:
                        wc_it = res.worst_case_plus - res.worst_case_minus
                        st.metric("Dispersion Totale ($IT_{\\text{WC}}$)", f"{wc_it:.4f} mm")

                    # Functional Margins & Verdict
                    has_targets = active_chain.target_min is not None or active_chain.target_max is not None
                    if has_targets:
                        col_marg1, col_marg2 = st.columns(2)
                        wc_is_ok = True

                        with col_marg1:
                            if active_chain.target_min is not None:
                                margin_min = res.worst_case_minus - active_chain.target_min
                                st.metric(
                                    f"Marge minimale (vs {active_chain.target_min:.3f} mm)",
                                    f"{margin_min:+.4f} mm",
                                    delta=f"{margin_min:+.4f} mm",
                                    delta_color="normal" if margin_min >= 0 else "inverse",
                                )
                                if margin_min < 0:
                                    wc_is_ok = False
                            else:
                                st.info("Aucune limite minimale spécifiée.")

                        with col_marg2:
                            if active_chain.target_max is not None:
                                margin_max = active_chain.target_max - res.worst_case_plus
                                st.metric(
                                    f"Marge maximale (vs {active_chain.target_max:.3f} mm)",
                                    f"{margin_max:+.4f} mm",
                                    delta=f"{margin_max:+.4f} mm",
                                    delta_color="normal" if margin_max >= 0 else "inverse",
                                )
                                if margin_max < 0:
                                    wc_is_ok = False
                            else:
                                st.info("Aucune limite maximale spécifiée.")

                        if wc_is_ok:
                            st.success(
                                f"✅ **100% CONFORME AU PIRE DES CAS** : Le jeu calculé "
                                f"`[{res.worst_case_minus:.4f} ; {res.worst_case_plus:.4f}] mm` est strictement "
                                f"dans les limites admissibles `[{active_chain.target_min} ; {active_chain.target_max}] mm`."
                            )
                        else:
                            st.error(
                                f"❌ **NON CONFORME AU PIRE DES CAS** : Risque d'interférence ou de jeu excessif. "
                                f"Ajustez les tolérances du catalogue ou de la chaîne pour retrouver la conformité."
                            )

                    # Range chart
                    st.plotly_chart(
                        render_wc_range_chart(res, active_chain.target_min, active_chain.target_max, active_chain.name),
                        use_container_width=True,
                    )

                except Exception as err:
                    st.error(f"Erreur de calcul pour la chaîne active : {err}")

    # =========================================================================
    # ONGLET 3 : TABLEAU DE BORD SYSTÈME & MATRICE DES IMPACTS
    # =========================================================================
    with tab_dashboard:
        st.markdown("### 📊 Tableau de Bord Global & Matrice des Impacts Croisés")
        st.caption("Vue d'ensemble de la santé dimensionnelle du système complet au Pire des Cas (Worst-Case).")

        # 3 Global Metrics
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("Total des chaînes", f"{summary.total_chains}")
        with kpi2:
            st.metric("Chaînes conformes WC", f"{summary.wc_compliant_count} / {summary.total_chains}")
        with kpi3:
            wc_nok = summary.total_chains - summary.wc_compliant_count
            st.metric("Chaînes critiques non conformes", f"{wc_nok}", delta=None if wc_nok == 0 else f"-{wc_nok}")

        st.divider()

        # Cross-Impact Heatmap (Pièces x Chaînes)
        st.plotly_chart(
            render_impact_heatmap(project, summary),
            use_container_width=True,
        )

        if summary.critical_pivot_parts:
            st.info(
                f"💡 **Pièces Pivots Détectées** : Les pièces `{'`, `'.join(summary.critical_pivot_parts)}` "
                f"interviennent simultanément dans plusieurs chaînes d'assemblage. "
                f"Tout arbitrage sur leurs tolérances d'usinage doit être validé sur l'ensemble du système mécanique."
            )

        st.divider()

        # Synthesis Table
        st.markdown("#### 📋 Synthèse Dimensionnelle Complète de l'Assemblage (Pire des Cas)")
        sys_rows = []
        for s in summary.chains_status:
            c = project.get_chain(s.chain_id)
            c_parts = [l.part_id for l in c.links if l.part_id]
            sys_rows.append({
                "Chaîne": s.name,
                "ID": s.chain_id,
                "Jeu Nominal": f"{s.result.nominal:.3f} mm",
                "Pire des Cas [Min ; Max]": f"[{s.result.worst_case_minus:.3f} ; {s.result.worst_case_plus:.3f}] mm",
                "Dispersion IT_WC": f"{s.result.worst_case_plus - s.result.worst_case_minus:.3f} mm",
                "Limites Cibles": f"[{c.target_min} ; {c.target_max}]" if (c.target_min is not None or c.target_max is not None) else "Sans cible",
                "Verdict": "🟢 Conforme" if s.wc_is_compliant else "🔴 Critique",
                "Pièces du Catalogue": ", ".join(set(c_parts)) if c_parts else "Cotes locales",
            })

        if sys_rows:
            st.dataframe(pd.DataFrame(sys_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune chaîne définie dans le projet.")


if __name__ == "__main__":
    main()
