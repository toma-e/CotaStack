"""CotaStack - Répertoire Unifié Multi-Chaînes (Jalon 3.1).

Gestion centralisée des pièces maîtresses et propagation instantanée
sur l'ensemble des chaînes d'assemblage d'un mécanisme complexe.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
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


def main() -> None:
    st.title("🏢 Répertoire Unifié Multi-Chaînes")
    st.caption("Gestion centralisée des pièces maîtresses & Propagation instantanée sur l'assemblage complet")

    # Session State Project Initialization
    if "multi_project" not in st.session_state:
        st.session_state.multi_project = init_default_project()

    project: MultiChainProject = st.session_state.multi_project
    materials = get_available_materials()

    with st.sidebar:
        st.header("🏢 Multi-Chaînes Système")
        st.caption("Mode test & qualification prioritaire (Jalon 3.1)")
        st.markdown(f"**Projet** : `{project.name}`")
        col_sb1, col_sb2 = st.columns(2)
        with col_sb1:
            st.metric("Pièces Maîtresses", len(project.parts))
        with col_sb2:
            st.metric("Chaînes Système", len(project.chains))

        st.divider()
        st.markdown("**Navigation de test**")
        st.info("ℹ️ Vous êtes directement sur le module Multi-Chaînes pour vos tests prioritaires.")

        unlock = st.toggle(
            "Afficher tous les modules",
            value=st.session_state.get("unlock_all_pages", False),
            key="toggle_unlock_pages",
            help="Permet d'afficher les autres modules (Calculateur 1D, Standards ISO, Rapports) sans recharger la page.",
        )
        if unlock != st.session_state.get("unlock_all_pages", False):
            st.session_state.unlock_all_pages = unlock
            st.rerun()

    tab_catalog, tab_chains, tab_dashboard = st.tabs([
        "📦 Répertoire & Pièces Partagées",
        "🔗 Chaînes d'Assemblage du Système",
        "📊 Tableau de Bord & Matrice d'Impacts",
    ])

    # =========================================================================
    # ONGLET 1: CATALOGUE DES PIÈCES MAÎTRESSES
    # =========================================================================
    with tab_catalog:
        st.subheader("📦 Catalogue des Pièces Maîtresses (Single Source of Truth)")
        st.markdown(
            "Définissez chaque composant physique **une seule fois**. "
            "Toute modification d'une tolérance ou d'une cote nominale est immédiatement "
            "propagée et recalculée sur toutes les chaînes d'assemblage utilisatrices."
        )

        col_cat_table, col_cat_form = st.columns([1.6, 1.2])

        with col_cat_table:
            # Build display dataframe
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
                    "Chaînes d'impact": f"{len(chains_used)} chaîne(s) ({', '.join(chains_used)})" if chains_used else "Aucune",
                })

            if parts_rows:
                df_parts = pd.DataFrame(parts_rows)
                st.dataframe(df_parts, use_container_width=True, hide_index=True)
            else:
                st.info("Le catalogue de pièces est actuellement vide.")

            st.divider()
            # Fast Propagation Simulator for demonstration
            st.markdown("#### ⚡ Simulateur de propagation directe")
            shared_p_options = list(project.parts.keys())
            if shared_p_options:
                selected_sim_p = st.selectbox(
                    "Choisir une pièce pour simuler un ajustement de tolérance :",
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
                        st.success(f"Tolérances de '{sim_part.name}' mises à jour. Propagation effectuée sur : {', '.join(impacted)} !")
                        st.rerun()

                if impacted:
                    st.caption(f"📢 **Impact direct** : La modification affectera simultanément les chaînes : `{'`, `'.join(impacted)}`.")
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
                    if st.button("🗑️ Supprimer", use_container_width=True, key="btn_del_part"):
                        impacted = project.remove_part(target_part.id)
                        st.warning(f"Pièce supprimée du catalogue (impact : {len(impacted)} chaîne(s)).")
                        st.rerun()

    # =========================================================================
    # ONGLET 2: CHAÎNES D'ASSEMBLAGE DU SYSTÈME
    # =========================================================================
    with tab_chains:
        st.subheader("🔗 Chaînes d'Assemblage du Système Mécanique")

        col_c_sel, col_c_action = st.columns([2, 1])
        with col_c_sel:
            chain_keys = list(project.chains.keys())
            if not chain_keys:
                st.warning("Aucune chaîne définie dans le projet.")
                return

            active_chain_id = st.selectbox(
                "Sélectionner la chaîne d'assemblage à afficher :",
                options=chain_keys,
                format_func=lambda x: f"{project.chains[x].name} ({len(project.chains[x].links)} maillons)",
                key="active_chain_select",
            )
        with col_c_action:
            st.write("")
            with st.expander("➕ Créer une nouvelle chaîne", expanded=False):
                new_c_id = st.text_input("ID Chaîne (ex: CH_JEU_PIGNON)", key="new_c_id")
                new_c_name = st.text_input("Nom de la chaîne", key="new_c_name")
                col_tmin, col_tmax = st.columns(2)
                with col_tmin:
                    new_tmin = st.number_input("Cible Min (mm)", value=0.1, step=0.1, key="new_tmin")
                with col_tmax:
                    new_tmax = st.number_input("Cible Max (mm)", value=0.8, step=0.1, key="new_tmax")
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

        # Header of active chain
        st.markdown(f"### 📍 {active_chain.name} (`{active_chain.id}`)")
        if active_chain.description:
            st.caption(active_chain.description)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            t_min_str = f"{active_chain.target_min:.3f} mm" if active_chain.target_min is not None else "Non spécifié"
            st.markdown(f"**Cible minimale ($J_{{\\min}}$)** : `{t_min_str}`")
        with col_t2:
            t_max_str = f"{active_chain.target_max:.3f} mm" if active_chain.target_max is not None else "Non spécifié"
            st.markdown(f"**Cible maximale ($J_{{\\max}}$)** : `{t_max_str}`")

        # Table of links
        st.markdown("#### Composition vectorielle de la chaîne")
        links_rows = []
        for idx, link in enumerate(active_chain.links):
            if link.part_id:
                p = project.parts.get(link.part_id)
                nom = (p.nominal * link.scale_factor) if p else 0.0
                es = (p.es * link.scale_factor) if p else 0.0
                ei = (p.ei * link.scale_factor) if p else 0.0
                source_lbl = f"🟢 Catalogue [{link.part_id}]"
                mat = p.material if p else "Inconnu"
            else:
                nom = (link.local_nominal or 0.0) * link.scale_factor
                es = (link.local_es or 0.0) * link.scale_factor
                ei = (link.local_ei or 0.0) * link.scale_factor
                source_lbl = "⚪ Cote Locale"
                mat = link.local_material

            orient_sym = "+" if link.orientation > 0 else "-"
            links_rows.append({
                "#": idx + 1,
                "Repère": link.custom_name or (p.name if link.part_id and p else f"Maillon {idx+1}"),
                "Sens": orient_sym,
                "Source": source_lbl,
                "Nominal (mm)": f"{nom:.3f}",
                "ES (mm)": f"{es:+.4f}",
                "EI (mm)": f"{ei:+.4f}",
                "IT (mm)": f"{es-ei:.4f}",
                "Matériau": mat,
            })

        if links_rows:
            st.dataframe(pd.DataFrame(links_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun maillon dans cette chaîne.")

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
                    chosen_p_id = st.selectbox("Choisir la pièce maîtresse", options=cat_opts, format_func=lambda x: f"{project.parts[x].name} [{x}]", key="link_p_sel")
                with col_l4:
                    custom_lbl = st.text_input("Nom contextuel (optionnel)", key="link_custom_lbl")

                if st.button("Ajouter le composant catalogue", type="primary", use_container_width=True, key="btn_add_cat_link"):
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

        # Chain Calculation Results
        if active_chain.links:
            try:
                res = project.evaluate_chain(active_chain.id)

                st.divider()
                st.markdown("#### 📈 Résultats de calcul temps réel")

                # Metrics Row
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                with col_r1:
                    st.metric("Jeu Nominal (J_nom)", f"{res.nominal:.4f} mm")
                with col_r2:
                    st.metric("Pire des Cas (WC)", f"[{res.worst_case_minus:.4f} ; {res.worst_case_plus:.4f}] mm", f"IT = {res.worst_case_plus - res.worst_case_minus:.4f} mm")
                with col_r3:
                    st.metric("Statistique RSS (3σ)", f"[{res.rss_minus:.4f} ; {res.rss_plus:.4f}] mm", f"IT = {res.rss_plus - res.rss_minus:.4f} mm")
                with col_r4:
                    wc_ok = res.compliance.get("wc_compliant")
                    if wc_ok is True:
                        st.metric("Statut Conformité WC", "✅ Conforme", "Dans les limites cibles")
                    elif wc_ok is False:
                        st.metric("Statut Conformité WC", "❌ Hors Tolérance", "Dépassement cible")
                    else:
                        st.metric("Statut Conformité WC", "⚪ Sans cible", "Aucune cible")

                # Compliance Banner
                if res.target_min is not None or res.target_max is not None:
                    if res.compliance.get("wc_compliant"):
                        st.success(f"✅ Chaîne conforme au pire des cas (WC) dans la plage [{active_chain.target_min} ; {active_chain.target_max}] mm.")
                    elif res.compliance.get("rss_compliant"):
                        st.warning("⚠️ Chaîne non conforme au pire des cas absolu, mais conforme en statistique RSS (99.73%).")
                    else:
                        st.error("❌ Risque élevé de non-conformité : les tolérances actuelles des pièces dépassent les cibles fonctionnelles !")

                # Pareto chart
                if res.pareto:
                    fig_pareto = px.bar(
                        pd.DataFrame(res.pareto),
                        x="name",
                        y="contribution_pct",
                        title=f"Diagramme de Pareto des Variances — {active_chain.name}",
                        labels={"name": "Composant / Maillon", "contribution_pct": "Contribution à la variance (%)"},
                        text_auto=".1f",
                        color="contribution_pct",
                        color_continuous_scale="Blues",
                    )
                    fig_pareto.update_layout(height=320, margin=dict(l=30, r=30, t=40, b=30))
                    st.plotly_chart(fig_pareto, use_container_width=True)

            except Exception as e:
                st.error(f"Erreur de calcul pour la chaîne '{active_chain.id}' : {e}")

    # =========================================================================
    # ONGLET 3: TABLEAU DE BORD SYSTÈME & MATRICE DES IMPACTS
    # =========================================================================
    with tab_dashboard:
        st.subheader("📊 Tableau de Bord Système & Matrice des Impacts Croisés")
        st.markdown(
            "Vue d'ensemble de la santé dimensionnelle du système complet. "
            "Identifiez d'un coup d'œil les pièces critiques (pivots) partagées par plusieurs chaînes."
        )

        summary = project.get_system_summary()

        # Health metrics
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Nombre total de chaînes", f"{summary.total_chains}")
        with col_m2:
            st.metric("Chaînes conformes au pire cas (WC)", f"{summary.wc_compliant_count} / {summary.total_chains}")
        with col_m3:
            st.metric("Chaînes conformes en RSS (3σ)", f"{summary.rss_compliant_count} / {summary.total_chains}")
        with col_m4:
            st.metric("Chaînes critiques non conformes", f"{summary.non_compliant_count}", delta=None if summary.non_compliant_count == 0 else f"-{summary.non_compliant_count}")

        st.divider()

        # Summary Table
        st.markdown("#### 📋 Statut de toutes les chaînes d'assemblage")
        sys_rows = []
        for s in summary.chains_status:
            c = project.get_chain(s.chain_id)
            c_parts = [l.part_id for l in c.links if l.part_id]
            sys_rows.append({
                "Chaîne": s.name,
                "ID": s.chain_id,
                "Jeu Nominal": f"{s.result.nominal:.3f} mm",
                "Jeu WC [Min ; Max]": f"[{s.result.worst_case_minus:.3f} ; {s.result.worst_case_plus:.3f}]",
                "Jeu RSS [Min ; Max]": f"[{s.result.rss_minus:.3f} ; {s.result.rss_plus:.3f}]",
                "Cibles [Min ; Max]": f"[{c.target_min} ; {c.target_max}]" if (c.target_min is not None or c.target_max is not None) else "—",
                "Verdict WC": s.wc_status_label,
                "Verdict RSS": s.rss_status_label,
                "Pièces Catalogue": ", ".join(set(c_parts)) if c_parts else "Cotes locales",
            })

        if sys_rows:
            st.dataframe(pd.DataFrame(sys_rows), use_container_width=True, hide_index=True)

        st.divider()

        # Shared Parts Matrix (Cross-Impacts)
        st.markdown("#### 🕸️ Matrice des Pièces Critiques (Pivots)")
        st.markdown(
            "Une **pièce pivot** est intégrée dans au moins **2 chaînes distinctes**. "
            "Resserrer ou relâcher sa tolérance impacte simultanément plusieurs exigences fonctionnelles de l'appareil."
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

        df_matrix = pd.DataFrame(matrix_rows).sort_values(by="Nb Chaînes", ascending=False)
        st.dataframe(df_matrix, use_container_width=True, hide_index=True)

        if summary.critical_pivot_parts:
            st.info(
                f"💡 **Recommandation d'optimisation** : Les pièces `{'`, `'.join(summary.critical_pivot_parts)}` "
                f"sont des composants pivots clés. Tout compromis technico-économique sur leur tolérance d'usinage "
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
