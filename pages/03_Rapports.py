"""CotaStack - Rapports (Phase 3 - À venir)."""

import streamlit as st


st.set_page_config(page_title="Rapports", page_icon="📄", layout="wide")


def main():
    st.title("📄 Rapports & Export")
    st.caption("Génération de notes de calcul PDF — Phase 3")

    st.info("🚧 **Module en cours de développement** — Disponible en Phase 3")

    st.markdown("""
    ### Fonctionnalités prévues

    #### 📑 Générateur PDF normé (A4)
    - **Cartouche** : Projet, Auteur, Date, Révision, Statut
    - **Tableau des maillons** : Repère, Orientation, Nominal, ES, EI, IT, L_moy
    - **Résultats** : Jeu Nominal, Jeu Moyen, WC (Min/Max), RSS (Min/Max)
    - **IT Totaux** : WC (arithmétique) & RSS (quadratique)
    - **Analyse de Pareto** : Graphique + tableau des contributions
    - **Distribution Gauss** : Courbe avec bornes WC, RSS, Cibles
    - **Verdict** : GO / NO-GO avec marges
    - **Bloc d'approbation** : Signature, Date, Visa qualité

    #### 💾 Export légers (Phase 2)
    - CSV : Données tabulaires UTF-8
    - Markdown : Synthèse textuelle pour email/CR
    - JSON `.cotastack` : Sauvegarde complète du projet (Phase 4)
    """)

    st.divider()
    st.warning(
        "⚠️ **Avertissement** : Outil d'aide à la conception. "
        "L'utilisateur demeure seul responsable de la validation technique avant fabrication."
    )


if __name__ == "__main__":
    main()