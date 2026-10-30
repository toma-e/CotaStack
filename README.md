# CotaStack

[![Python](https://img.shields.io/badge/Python-≥3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-≥1.39-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Pytest](https://img.shields.io/badge/Tests-118%20passed%20(100%25%20coverage)-00D26A?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-Source--Available-0284c7.svg)](LICENSE)

**CotaStack** est une application web d'ingénierie mécanique dédiée au calcul, à l'analyse et à l'optimisation des chaînes de cotes 1D (empilements de tolérances). Conçue pour les bureaux d'études, projeteurs et ingénieurs méthodes, elle remplace avantageusement les tableurs manuels fragiles en apportant rigueur mathématique, intégration des normes ISO et propagation instantanée sur les assemblages complexes.

---

## ✨ Fonctionnalités clés

- **Calcul déterministe & statistique 1D** :
  - **Pire des cas (Worst-Case / WC)** : garantie absolue d'assemblabilité aux limites extrêmes.
  - **Statistique quadratique (RSS à $3\sigma$)** : tolérancement probabiliste pour production de série.
  - **Diagramme de Pareto interactif** : identification immédiate des cotes générant l'essentiel de la dispersion.
  - **Contrôle de conformité Go / No-Go** en regard des jeux fonctionnels cibles $[J_{\min}, J_{\max}]$.
- **🏢 Répertoire unifié multi-chaînes (Jalon 3.1)** :
  - Définition unique des pièces et cotes sources dans un catalogue centralisé.
  - Instanciation d'une même cote physique dans plusieurs chaînes d'assemblage distinctes avec coefficients vectoriels ($\pm 1$).
  - **Propagation instantanée** : la modification d'une seule cote recalcule et réévalue instantanément la conformité de l'ensemble du système mécanique.
  - Matrice d'impact croisé et synthèse globale de conformité.
- **Ⓜ Tolérancement géométrique ISO GPS & ASME Y14.5** :
  - Spécifications de localisation, parallélisme et battement.
  - Calcul automatique de l'état au maximum de matière (MMS), du minimum de matière (LMS) et de l'état virtuel ($V_c$).
  - **Bonus dimensionnel au maximum de matière (MMR / Ⓜ)** exploitable dans la chaîne 1D.
- **🌡 Dilatation thermique différentielle ($\Delta T$)** :
  - Catalogue intégré des matériaux industriels (aciers, inox, alliages d'aluminium, laiton, POM/polymères) avec coefficients $\alpha$.
  - Comparatif jeu à froid ($20^\circ\text{C}$ ISO 1) vs jeu de fonctionnement à chaud.
  - Courbe de sensibilité continue $J(T)$ sur la plage de température.
- **🎲 Simulation stochastique Monte Carlo** :
  - Moteur vectorisé NumPy ($100\,000$ itérations par run).
  - Prise en charge des distributions **Normale**, **Uniforme** et **Triangulaire** par composant.
  - Histogramme interactif avec bornes cibles et calcul du risque de rebut en **PPM (Parties Par Million)**.
- **⚖️ Synthèse et allocation inverse de tolérances** :
  - Répartition automatique d'un jeu cible global sur les maillons selon 3 méthodes : proportionnelle, par minimisation de coût d'usinage (pondération des procédés), ou par échelonnement ISO (formule $i = 0{,}45 \sqrt[3]{D} + 0{,}001 D$).
- **🔒 Confidentialité locale (*Privacy-First*) & Rapports normés** :
  - Sauvegarde et chargement de projet au format standard `.cotastack` (JSON local, aucun transit sur serveur externe).
  - Générateur de **rapports PDF A4 vectorisés** (ReportLab) avec cartouche officiel, tableau des cotes, bilans thermiques, statistiques et verdict d'assemblage.

---

## 🏗 Architecture du projet

```
CotaStack/
├── backend/                      # Moteur d'ingénierie métier (pur Python, typé, 100% testé)
│   ├── __init__.py
│   ├── models.py                 # Dataclasses structurelles : Item, ChainResult, MaterialInfo
│   ├── calculator.py             # Moteur WC, RSS, Pareto et conformité
│   ├── iso_standards.py          # Tables d'ajustements ISO 286 et tolérances ISO 2768-1
│   ├── geometric_tolerances.py    # ISO GPS : MMS, LMS, Vc, bonus MMR Ⓜ et interfaces
│   ├── multi_chain.py            # Répertoire multi-chaînes unifié, liaisons et propagation
│   ├── thermal.py                # Dilatation thermique différentielle et sensibilité J(T)
│   ├── monte_carlo.py            # Simulation Monte Carlo (100k runs, lois, PPM)
│   ├── tolerance_synthesis.py    # Allocation inverse (coûts, proportionnelle, ISO)
│   ├── project_io.py             # Format .cotastack JSON (export/import local sécurisé)
│   └── report_generator.py       # Génération de rapports PDF A4 normés (ReportLab)
├── pages/                        # Interface utilisateur Streamlit
│   ├── 01_Calculateur.py         # Calculateur 1D, onglets Thermique & Monte Carlo
│   ├── 02_Standards_ISO.py       # Explorateur ISO 286, ISO 2768 et ISO GPS Ⓜ
│   ├── 03_Rapports.py            # Générateur de rapports officiels (PDF, CSV, Markdown)
│   └── 04_Multi_Chaines.py       # Répertoire multi-chaînes système et matrice d'impact
├── tests/                        # Suite de tests automatisés pytest (118 tests)
│   ├── __init__.py
│   ├── test_calculator.py        # Validation modèles et formules WC / RSS / Pareto
│   ├── test_iso_standards.py     # Contrôle des écarts ISO 286 et ISO 2768
│   ├── test_geometric_tolerances.py # Tests ISO GPS, états virtuels et bonus MMR
│   ├── test_multi_chain.py       # Tests du catalogue, propagation et persistance multi-chaînes
│   ├── test_thermal.py           # Tests de dilatation thermique différentielle
│   ├── test_monte_carlo.py       # Tests de simulation stochastique et lois statistiques
│   ├── test_tolerance_synthesis.py # Tests d'allocation inverse de tolérances
│   └── test_reports_and_io.py    # Tests sérialisation .cotastack et génération PDF
├── landing/                      # Page portail statique & redirection web
│   └── index.html
├── .streamlit/                   # Configuration du thème et du serveur Streamlit
│   └── config.toml
├── app.py                        # Point d'entrée de l'application Streamlit
├── requirements.txt              # Dépendances Python du projet
├── LICENSE                       # Licence Source-Available & Non-Commercial Code
└── README.md
```

---

## 🚀 Installation & Lancement local

### Prérequis
- **Python ≥ 3.11**
- Gestionnaire de paquets : [`uv`](https://github.com/astral-sh/uv) (recommandé) ou `venv` + `pip`

### Avec `uv` (recommandé)
```bash
# Cloner le dépôt
git clone https://github.com/toma-e/CotaStack.git
cd CotaStack

# Création de l'environnement virtuel et installation
uv venv
uv pip install -r requirements.txt

# Lancement de l'application
uv run streamlit run app.py
```

### Avec `venv` + `pip`
```bash
# Création de l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate  # Sur Linux/macOS
# .venv\Scripts\activate   # Sur Windows

# Installation des dépendances
pip install -r requirements.txt

# Lancement
streamlit run app.py
```

L'application est immédiatement accessible dans votre navigateur à l'adresse : `http://localhost:8501`.

---

## 🧪 Tests & Qualité de code

La totalité du backend d'ingénierie est couverte par une suite de tests unitaires et d'intégration automatisés avec un objectif maintenu de **100 % de couverture de code**.

```bash
# Exécution de la suite complète des tests (118 tests)
.venv/bin/pytest -v

# Vérification du rapport de couverture de code
.venv/bin/pytest --cov=backend --cov-report=term-missing
```

---

## 📦 Dépendances principales

| Paquet | Version | Rôle dans l'architecture |
|--------|---------|--------------------------|
| `streamlit` | ≥ 1.39.0 | Interface web réactive multipage et composants interactifs |
| `pandas` | ≥ 2.0.0 | Manipulation des tableaux de cotes et matrices d'impact |
| `numpy` | ≥ 1.24.0 | Calcul matriciel et moteur stochastique vectorisé Monte Carlo |
| `scipy` | ≥ 1.13.0 | Fonctions statistiques pour lois normales et distributions continues |
| `plotly` | ≥ 5.18.0 | Tracés graphiques interactifs (Pareto, distributions, courbes thermiques) |
| `reportlab` | ≥ 4.0.0 | Moteur de génération des rapports de calcul PDF A4 vectorisés |
| `Pillow` | ≥ 10.0.0 | Traitement et insertion d'images / logos dans les exports |
| `pytest` | ≥ 8.0.0 | Framework d'exécution des tests automatisés |
| `pytest-cov` | ≥ 4.0.0 | Analyse et contrôle de la couverture de test du code |

---

## 🗺 État d'avancement & Feuille de route

Consultez le document détaillé [**`ROADMAP.md`**](ROADMAP.md) pour le suivi technique complet.

- [x] **Phase 1 : Cœur 1D déterministe & statistique** (Modèles, calculs WC/RSS, Pareto, conformité, tests unitaires).
- [x] **Phase 2 : Référentiel normatif d'atelier** (Ajustements ISO 286, tolérances ISO 2768-1, exports CSV/Markdown).
- [x] **Phase 3 : Modules avancés à haute valeur ajoutée** :
  - [x] Répertoire unifié multi-chaînes avec propagation instantanée (Jalon 3.1).
  - [x] Allocation inverse et synthèse de tolérances par coût et normes (Jalon 3.2).
  - [x] Compensation des dilatations thermiques différentielles (Jalon 3.3).
  - [x] Convertisseur 1D ISO GPS avec bonus au maximum de matière Ⓜ (Jalon 3.4).
  - [x] Moteur stochastique Monte Carlo (100 000 itérations, estimation PPM) (Jalon 3.5).
- [x] **Phase 4.1 & 4.2 : Traçabilité & Confidentialité** :
  - [x] Format local sécurisé `.cotastack` JSON (*Privacy-First*).
  - [x] Générateur de rapports PDF normés d'ingénierie.
- [ ] **Phase 4.3 : Surcouche visuelle d'annotation sur plan 2D** (à venir).

---

## 📄 Licence

Ce projet est distribué sous la licence [**CotaStack Source-Available & Non-Commercial Code License**](LICENSE).

- **Utilisation interne autorisée** : Toute personne ou entreprise (y compris commerciale, bureaux d'études, industriels) peut utiliser librement l'application dans le cadre de ses activités professionnelles internes et exploiter/diffuser les rapports techniques et résultats de calcul produits.
- **Restrictions commerciales sur le code** : La revente, la sous-licence, l'hébergement en service commercial payant (SaaS) ou l'incorporation directe du code source dans des produits commerciaux tiers est strictement interdite sans autorisation écrite préalable.
- **Clause de non-responsabilité technique** : Le logiciel est fourni « tel quel » sans garantie d'exactitude absolue. Tout calcul ou tolérancement doit être validé par un ingénieur qualifié avant mise en fabrication. Les auteurs déclinent toute responsabilité en cas de rebut, d'interférence d'assemblage ou de dommages directs ou indirects.

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Merci d'ouvrir une issue ou une PR pour proposer des améliorations :

```bash
git checkout -b feature/ma-fonctionnalite
# Développement + tests (maintien impératif du 100% de couverture)
pytest -v --cov=backend
git commit -m "feat: description concise"
git push origin feature/ma-fonctionnalite
```

---

## 📬 Contact

- **Email** : contact@cotastack.app
- **GitHub** : [github.com/toma-e/CotaStack](https://github.com/toma-e/CotaStack)
