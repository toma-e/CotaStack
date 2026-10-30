"""CotaStack - Point d'entrée principal.

Arrivée directe sur le module Répertoire Multi-Chaînes (Jalon 3.1).
Toutes les autres pages (Calculateur 1D, Standards ISO, Rapports) sont préservées intactes.
"""

import streamlit as st

# Définition des pages de l'application
page_multi = st.Page(
    "pages/04_Multi_Chaines.py",
    title="Multi-Chaînes Système",
    icon="🏢",
    default=True,
)
page_calculateur = st.Page(
    "pages/01_Calculateur.py",
    title="Calculateur 1D",
    icon="🧮",
)
page_iso = st.Page(
    "pages/02_Standards_ISO.py",
    title="Standards ISO",
    icon="📋",
)
page_rapports = st.Page(
    "pages/03_Rapports.py",
    title="Rapports & Export",
    icon="📄",
)

# Accès direct et exclusif à la page multi-chaînes pour les tests
if "unlock_all_pages" not in st.session_state:
    st.session_state.unlock_all_pages = False

if st.session_state.unlock_all_pages:
    pg = st.navigation({
        "🎯 Priorité en cours": [page_multi],
        "Outils complémentaires": [page_calculateur, page_iso, page_rapports],
    })
else:
    # Navigation masquée : l'utilisateur arrive directement et uniquement sur Multi-Chaînes
    pg = st.navigation([page_multi], position="hidden")

pg.run()
