# Palette's Journal - UX & Accessibility Learnings

## 2026-11-03 - Streamlit Widget Key Isolation & Real-Time Propagation Feedback
**Observation:**
Dans les interfaces interactives Streamlit (comme le Simulateur de Propagation Directe du catalogue multi-chaînes), assigner des clés statiques (`key="sim_new_es"`) aux champs `st.number_input` ou `st.text_input` entraîne la persistance de l'état dans `st.session_state`. Quand l'utilisateur change la sélection d'un `st.selectbox` parent, Streamlit ignore l'argument `value=sim_part.es` mis à jour et conserve les valeurs de la pièce précédemment sélectionnée. L'utilisateur se retrouve avec des champs désynchronisés et risque d'écraser silencieusement les tolérances d'une pièce avec celles d'une autre.

**Learning & Contrainte UX:**
1. **Isolation des clés de widgets contextuels :** Toujours préfixer ou suffixer les `key` des widgets d'édition dépendants avec l'identifiant de l'élément sélectionné (ex: `key=f"sim_new_es_{selected_sim_p}"`). Cela force Streamlit à instancier un état propre à chaque entité et garantit le rechargement immédiat des valeurs nominales et tolérances réelles.
2. **Double lecture et repères dimensionnels :** En métrologie et cotation fonctionnelle, ne jamais afficher des champs de saisie d'écarts (ES, EI) sans rappeler explicitement la cote nominale et les tolérances actuelles de référence en sous-titre (`st.caption`).
3. **Feedback pré-action et accessibilité :** Fournir des infobulles explicatives (`help=...`) sur les notions normatives (ES, EI, IT) et un retour visuel immédiat (comme `st.metric` avec delta coloré sur l'intervalle de tolérance IT simulé) permet à l'utilisateur d'anticiper l'impact de son ajustement avant même de déclencher la propagation.
