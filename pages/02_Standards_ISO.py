"""CotaStack - Standards ISO (Phase 2 - À venir)."""

import streamlit as st


st.set_page_config(page_title="Standards ISO", page_icon="📋", layout="wide")


def main():
    st.title("📋 Standards ISO")
    st.caption("ISO 286 (Ajustements) & ISO 2768-1 (Tolérances générales) — Phase 2")

    st.info("🚧 **Module en cours de développement** — Disponible en Phase 2")

    st.markdown("""
    ### Fonctionnalités prévues

    #### 🔧 ISO 286 — Système d'ajustements
    - Sélecteur d'ajustement (ex: H7/g6, H8/f7, etc.)
    - Lookup automatique des écarts ES/EI selon le diamètre nominal
    - Pré-remplissage direct dans le calculateur
    - Calcul isolé : Jeu / Serrage / Incertain avec verdict

    #### 📐 ISO 2768-1 — Tolérances générales
    - Classes de précision : **f** (fine), **m** (moyenne), **c** (grosse), **v** (très grosse)
    - Tolérances linéaires par palier dimensionnel
    - Tolérances angulaires et de chanfrein
    - Application rapide aux cotes sans tolérance explicite

    #### 🔄 Intégration
    - Bouton "Appliquer au calculateur" depuis chaque standard
    - Mise à jour automatique des colonnes ES/EI dans le tableau
    """)

    st.divider()
    st.warning(
        "⚠️ **Avertissement** : Outil d'aide à la conception. "
        "L'utilisateur demeure seul responsable de la validation technique avant fabrication."
    )


if __name__ == "__main__":
    main()