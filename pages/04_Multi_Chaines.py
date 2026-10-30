"""CotaStack - Répertoire Unifié Multi-Chaînes (Jalon 3.1).

Gestion centralisée des pièces maîtresses & Calculs arithmétiques au Pire des Cas (Worst-Case).
"""

import streamlit as st
import pandas as pd
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

# Masquage complet de la barre latérale et de son bouton chevron
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


def render_wc_range_chart(res, target_min: float | None, target_max: float | None, chain_name: str):
    """Plot horizontal visual range of calculated Worst-Case game vs functional targets."""
    fig = go.Figure()

    wc_min = res.worst_case_minus
    wc_max = res.worst_case_plus
    j_nom = res.nominal

    # Calculated WC bar
    fig.add_trace(go.Bar(
        name="Plage Pire des Cas (WC)",
        y=["Jeu fonctionnel"],
        x=[wc_max - wc_min],
        base=[wc_min],
        orientation="h",
        marker=dict(color="#0284c7"),
        hovertemplate=f"<b>Jeu au Pire des Cas</b><br>J_min: {wc_min:.4f} mm<br>J_max: {wc_max:.4f} mm<br>IT: {wc_max - wc_min:.4f} mm<extra></extra>",
    ))

    # Nominal marker
    fig.add_trace(go.Scatter(
        name="Jeu nominal",
        x=[j_nom],
        y=["Jeu fonctionnel"],
        mode="markers",
        marker=dict(color="#0f172a", size=14, symbol="line-ns", line=dict(width=3, color="#0f172a")),
        hovertemplate=f"Jeu nominal: {j_nom:.4f} mm<extra></extra>",
    ))

    # Target lines
    if target_min is not None:
        fig.add_vline(
            x=target_min,
            line_dash="dash",
            line_color="#10b981" if wc_min >= target_min else "#ef4444",
            annotation_text=f"Cible Min ({target_min:.3f})",
            annotation_position="top left",
        )
    if target_max is not None:
        fig.add_vline(
            x=target_max,
            line_dash="dash",
            line_color="#10b981" if wc_max <= target_max else "#ef4444",
            annotation_text=f"Cible Max ({target_max:.3f})",
            annotation_position="top right",
        )

    fig.update_layout(
        title=f"Positionnement arithmétique Pire des Cas (WC) — {chain_name}",
        xaxis_title="Jeu (mm)",
        height=220,
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor="#f8fafc",
        showlegend=False,
    )
    return fig


def main() -> None:
    # Session State Project Initialization
    if "multi_project" not in st.session_state:
        st.session_state.multi_project = init_default_project()

    project: MultiChainProject = st.session_state.multi_project
    materials = get_available_materials()

    # Top Header & Quick Reset Actions
    col_top1, col_top2, col_top3 = st.columns([2.5, 1, 1])
    with col_top1:
        st.title("🏢 Répertoire Unifié Multi-Chaînes")
        st.caption(f"Système mécanique actif : **{project.name}** | {len(project.parts)} pièces maîtresses | {len(project.chains)} chaînes")
    with col_top2:
        if st.button("🗑️ Repartir à zéro", use_container_width=True, help="Efface tout pour concevoir votre mécanisme à blanc (0 pièce, 0 chaîne)"):
            project.clear_all()
            project.name = "Nouveau Système Mécanique"
            project.description = "Projet vierge"
            st.toast("Projet réinitialisé à vide !")
            st.rerun()
    with col_top3:
        if st.button("🔄 Démo (Boîte de vitesses)", use_container_width=True, help="Recharge l'exemple de démonstration complet"):
            st.session_state.multi_project = init_default_project()
            st.toast("Exemple de démonstration rechargé !")
            st.rerun()

    tab_catalog, tab_chains, tab_dashboard = st.tabs([
        "📦 Répertoire & Pièces Partagées",
        "🔗 Chaînes d'Assemblage du Système",
        "📊 Tableau de Bord Système",
    ])

    # =========================================================================
    # ONGLET 1: CATALOGUE DES PIÈCES MAÎTRESSES
    # =========================================================================
    with tab_catalog:
        st.subheader("📦 Catalogue des Pièces Maîtresses (Single Source of Truth)")
        st.markdown(
            "Définissez chaque composant physique **une seule fois**. "
            "Toute modification d'une tolérance est immédiatement **propagée et recalculée** "
            "sur toutes les chaînes d'assemblage qui l'utilisent."
        )

        col_cat_table, col_cat_form = st.columns([1.6, 1.2])

        with col_cat_table:
            parts_rows = []
            for p_id, p in project.parts.items():
                chains_used = project.get_part_impact(p_id)
                parts_rows.append({
                    "ID Pièce": p.id,
                    "Nom de la pièce": p.name,
                    "Nominal (mm)": f"{p.nominal:.3f}",
                    "ES (mm)": f"{p.es:+.4f}",
                    "EI (mm)": f"{p.ei:+.4f}",
                    "IT (mm)": f"{p.IT:.4f}",
                    "Matériau": p.material,
                    "Impact": f"{len(chains_used)} chaîne(s) ({', '.join(chains_used)})" if chains_used else "Aucune",
                })

            if parts_rows:
                df_parts = pd.DataFrame(parts_rows)
                st.dataframe(df_parts, use_container_width=True, hide_index=True)
            else:
                st.info("Le catalogue de pièces est actuellement vide. Ajoutez votre première pièce ci-contre.")

            st.divider()
            # Fast Propagation Simulator for demonstration
            st.markdown("#### ⚡ Propagation directe d'une tolérance")
            shared_p_options = list(project.parts.keys())
            if shared_p_options:
                selected_sim_p = st.selectbox(
                    "Choisir une pièce pour ajuster sa tolérance et voir l'impact immédiat :",
                    options=shared_p_options,
                    format_func=lambda x: f"{project.parts[x].name} [{x}] (utilisée dans {len(project.get_part_impact(x))} chaîne(s))",
                    key="sim_part_select",
                )
                sim_part = project.parts[selected_sim_p]
                impacted = project.get_part_impact(selected_sim_p)

                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    new_es = st.number_input("Nouveau ES (mm)", value=sim_part.es, step=0.005, format="%.4f", key="sim_es")
                with col_s2:
                    new_ei = st.number_input("Nouveau EI (mm)", value=sim_part.ei, step=0.005, format="%.4f", key="sim_ei")
                with col_s3:
                    st.write("")
                    st.write("")
                    if st.button("🚀 Propager la tolérance", type="primary", use_container_width=True, key="btn_propagate"):
                        sim_part.es = new_es
                        sim_part.ei = new_ei
                        st.success(f"Tolérances de '{sim_part.name}' mises à jour. Propagation effectuée sur : {', '.join(impacted) or 'aucune'} !")
                        st.rerun()

                if impacted:
                    st.caption(f"📢 **Impact direct** : La modification affectera simultanément : `{'`, `'.join(impacted)}`.")
                else:
                    st.caption("Cette pièce n'est actuellement liée à aucune chaîne.")

        with col_cat_form:
            st.markdown("#### ✏️ Ajouter ou Modifier une Pièce")
            part_mode = st.radio("Mode d'action", options=["Créer une nouvelle pièce", "Modifier une pièce existante"], horizontal=True)

            target_part = None
            if part_mode == "Modifier une pièce existante" and project.parts:
                edit_id = st.selectbox("Sélectionner la pièce à éditer", options=list(project.parts.keys()), key="edit_part_sel")
                target_part = project.parts[edit_id]

            p_id = st.text_input(
                "Identifiant unique (ID)",
                value=target_part.id if target_part else "PIGNON",
                disabled=(part_mode == "Modifier une pièce existante"),
                key="input_part_id",
            )
            p_name = st.text_input("Désignation de la pièce", value=target_part.name if target_part else "Pignon d'entraînement", key="input_part_name")
            p_nom = st.number_input("Cote nominale (mm)", min_value=0.0, value=target_part.nominal if target_part else 45.0, step=1.0, format="%.3f", key="input_part_nom")

            # ISO 286 helper
            use_iso = st.checkbox("Utiliser un ajustement ISO 286 pour définir les écarts", value=False, key="part_use_iso")
            if use_iso:
                all_symbols = get_available_iso286_symbols()
                merged_syms = [f"Alésage {h}" for h in all_symbols["holes"]] + [f"Arbre {s}" for s in all_symbols["shafts"]]
                iso_sel = st.selectbox("Symbole ISO 286", options=merged_syms, index=1, key="part_iso_sym")
                sym_clean = iso_sel.split()[-1]
                calc_ei, calc_es = get_iso286_limits(max(0.1, p_nom), sym_clean)
                p_es = calc_es
                p_ei = calc_ei
                st.caption(f"Écarts ISO calculés : ES = {p_es:+.4f} mm, EI = {p_ei:+.4f} mm")
            else:
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    p_es = st.number_input("Écart Supérieur ES (mm)", value=target_part.es if target_part else 0.025, step=0.005, format="%.4f", key="input_part_es")
                with col_e2:
                    p_ei = st.number_input("Écart Inférieur EI (mm)", value=target_part.ei if target_part else -0.025, step=0.005, format="%.4f", key="input_part_ei")

            mat_idx = materials.index(target_part.material) if (target_part and target_part.material in materials) else 0
            p_mat = st.selectbox("Matériau", options=materials, index=mat_idx, key="input_part_mat")
            p_desc = st.text_area("Description / Notes", value=target_part.description if target_part else "", key="input_part_desc")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                btn_label = "💾 Enregistrer" if part_mode == "Modifier une pièce existante" else "➕ Ajouter la pièce"
                if st.button(btn_label, type="primary", use_container_width=True, key="btn_save_part"):
                    try:
                        new_p = CatalogPart(
                            id=p_id.strip().upper(),
                            name=p_name.strip(),
                            nominal=p_nom,
                            es=p_es,
                            ei=p_ei,
                            material=p_mat,
                            description=p_desc,
                        )
                        project.add_part(new_p)
                        st.success(f"Pièce '{new_p.name}' enregistrée avec succès !")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Erreur : {err}")

            with col_btn2:
                if part_mode == "Modifier une pièce existante" and target_part:
                    if st.button("🗑️ Supprimer la pièce", use_container_width=True, key="btn_del_part"):
                        impacted = project.remove_part(target_part.id)
                        msg = f"Pièce '{target_part.name}' supprimée."
                        if impacted:
                            msg += f" Attention : elle était référencée dans {len(impacted)} chaîne(s) ({', '.join(impacted)})."
                        st.warning(msg)
                        st.rerun()

    # =========================================================================
    # ONGLET 2: CHAÎNES D'ASSEMBLAGE DU SYSTÈME
    # =========================================================================
    with tab_chains:
        st.subheader("🔗 Chaînes d'Assemblage du Système Mécanique")

        chain_keys = list(project.chains.keys())

        # If no chains in project, show quick creation box
        if not chain_keys:
            st.info("Aucune chaîne d'assemblage n'est définie dans le projet. Créez votre première chaîne ci-dessous.")
            with st.form("form_create_first_chain"):
                c_id_new = st.text_input("Identifiant unique (ex: CH_JEU_AXIAL)", value="CH_JEU_AXIAL")
                c_name_new = st.text_input("Nom de la chaîne", value="Jeu axial principal")
                c_desc_new = st.text_input("Description fonctionnelle", value="Jeu de fonctionnement axial")
                col_tm1, col_tm2 = st.columns(2)
                with col_tm1:
                    c_tmin_new = st.number_input("Cible Minimale J_min (mm)", value=0.100, step=0.050, format="%.3f")
                with col_tm2:
                    c_tmax_new = st.number_input("Cible Maximale J_max (mm)", value=0.800, step=0.050, format="%.3f")
                if st.form_submit_button("➕ Créer la chaîne", type="primary"):
                    try:
                        c_obj = AssemblyChain(
                            id=c_id_new.strip().upper(),
                            name=c_name_new.strip(),
                            description=c_desc_new.strip(),
                            target_min=c_tmin_new,
                            target_max=c_tmax_new,
                        )
                        project.add_chain(c_obj)
                        st.success(f"Chaîne '{c_obj.name}' créée avec succès !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
            return

        # Top Bar: Select chain or Create new
        col_c_sel, col_c_action = st.columns([2, 1])
        with col_c_sel:
            active_chain_id = st.selectbox(
                "Sélectionner la chaîne d'assemblage à afficher :",
                options=chain_keys,
                format_func=lambda x: f"{project.chains[x].name} ({len(project.chains[x].links)} maillons)",
                key="active_chain_select",
            )
        with col_c_action:
            st.write("")
            with st.expander("➕ Créer une autre chaîne", expanded=False):
                new_c_id = st.text_input("ID Chaîne", key="new_c_id")
                new_c_name = st.text_input("Nom de la chaîne", key="new_c_name")
                col_tmin, col_tmax = st.columns(2)
                with col_tmin:
                    new_tmin = st.number_input("Cible Min (mm)", value=0.100, step=0.050, format="%.3f", key="new_tmin")
                with col_tmax:
                    new_tmax = st.number_input("Cible Max (mm)", value=0.800, step=0.050, format="%.3f", key="new_tmax")
                if st.button("Créer la chaîne", type="primary", use_container_width=True, key="btn_create_chain"):
                    try:
                        new_chain = AssemblyChain(
                            id=new_c_id.strip().upper(),
                            name=new_c_name.strip(),
                            target_min=new_tmin,
                            target_max=new_tmax,
                        )
                        project.add_chain(new_chain)
                        st.success(f"Chaîne '{new_chain.name}' créée avec succès !")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Erreur : {err}")

        active_chain = project.get_chain(active_chain_id)

        # Settings of Active Chain: Edit Limits, Name, Targets, or Delete Chain
        with st.expander("⚙️ Modifier les limites cibles ou supprimer cette chaîne", expanded=False):
            col_ed1, col_ed2 = st.columns([2, 1])
            with col_ed1:
                edit_chain_name = st.text_input("Nom de la chaîne", value=active_chain.name, key="edit_c_name")
                edit_chain_desc = st.text_input("Description", value=active_chain.description, key="edit_c_desc")
                col_ed_t1, col_ed_t2 = st.columns(2)
                with col_ed_t1:
                    edit_chain_tmin = st.number_input(
                        "Cible minimale J_min (mm)",
                        value=active_chain.target_min if active_chain.target_min is not None else 0.0,
                        step=0.050,
                        format="%.3f",
                        key="edit_c_tmin",
                    )
                with col_ed_t2:
                    edit_chain_tmax = st.number_input(
                        "Cible maximale J_max (mm)",
                        value=active_chain.target_max if active_chain.target_max is not None else 1.0,
                        step=0.050,
                        format="%.3f",
                        key="edit_c_tmax",
                    )
                if st.button("💾 Mettre à jour les limites et le nom", type="primary", key="btn_update_chain_limits"):
                    try:
                        project.update_chain(
                            active_chain.id,
                            name=edit_chain_name,
                            description=edit_chain_desc,
                            target_min=edit_chain_tmin,
                            target_max=edit_chain_tmax,
                        )
                        st.success("Limites de la chaîne mises à jour avec succès !")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Erreur : {err}")

            with col_ed2:
                st.markdown("#### Zone dangereuse")
                st.caption("Supprime définitivement cette chaîne d'assemblage du projet.")
                if st.button("🗑️ Supprimer cette chaîne", type="secondary", use_container_width=True, key="btn_delete_chain"):
                    project.remove_chain(active_chain.id)
                    st.warning("Chaîne d'assemblage supprimée.")
                    st.rerun()

        # Display active chain targets
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            t_min_str = f"{active_chain.target_min:.3f} mm" if active_chain.target_min is not None else "Non spécifié"
            st.markdown(f"**Cible minimale ($J_{{\\min}}$)** : `{t_min_str}`")
        with col_t2:
            t_max_str = f"{active_chain.target_max:.3f} mm" if active_chain.target_max is not None else "Non spécifié"
            st.markdown(f"**Cible maximale ($J_{{\\max}}$)** : `{t_max_str}`")

        # Composition vectorielle des maillons avec suppression individuelle
        st.markdown("#### Composition vectorielle de la chaîne")

        if active_chain.links:
            # Table header
            c_num, c_rep, c_sens, c_src, c_nom, c_tol, c_it, c_del = st.columns([0.6, 2.2, 0.8, 1.8, 1.2, 1.5, 1.0, 0.8])
            with c_num:
                st.markdown("**#**")
            with c_rep:
                st.markdown("**Repère / Désignation**")
            with c_sens:
                st.markdown("**Sens**")
            with c_src:
                st.markdown("**Source**")
            with c_nom:
                st.markdown("**Nominal**")
            with c_tol:
                st.markdown("**[EI ; ES]**")
            with c_it:
                st.markdown("**IT (mm)**")
            with c_del:
                st.markdown("**Retirer**")

            for idx, link in enumerate(active_chain.links):
                c_n, c_r, c_s, c_sc, c_nm, c_tl, c_i, c_d = st.columns([0.6, 2.2, 0.8, 1.8, 1.2, 1.5, 1.0, 0.8])
                if link.part_id:
                    p = project.parts.get(link.part_id)
                    nom = (p.nominal * link.scale_factor) if p else 0.0
                    es = (p.es * link.scale_factor) if p else 0.0
                    ei = (p.ei * link.scale_factor) if p else 0.0
                    source_lbl = f"🟢 [{link.part_id}]"
                    rep_name = link.custom_name or (p.name if p else f"Maillon {idx+1}")
                else:
                    nom = (link.local_nominal or 0.0) * link.scale_factor
                    es = (link.local_es or 0.0) * link.scale_factor
                    ei = (link.local_ei or 0.0) * link.scale_factor
                    source_lbl = "⚪ Locale"
                    rep_name = link.custom_name or f"Cote locale {idx+1}"

                orient_sym = "+" if link.orientation > 0 else "-"

                with c_n:
                    st.write(f"#{idx+1}")
                with c_r:
                    st.write(rep_name)
                with c_s:
                    st.write(f"**{orient_sym}**")
                with c_sc:
                    st.caption(source_lbl)
                with c_nm:
                    st.write(f"{nom:.3f}")
                with c_tl:
                    st.write(f"[{ei:+.3f} ; {es:+.3f}]")
                with c_i:
                    st.write(f"{es-ei:.3f}")
                with c_d:
                    if st.button("🗑️", key=f"del_link_{active_chain.id}_{idx}", help=f"Supprimer le maillon #{idx+1}"):
                        project.remove_link_from_chain(active_chain.id, idx)
                        st.rerun()
        else:
            st.info("Cette chaîne ne contient actuellement aucun maillon. Ajoutez-en un ci-dessous.")

        # Add link expander
        with st.expander("➕ Ajouter un maillon à cette chaîne", expanded=False):
            col_l1, col_l2, col_l3, col_l4 = st.columns([1.5, 1, 1.5, 1])
            with col_l1:
                link_kind = st.radio("Origine du maillon", options=["Pièce du Catalogue", "Cote Locale Autonome"], horizontal=True, key="link_kind_rad")
            with col_l2:
                link_orient_str = st.selectbox("Orientation vectorielle", options=["+ (augmente le jeu)", "- (diminue le jeu)"], key="link_orient_sel")
                link_orient = 1 if link_orient_str.startswith("+") else -1

            if link_kind == "Pièce du Catalogue":
                with col_l3:
                    cat_opts = list(project.parts.keys())
                    if cat_opts:
                        chosen_p_id = st.selectbox("Choisir la pièce maîtresse", options=cat_opts, format_func=lambda x: f"{project.parts[x].name} [{x}]", key="link_p_sel")
                    else:
                        st.warning("Aucune pièce au catalogue.")
                        chosen_p_id = None
                with col_l4:
                    custom_lbl = st.text_input("Nom contextuel (optionnel)", key="link_custom_lbl")

                if chosen_p_id and st.button("Ajouter le composant catalogue", type="primary", use_container_width=True, key="btn_add_cat_link"):
                    project.add_link_to_chain(
                        active_chain.id,
                        part_id=chosen_p_id,
                        orientation=link_orient,  # type: ignore
                        custom_name=custom_lbl,
                    )
                    st.success("Maillon lié au catalogue ajouté !")
                    st.rerun()
            else:
                with col_l3:
                    loc_name = st.text_input("Nom de la cote locale", value="Jeu de gorge", key="link_loc_name")
                    loc_nom = st.number_input("Nominal (mm)", min_value=0.0, value=10.0, step=1.0, key="link_loc_nom")
                with col_l4:
                    loc_es = st.number_input("ES (mm)", value=0.05, step=0.01, format="%.4f", key="link_loc_es")
                    loc_ei = st.number_input("EI (mm)", value=-0.05, step=0.01, format="%.4f", key="link_loc_ei")

                if st.button("Ajouter la cote locale", type="primary", use_container_width=True, key="btn_add_loc_link"):
                    project.add_link_to_chain(
                        active_chain.id,
                        orientation=link_orient,  # type: ignore
                        custom_name=loc_name,
                        local_nominal=loc_nom,
                        local_es=loc_es,
                        local_ei=loc_ei,
                    )
                    st.success("Cote locale ajoutée !")
                    st.rerun()

        # =====================================================================
        # RÉSULTATS DE CALCUL : PIRE DES CAS (WORST-CASE) UNIQUEMENT
        # =====================================================================
        if active_chain.links:
            try:
                res = project.evaluate_chain(active_chain.id)

                st.divider()
                st.markdown("#### 📐 Bilan arithmétique au Pire des Cas (Worst-Case)")

                # WC Metrics Row
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                with col_r1:
                    st.metric("Jeu Nominal ($J_{\\text{nom}}$)", f"{res.nominal:.4f} mm")
                with col_r2:
                    st.metric("Jeu Minimal ($J_{\\min,\\text{WC}}$)", f"{res.worst_case_minus:.4f} mm")
                with col_r3:
                    st.metric("Jeu Maximal ($J_{\\max,\\text{WC}}$)", f"{res.worst_case_plus:.4f} mm")
                with col_r4:
                    wc_it = res.worst_case_plus - res.worst_case_minus
                    st.metric("Dispersion Totale ($IT_{\\text{WC}}$)", f"{wc_it:.4f} mm")

                # Compliance & Safety Margins (Worst-Case Only)
                has_targets = active_chain.target_min is not None or active_chain.target_max is not None
                if has_targets:
                    col_m1, col_m2 = st.columns(2)
                    wc_compliant = True

                    with col_m1:
                        if active_chain.target_min is not None:
                            margin_min = res.worst_case_minus - active_chain.target_min
                            delta_color = "normal" if margin_min >= 0 else "inverse"
                            st.metric(
                                f"Marge minimale (vs Cible {active_chain.target_min:.3f} mm)",
                                f"{margin_min:+.4f} mm",
                                delta=f"{margin_min:+.4f} mm",
                                delta_color=delta_color,
                            )
                            if margin_min < 0:
                                wc_compliant = False
                        else:
                            st.info("Aucune cible minimale spécifiée.")

                    with col_m2:
                        if active_chain.target_max is not None:
                            margin_max = active_chain.target_max - res.worst_case_plus
                            delta_color = "normal" if margin_max >= 0 else "inverse"
                            st.metric(
                                f"Marge maximale (vs Cible {active_chain.target_max:.3f} mm)",
                                f"{margin_max:+.4f} mm",
                                delta=f"{margin_max:+.4f} mm",
                                delta_color=delta_color,
                            )
                            if margin_max < 0:
                                wc_compliant = False
                        else:
                            st.info("Aucune cible maximale spécifiée.")

                    # Worst-Case Banner Verdict
                    if wc_compliant:
                        st.success(
                            f"✅ **100% CONFORME AU PIRE DES CAS** : Le jeu fonctionnel [{res.worst_case_minus:.4f} ; {res.worst_case_plus:.4f}] mm "
                            f"est strictement compris dans les limites requises [{active_chain.target_min} ; {active_chain.target_max}] mm. "
                            f"Aucun risque de collision ni de jeu excessif."
                        )
                    else:
                        st.error(
                            f"❌ **NON CONFORME AU PIRE DES CAS** : Dépassement des limites fonctionnelles ! "
                            f"Ajustez les tolérances des pièces du catalogue pour retrouver la conformité."
                        )

                # Visual Horizontal Range Chart (WC only)
                st.plotly_chart(
                    render_wc_range_chart(res, active_chain.target_min, active_chain.target_max, active_chain.name),
                    use_container_width=True,
                )

            except Exception as e:
                st.error(f"Erreur de calcul pour la chaîne '{active_chain.id}' : {e}")

    # =========================================================================
    # ONGLET 3: TABLEAU DE BORD SYSTÈME & MATRICE DES IMPACTS (100% WC)
    # =========================================================================
    with tab_dashboard:
        st.subheader("📊 Tableau de Bord Système (Pire des Cas)")
        st.markdown(
            "Vue d'ensemble de la santé dimensionnelle du système complet au **Pire des Cas arithmétique (Worst-Case)**."
        )

        summary = project.get_system_summary()

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Nombre total de chaînes", f"{summary.total_chains}")
        with col_m2:
            st.metric("Chaînes conformes au pire des cas (WC)", f"{summary.wc_compliant_count} / {summary.total_chains}")
        with col_m3:
            wc_nok = summary.total_chains - summary.wc_compliant_count
            st.metric("Chaînes critiques non conformes WC", f"{wc_nok}", delta=None if wc_nok == 0 else f"-{wc_nok}")

        st.divider()

        # Summary Table (WC Only)
        st.markdown("#### 📋 Synthèse de toutes les chaînes d'assemblage (Pire des Cas)")
        sys_rows = []
        for s in summary.chains_status:
            c = project.get_chain(s.chain_id)
            c_parts = [l.part_id for l in c.links if l.part_id]
            sys_rows.append({
                "Chaîne": s.name,
                "ID": s.chain_id,
                "Jeu Nominal": f"{s.result.nominal:.3f} mm",
                "Jeu Pire des Cas [Min ; Max]": f"[{s.result.worst_case_minus:.3f} ; {s.result.worst_case_plus:.3f}] mm",
                "Dispersion IT_WC": f"{s.result.worst_case_plus - s.result.worst_case_minus:.3f} mm",
                "Cibles fonctionnelles": f"[{c.target_min} ; {c.target_max}]" if (c.target_min is not None or c.target_max is not None) else "Sans cible",
                "Verdict Pire des Cas": s.wc_status_label,
                "Pièces Catalogue": ", ".join(set(c_parts)) if c_parts else "Cotes locales",
            })

        if sys_rows:
            st.dataframe(pd.DataFrame(sys_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune chaîne définie dans le projet.")

        st.divider()

        # Shared Parts Matrix (Cross-Impacts)
        st.markdown("#### 🕸️ Matrice des Pièces Critiques (Pivots)")
        st.markdown(
            "Une **pièce pivot** est intégrée dans au moins **2 chaînes distinctes**. "
            "Resserrer ou relâcher sa tolérance impacte simultanément plusieurs exigences fonctionnelles du mécanisme."
        )

        matrix_rows = []
        for p_id, p in project.parts.items():
            used_in = summary.shared_parts_matrix.get(p_id, [])
            is_pivot = len(used_in) >= 2
            matrix_rows.append({
                "ID Pièce": p_id,
                "Désignation": p.name,
                "Type": "🔥 Pièce Pivot Critique" if is_pivot else "Pièce Locale (1 chaîne)",
                "Nb Chaînes": len(used_in),
                "Chaînes Utilisatrices": ", ".join(used_in) if used_in else "Aucune",
                "IT actuel (mm)": f"{p.IT:.4f}",
            })

        if matrix_rows:
            df_matrix = pd.DataFrame(matrix_rows).sort_values(by="Nb Chaînes", ascending=False)
            st.dataframe(df_matrix, use_container_width=True, hide_index=True)

        if summary.critical_pivot_parts:
            st.info(
                f"💡 **Recommandation** : Les composants `{'`, `'.join(summary.critical_pivot_parts)}` "
                f"sont des pièces pivots. Tout compromis sur leur tolérance d'usinage "
                f"doit être validé conjointement sur l'ensemble de leurs chaînes associées."
            )

        st.divider()

        # Import / Export JSON
        st.markdown("#### 💾 Sauvegarde & Export du Projet Multi-Chaînes")
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            project_json = project.to_json()
            st.download_button(
                label="📥 Télécharger le projet système (.cotastack_multi.json)",
                data=project_json,
                file_name="systeme_multi_chaines.cotastack_multi.json",
                mime="application/json",
                use_container_width=True,
                key="btn_download_multi",
            )
        with col_exp2:
            uploaded_file = st.file_uploader("📂 Charger un projet système JSON", type=["json"], key="upload_multi_json")
            if uploaded_file is not None:
                try:
                    content = uploaded_file.read().decode("utf-8")
                    loaded_proj = MultiChainProject.from_json(content)
                    st.session_state.multi_project = loaded_proj
                    st.success(f"Projet '{loaded_proj.name}' chargé avec {len(loaded_proj.parts)} pièces et {len(loaded_proj.chains)} chaînes !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors du chargement : {e}")


if __name__ == "__main__":
    main()
