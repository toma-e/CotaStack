# Feuille de route & Plan de développement — CotaStack

Document de référence pour le déploiement incrémental de CotaStack.  
Chaque étape doit faire l'objet de tests unitaires ou de recette fonctionnelle avant de passer à la suivante.

---

## 🟢 Phase 1 : Le cœur 1D minimal (MVP & Moteur Héro)

L'objectif est d'obtenir le premier livrable fonctionnel : le calcul d'empilement 1D en pire des cas et statistique.

### 1.1 — Moteur mathématique pur & Modèle de données (Backend)
- [ ] **Modélisation (`backend/models.py`)** :
  - Dataclass `Item` : repère (`id`, `name`), orientation (`+` ou `-`), valeur nominale, écart supérieur (`es`), écart inférieur (`ei`).
  - Validation stricte dès l'instanciation : lever `ValueError` si $ES < EI$.
  - Propriétés dérivées : Intervalle de Tolérance ($IT = ES - EI$), cote moyenne ($Nominal + \frac{ES + EI}{2}$).
- [ ] **Moteur de calcul (`backend/calculator.py`)** :
  - Classe `ChainCalculator(items, target_min=None, target_max=None)`.
  - Calcul du jeu nominal et du jeu moyen.
  - Calcul Pire des Cas (Worst Case — WC) : Min, Max, IT total.
  - Calcul Statistique (Root Sum Squares — RSS à $3\sigma$) : Min, Max, IT quadratique.
  - Analyse de contribution de Pareto (% de variance par maillon).
  - Évaluation de conformité booléenne vis-à-vis des bornes cibles ($J_{\min \text{ cible}}$, $J_{\max \text{ cible}}$).
- [ ] **Tests unitaires (`tests/test_calculator.py`)** :
  - Validation des formules WC et RSS sur un cas de référence connu (3 cotes avec alternance de signes).
  - Validation de la levée d'exception si $ES < EI$.
  - Validation du calcul de sensibilité de Pareto (somme des contributions = 100 %).

### 1.2 — Interface de saisie & Synthèse (Frontend)
- [ ] **Structure UI (`app.py`)** :
  - Tableau interactif éditable (`st.data_editor`) avec colonnes typées et lignes dynamiques.
  - Définition optionnelle des cibles fonctionnelles (Jeu Min / Jeu Max).
  - Cartes métriques réactives : Jeu Nominal, WC (Min/Max), RSS (Min/Max), IT.
  - Badges de conformité visuelle (Go / No-Go).
  - Clause de non-responsabilité technique sous les résultats et footer Privacy-First.
- [ ] **Recette fonctionnelle** :
  - Modification dynamique d'un signe ou d'une tolérance à l'écran : vérification de la réactivité sans latence ni perte d'état.

### 1.3 — Restitution graphique Plotly
- [ ] **Visualisation (`app.py`)** :
  - Diagramme en barres horizontales pour le tri de Pareto (identification immédiate de la cote la plus pénalisante).
  - Graphique d'intervalle ou courbe de distribution normale avec matérialisation des bornes cibles.
- [ ] **Recette fonctionnelle** :
  - Vérification de l'adaptation dynamique des graphiques lors de l'ajout/suppression de lignes.

---

## 🔵 Phase 2 : Enrichissement normatif et ergonomie rapide

Intégration des standards d'atelier sans modifier le socle d'architecture.

### 2.1 — Tolérances générales ISO 2768-1
- [ ] **Backend (`backend/iso_standards.py`)** :
  - Tables de tolérances par classe de précision (*f*, *m*, *c*, *v*) sur les plages dimensionnelles ($]0, 3]$, $]3, 6]$, ..., $]400, 1000]$ mm).
  - Fonction de lookup `get_iso2768_tolerance(nominal, precision_class) -> float`.
- [ ] **UI** : Sélecteur de classe générale pour pré-remplir les cotes sans tolérance spécifique.
- [ ] **Tests** : Validation aux bornes des intervalles dimensionnels.

### 2.2 — Module autonome "Ajustements ISO 286"
- [ ] **Backend (`backend/iso_standards.py`)** :
  - Tables d'écarts pour alésages et arbres usuels (H7, H8, H11, g6, f7, h6, js6, p6).
  - Fonction `get_iso286_limits(nominal, symbol) -> tuple[float, float]`.
- [ ] **UI** :
  - Onglet ou vue dédiée au calcul rapide d'un ajustement isolé (Jeu / Serrage / Incertain).
  - Option de pré-remplissage direct d'un maillon de la chaîne à partir d'un symbole ISO.
- [ ] **Tests** : Contrôle d'exactitude des valeurs $ES/EI$ face aux tables officielles du Cetim / ISO 286.

### 2.3 — Exports légers
- [ ] **Téléchargement CSV** : Bouton d'export des données tabulaires formatées en UTF-8.
- [ ] **Résumé Texte/Markdown** : Génération d'une synthèse textuelle prête à copier dans un e-mail ou un compte-rendu.

---

## 🟡 Phase 3 : Fonctions avancées de calcul et reporting (Palier Pro)

Fonctionnalités à forte valeur ajoutée destinées à la productivité et aux dossiers techniques.

### 3.1 — Module de dilatation thermique ($\Delta T$)
- [ ] Saisie de la température de service et choix du matériau par maillon (acier, aluminium, inox, laiton).
- [ ] Recalcul dimensionnel automatique : $L(T) = L_{20^\circ\text{C}} \times [1 + \alpha \cdot (T - 20)]$.
- [ ] Tests comparatifs de jeu à froid vs jeu à chaud.

### 3.2 — Sauvegarde locale "Privacy-First"
- [ ] Export de l'état complet du projet sous fichier `.cotastack` (JSON sérialisé).
- [ ] Import/glisser-déposer d'un fichier `.cotastack` pour recharger instantanément l'étude en mémoire vive.

### 3.3 — Générateur de rapports PDF normés
- [ ] Intégration d'un moteur de rendu PDF (ReportLab ou WeasyPrint).
- [ ] Mise en page A4 : cartouche d'identification, tableau des maillons, graphiques de dispersion, verdict Go / No-Go et bloc d'approbation.

### 3.4 — Simulation Monte Carlo & Lois réelles
- [ ] Tirages aléatoires multi-distributions (loi normale avec $C_p/C_{pk}$, loi uniforme, loi triangulaire).
- [ ] Estimation du taux de rebut réel en PPM.

---

## 🧭 Suite d'outils complémentaires : Matrice de priorité

Une fois le calculateur 1D stabilisé, extension progressive de la suite CotaStack par briques modulaires :

| Priorité | Module / Outil | Rôle & Synergie avec CotaStack 1D | Complexité |
| :--- | :--- | :--- | :--- |
| **1** | **Table de Cotes Source & Impact** | Lier une cote usinée commune à plusieurs chaînes avec propagation automatique des modifications. | Moyenne |
| **2** | **Tracé vectoriel sur plan** | Import d'image de plan (PNG/JPG) avec surcouche d'annotation pour repérer visuellement les boucles. | Moyenne |
| **3** | **Convertisseur GD&T vers 1D (ISO 1101)** | Traduction des tolérances de localisation, parallélisme et modificateurs de matière (MMR/LMR) en écarts 1D. | Élevée |
| **4** | **Calculateur d'emmanchement & frettage** | Calcul des pressions de contact, efforts d'insertion et contraintes à partir des tolérances ISO 286. | Moyenne |
| **5** | **Assemblages vissés (NF E 25-030)** | Vérification des précharges, couples de serrage et jeux de passage de vis interagissant avec les empilements. | Élevée |
| **6** | **Calculateur masse, volume & inertie** | Utilitaire rapide de vérification matière/poids pour devis et dimensionnement préliminaire. | Faible |