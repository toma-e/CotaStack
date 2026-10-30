"""CotaStack - Point d'entrée principal.

Accès direct et exclusif au module Répertoire Multi-Chaînes (Jalon 3.1).
Menu latéral masqué pour concentration totale sur les tests multi-chaînes.
Tous les autres modules existants (Calculateur 1D, Standards ISO, Rapports) restent préservés dans le code.
"""

import streamlit as st

# Définition exclusive de la page multi-chaînes
page_multi = st.Page(
    "pages/04_Multi_Chaines.py",
    title="Multi-Chaînes Système",
    icon="🏢",
    default=True,
)

# Navigation strictement limitée à la page multi-chaînes, menu masqué
pg = st.navigation([page_multi], position="hidden")
pg.run()
