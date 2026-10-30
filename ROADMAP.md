# Feuille de route technique et fonctionnelle — CotaStack

Ce document formalise la feuille de route d'ingénierie logicielle pour **CotaStack**, solution web dédiée au dimensionnement, à l'analyse et à l'optimisation des chaînes de cotes 1D.  
Chaque brique est validée par une suite de tests unitaires automatisés (`pytest`) avec un objectif strict de **100 % de couverture de test** sur le backend d'ingénierie.

---

## 🟢 Phase 1 : Cœur 1D déterministe et statistique (Socle MVP)

L'objectif de cette phase est de supplanter les tableurs informels par un outil rapide, fiable, testé et sécurisé contre les erreurs de sens vectoriel.

### 1.1 — Moteur métier pur et modèle de données (`backend/`)
- [x] **Modèle structurel (`backend/models.py`)** :
  - Dataclass `Item` : `id`, `name`, `orientation` (+1 ou -1), `nominal`, `es` (écart sup), `ei` (écart inf).
  - Validation stricte dès l'instanciation : lever `ValueError` si $es < ei$.
  - Propriétés dérivées : Intervalle de tolérance ($IT = es - ei$), cote moyenne ($L_{\text{moy}} = nominal + \frac{es + ei}{2}$).
- [x] **Moteur de calcul vectoriel (`backend/calculator.py`)** :
  - Classe `ChainCalculator(items, target_min=None, target_max=None)`.
  - Contrôle d'intégrité vectorielle : vérification de la fermeture de la boucle dimensionnelle ($\sum a_i L_i - J_{\text{nom}} = 0$).
  - Calcul du jeu nominal et du jeu moyen.
  - Calcul Worst Case (Pire des Cas) : $J_{\min, \text{WC}}$, $J_{\max, \text{WC}}$ et $IT_{\text{total, WC}}$.
  - Calcul RSS (Statistique quadratique à $3\sigma$) : $J_{\min, \text{RSS}}$, $J_{\max, \text{RSS}}$ et $IT_{\text{total, RSS}} = \sqrt{\sum IT_i^2}$.
  - Analyse de contribution de Pareto : pourcentage de variance par cote ($C_i = \frac{IT_i^2}{\sum IT_k^2} \times 100$).
  - Évaluation de conformité vis-à-vis des bornes cibles ($J_{\min,\text{cible}}$, $J_{\max,\text{cible}}$).
- [x] **Tests unitaires (`tests/test_calculator.py`)** :
  - Validation mathématique des formules WC et RSS sur des cas étalons Cetim.
  - Test de détection et levée d'exception si $es < ei$.
  - Vérification de la somme des contributions de Pareto (égale à 100 %).

### 1.2 — Interface utilisateur réactive (`app.py` & `pages/01_Calculateur.py`)
- [x] **Saisie tabulaire interactive (`st.data_editor`)** :
  - Tableau réactif avec typage strict : Repère, Orientation (+/-), Nominal, ES, EI.
  - Calcul automatique et affichage de l'IT en temps réel.
  - Champs optionnels pour définir le Jeu Cible ($J_{\min}$ et $J_{\max}$).
- [x] **Tableau de bord de synthèse & Sécurité** :
  - Cartes métriques réactives : Jeu nominal, Pire des cas (Min/Max), RSS (Min/Max).
  - Badges de conformité visuelle Go / No-Go.
  - Mention d'avertissement permanente : *"Outil d'aide à la conception. L'utilisateur demeure seul responsable de la validation technique de ses chaînes avant fabrication."*
- [x] **Recette fonctionnelle** :
  - Recalcul dynamique immédiat lors de la modification d'une cellule sans réinitialisation de l'état Streamlit (`st.session_state`).

### 1.3 — Visualisation d'aide à la décision (Plotly)
- [x] Diagramme de Pareto horizontal identifiant instantanément la cote la plus pénalisante.
- [x] Courbe de distribution de Gauss RSS avec matérialisation des bornes cibles de l'assemblage.

---

## 🔵 Phase 2 : Référentiel normatif d'atelier et ergonomie opérationnelle

L'objectif de cette phase est d'éliminer la consultation manuelle des tables physiques et de faciliter l'export des données.

### 2.1 — Système d'ajustements ISO 286-1 et ISO 286-2
- [x] **Backend normatif (`backend/iso_standards.py`)** :
  - Tables d'écarts limites pour alésages (H7, H8, H11, F8, D10) et arbres (h6, g6, f7, p6, k6, js6).
  - Fonction de lookup : `get_iso286_limits(nominal, fit_code) -> tuple[float, float]`.
- [x] **UI (`pages/02_Standards_ISO.py` & intégration calculateur)** :
  - Remplissage automatique des écarts $ES$ et $EI$ dans le tableau dès le choix d'un symbole ISO.
  - Page dédiée au calcul isolé d'un ajustement (Jeu / Serrage / Incertain).
- [x] **Tests unitaires (`tests/test_iso_standards.py`)** : Contrôle d'exactitude sur les paliers dimensionnels critiques face aux tables officielles.

### 2.2 — Tolérances générales d'usinage et veille normative
- [x] **Tolérances générales ISO 2768-1** : Classes linéaire et chanfrein (*f*, *m*, *c*, *v*) par palier dimensionnel.
- [x] **Veille normative ISO 22081:2021** : Remplacement didactique de l'ancienne ISO 2768-2 par une notice sur le profil de surface général avec système de références.

### 2.3 — Exports légers
- [x] Export CSV direct du tableau des maillons.
- [x] Bouton de copie d'une synthèse textuelle/Markdown prête pour intégration dans un e-mail ou dossier de calcul.

---

## 🟡 Phase 3 : Modules avancés à fort impact concurrentiel

L'objectif de cette phase est d'apporter des briques d'aide à la décision à forte valeur ajoutée absentes des tableurs et visualiseurs basiques.

### 3.1 — Répertoire unifié des cotes sources & impact multi-chaînes (Différenciateur Majeur)
- [x] Modèle relationnel d'entité « Cotes Pièces » (`backend/multi_chain.py`).
- [x] Instanciation dynamique d'une même dimension physique dans plusieurs chaînes d'assemblage distinctes avec coefficients vectoriels.
- [x] Propagation automatique et recalcul en cascade de la conformité globale de l'ensemble du mécanisme.
- [x] Page dédiée interactive `pages/04_Multi_Chaines.py` avec gestion CRUD (ajout/modification/suppression de pièces, chaînes et liaisons, réinitialisation de projet).
- [x] Tests unitaires complets (`tests/test_multi_chain.py`).

### 3.2 — Allocation inverse et synthèse de tolérances (Différenciateur Majeur)
- [x] Définition d'un jeu cible global $[J_{\min}, J_{\max}]$.
- [x] Algorithme d'optimisation mathématique distribuant automatiquement les tolérances $IT_i$ sur les composants (`backend/tolerance_synthesis.py`).
- [x] Trois modes de synthèse : proportionnel, minimisation de coût de fabrication (pondération procédés) et échelonnement par degré de qualité ISO.
- [x] Tests unitaires automatisés (`tests/test_tolerance_synthesis.py`).

### 3.3 — Compensation des dilatations thermiques différentielles ($\Delta T$)
- [x] Base de données des coefficients de dilatation $\alpha$ (aciers, inox, alu, laiton, polymères POM) (`backend/thermal.py`).
- [x] Recalcul dimensionnel : $L(T) = L_{20^\circ\text{C}} \times [1 + \alpha (T_{\text{service}} - 20)]$.
- [x] Tableau comparatif : Jeu de montage à froid ($20\text{ }^\circ\text{C}$) vs Jeu de fonctionnement à chaud.
- [x] Courbe continue de sensibilité thermique $J(T)$.
- [x] Tests unitaires automatisés (`tests/test_thermal.py`).

### 3.4 — Convertisseur 1D des spécifications géométriques (ISO GPS / ASME Y14.5)
- [x] Projection 1D des défauts de localisation, d'orientation (parallélisme) et de battement (`backend/geometric_tolerances.py`).
- [x] Prise en compte de l'exigence du maximum de matière (MMR / symbole Ⓜ) avec calcul du bonus dimensionnel.
- [x] Calcul de l'état virtuel d'assemblabilité ($V_c$) et vérification de garantie de montage.
- [x] Tests unitaires automatisés (`tests/test_geometric_tolerances.py`).

### 3.5 — Statistique industrielle avancée et simulation Monte Carlo
- [x] Moteur de simulation stochastique vectorisé ($100\,000$ tirages NumPy) autorisant des lois normales, uniformes et triangulaires (`backend/monte_carlo.py`).
- [x] Évaluation prédictive du taux de rebut réel en PPM (parties par million) et des indices statistiques.
- [x] Histogramme de dispersion avec bornes de tolérance interactives.
- [x] Tests unitaires automatisés (`tests/test_monte_carlo.py`).

---

## 🟣 Phase 4 : Certification documentaire et traçabilité

L'objectif de cette phase est d'ancrer l'outil dans les procédures qualité formelles et les revues de conception.

### 4.1 — Gestion locale et confidentialité stricte (*Privacy-First*)
- [x] Format de fichier de sauvegarde `.cotastack` (JSON local) sans transit sur base de données distante (`backend/project_io.py`).
- [x] Importation par téléversement direct et glisser-déposer pour rechargement immédiat du projet.
- [x] Export et téléchargement en un clic de l'état complet.
- [x] Tests unitaires de sérialisation et tolérance aux formats corrompus (`tests/test_reports_and_io.py`).

### 4.2 — Générateur de rapports de calcul normés en PDF
- [x] Module d'exportation A4 normé vectorisé via ReportLab (`backend/report_generator.py`).
- [x] Cartouche d'ingénierie, tableau complet des cotes et tolérances, bilans thermiques, statistiques de dispersion et verdict Go / No-Go horodaté.
- [x] Tests unitaires de génération du document binaire (`tests/test_reports_and_io.py`).

### 4.3 — Surcouche visuelle d'annotation sur plan 2D
- [ ] Import d'image de plan (PNG, SVG, PDF).
- [ ] Dessin guidé des vecteurs sur le plan pour archivage et soutenance en revue de conception.
