"""CotaStack - Point d'entrée principal.

Accès direct et exclusif au module Répertoire Multi-Chaînes.
Les autres pages historiques (Calculateur 1D, Standards ISO, Rapports mono-chaîne)
sont considérées comme obsolètes / dépréciées et sont masquées de la navigation.
"""

import streamlit as st

# Définition exclusive de la page multi-chaînes (seule page active)
page_multi = st.Page(
    "pages/04_Multi_Chaines.py",
    title="Multi-Chaînes Système",
    icon="🏢",
    default=True,
)

# Navigation strictement limitée à la page multi-chaînes, menu latéral masqué
pg = st.navigation([page_multi], position="hidden")
pg.run()

