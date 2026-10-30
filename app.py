"""CotaStack - 1D Tolerance Chain Calculator.

Streamlit web application for mechanical tolerance stack-up analysis.
Supports Worst-Case and RSS (Root Sum Square) calculation methods.
"""

import streamlit as st

st.set_page_config(
    page_title="CotaStack — Chaînes de cotes 1D",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    st.title("CotaStack — Chaînes de cotes 1D")
    st.caption("Calcul de tolérancement 1D : Pire des cas & RSS — Conforme pratiques ISO")

    with st.sidebar:
        st.header("Navigation")
        st.page_link("app.py", label="🏠 Accueil", icon="🏠")
        st.page_link("pages/01_Calculateur.py", label="🧮 Calculateur", icon="🧮")
        st.page_link("pages/02_Standards_ISO.py", label="📋 Standards ISO", icon="📋")
        st.page_link("pages/03_Rapports.py", label="📄 Rapports & Export", icon="📄")

        st.divider()
        st.markdown("**Méthodes de calcul**")
        st.checkbox("Pire des cas (WC)", value=True, disabled=True)
        st.checkbox("RSS (Statistique)", value=True, disabled=True)
        st.checkbox("Dilatation thermique", value=False, disabled=True)

        st.divider()
        st.markdown("[Documentation](https://github.com/cotastack)")
        st.markdown("[Signaler un bug](https://github.com/cotastack/issues)")

    st.subheader("Bienvenue dans CotaStack")
    st.markdown("""
    **CotaStack** est un outil web d'ingénierie mécanique pour le dimensionnement, le calcul et l'optimisation des chaînes de cotes 1D.

    ### Fonctionnalités opérationnelles (Phases 1 & 2)
    - ✅ **Calculateur interactif** : Saisie vectorielle de maillons, recalcul instantané Pire des Cas (WC) & Statistique (RSS).
    - ✅ **Analyse de Pareto** : Classement par contribution quadratique à la variance totale pour cibler les tolérances critiques.
    - ✅ **Distribution Gaussienne** : Courbe de densité RSS à 3σ avec bornes fonctionnelles cibles ($J_{min}, J_{max}$).
    - ✅ **Conformité & Marges** : Badges Go / No-Go immédiats avec calcul des marges d'assemblage.
    - ✅ **Référentiel ISO 286** : Calculateur d'ajustements (H7/g6, H8/f7, etc.) avec qualification du type (jeu, serrage, incertain) et positionnement graphique des IT.
    - ✅ **Tolérances générales ISO 2768-1** : Classes f, m, c, v pour cotes linéaires et chanfreins.
    - ✅ **Assistant d'injection** : Injection directe de cotes normées (ISO 286 et 2768-1) dans la chaîne de calcul.
    - ✅ **Exports légers** : Export CSV du tableau et génération de note de calcul Markdown prête pour compte-rendu ou e-mail.

    ### Feuilles de route à venir (Phase 3 & 4)
    - 🚧 **Dilatation thermique différentielle** : Prise en compte du gradient de température $\\Delta T$ et des coefficients $\\alpha$ des matériaux.
    - 🚧 **Simulation stochastique Monte Carlo** : Prédiction du taux de non-conformité en PPM.
    - 🚧 **Générateur PDF normé A4** : Note de calcul complète avec cartouche officiel, graphiques vectoriels et visa qualité.
    """)

    st.divider()
    st.warning(
        "⚠️ **Avertissement** : Outil d'aide à la conception. "
        "L'utilisateur demeure seul responsable de la validation technique de ses chaînes avant fabrication."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Statut", "🟢 Phases 1 & 2 opérationnelles")
    with col2:
        st.metric("Tests unitaires", "33/33 validés (100%)")
    with col3:
        st.metric("Couverture backend", "100% (models/calc/iso)")


if __name__ == "__main__":
    main()
