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

    st.info("🚧 Application en cours de développement — Socle technique initialisé")

    with st.sidebar:
        st.header("Navigation")
        st.page_link("app.py", label="🏠 Accueil", icon="🏠")
        st.page_link("pages/01_Calculateur.py", label="🧮 Calculateur", icon="🧮")
        st.page_link("pages/02_Standards_ISO.py", label="📋 Standards ISO", icon="📋")
        st.page_link("pages/03_Rapports.py", label="📄 Rapports", icon="📄")

        st.divider()
        st.markdown("**Méthodes de calcul**")
        st.checkbox("Pire des cas (WC)", value=True, disabled=True)
        st.checkbox("RSS (Statistical)", value=True, disabled=True)
        st.checkbox("Dilatation thermique", value=False, disabled=True)

        st.divider()
        st.markdown("[Documentation](https://github.com/cotastack)")
        st.markdown("[Signaler un bug](https://github.com/cotastack/issues)")

    st.subheader("Bienvenue dans CotaStack")
    st.markdown("""
    **CotaStack** est un outil web d'ingénierie mécanique pour le calcul et l'analyse de chaînes de cotes 1D.

    ### Fonctionnalités prévues
    - **Tracé graphique vectoriel** : Visualisation interactive des maillons avec sens et fermeture de boucle
    - **Double moteur de calcul** : Pire des cas (arithmétique) et RSS (quadratique)
    - **Standards ISO intégrés** : ISO 286 (ajustements) et ISO 2768-1 (tolérances générales)
    - **Dilatation thermique** : Prise en compte des coefficients de dilatation matériaux
    - **Export PDF normé** : Notes de calcul horodatées avec verdict Go/No-Go
    - **Sauvegarde projets** : Réutilisation et versioning des chaînes de cotes

    ### Démarrage rapide (développement)
    ```bash
    uv venv && uv pip install -r requirements.txt
    streamlit run app.py
    ```
    """)

    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Statut", "🟢 Socle prêt")
    with col2:
        st.metric("Architecture", "Modulaire")
    with col3:
        st.metric("Tests", "pytest prêt")


if __name__ == "__main__":
    main()