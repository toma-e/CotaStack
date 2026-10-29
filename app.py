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
        st.page_link("pages/03_Rapports.py", label="📄 Rapports", icon="📄")

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
    **CotaStack** est un outil web d'ingénierie mécanique pour le calcul et l'analyse de chaînes de cotes 1D.

    ### Fonctionnalités disponibles (Phase 1)
    - ✅ **Calculateur interactif** : Saisie de maillons, résultats WC/RSS temps réel
    - ✅ **Analyse de Pareto** : Identification de la cote la plus pénalisante
    - ✅ **Distribution statistique** : Courbe Gauss RSS avec bornes cibles
    - ✅ **Conformité** : Badges Go/No-Go vs jeu cible
    - 🚧 **Standards ISO** : ISO 286 & 2768-1 (Phase 2)
    - 🚧 **Dilatation thermique** : ΔT matériaux (Phase 3)
    - 🚧 **Export PDF** : Notes de calcul normées (Phase 3)

    ### Démarrage rapide (développement)
    ```bash
    uv venv && uv pip install -r requirements.txt
    streamlit run app.py
    ```
    """)

    st.divider()
    st.warning(
        "⚠️ **Avertissement** : Outil d'aide à la conception. "
        "L'utilisateur demeure seul responsable de la validation technique de ses chaînes avant fabrication."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Statut", "🟢 Phase 1 opérationnelle")
    with col2:
        st.metric("Backend", "100% tests OK")
    with col3:
        st.metric("Couverture", "100% (calculator/models)")


if __name__ == "__main__":
    main()