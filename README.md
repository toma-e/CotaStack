# CotaStack

**CotaStack** est une application web open-source de calcul et d'analyse de tolérancement mécanique 1D (chaînes de cotes). Elle permet aux ingénieurs et projeteurs de sécuriser leurs empilements de tolérances via deux méthodes de calcul : **Pire des cas (Worst-Case)** et **RSS (Root Sum Square / statistique quadratique)**.

L'outil génère des notes de calcul normées (PDF), intègre les standards ISO 286 et ISO 2768-1, et propose un tracé graphique vectoriel interactif pour valider visuellement la fermeture de boucle.

---

## 🏗 Architecture du projet

```
CotaStack/
├── landing/                 # Landing page marketing (HTML statique)
│   └── index.html
├── backend/                 # Logique métier pure (calculs, modèles, standards)
│   ├── __init__.py
│   ├── models.py           # Dataclasses: Item, ChainResult
│   ├── calculator.py       # ChainCalculator: WC & RSS
│   └── iso_standards.py    # Tables ISO 286, ISO 2768-1
├── app.py                  # Point d'entrée Streamlit (page d'accueil)
├── pages/                  # Pages Streamlit multipage (à créer)
│   ├── 01_Calculateur.py
│   ├── 02_Standards_ISO.py
│   └── 03_Rapports.py
├── tests/                  # Suite de tests pytest
│   ├── __init__.py
│   └── test_calculator.py
├── .streamlit/
│   └── config.toml         # Thème & config Streamlit
├── requirements.txt        # Dépendances Python
├── .gitignore
└── README.md
```

---

## 🚀 Installation & Lancement local

### Prérequis
- Python ≥ 3.11
- `uv` (recommandé) ou `venv` + `pip`

### Avec `uv` (recommandé — rapide & reproductible)
```bash
# Création de l'environnement virtuel
uv venv

# Installation des dépendances
uv pip install -r requirements.txt

# Lancement de l'application Streamlit
uv run streamlit run app.py
```

### Avec `venv` + `pip` (standard)
```bash
# Création de l'environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Installation des dépendances
pip install -r requirements.txt

# Lancement
streamlit run app.py
```

L'application s'ouvre sur `http://localhost:8501`.

---

## 🧪 Tests

```bash
# Exécution de la suite de tests
pytest -v

# Avec couverture de code
pytest --cov=backend --cov-report=term-missing
```

---

## 📦 Dépendances principales

| Paquet | Version | Rôle |
|--------|---------|------|
| `streamlit` | ≥ 1.39.0 | Framework web UI |
| `pandas` | ≥ 2.0.0 | Manipulation données / tableaux |
| `numpy` | ≥ 1.24.0 | Calcul numérique |
| `plotly` | ≥ 5.18.0 | Graphiques interactifs (SVG/WebGL) |
| `Pillow` | ≥ 10.0.0 | Génération d'images / PDF |
| `pytest` | ≥ 8.0.0 | Framework de tests |

---

## 🗺 Feuille de route (prochaines étapes)

1. **Calculateur interactif** — Saisie de maillons, tracé vectoriel Plotly, résultats WC/RSS en temps réel
2. **Module ISO** — Sélecteurs d'ajustements (ISO 286) et tolérances générales (ISO 2768-1) avec pré-remplissage
3. **Dilatation thermique** — Matériaux (acier, alu, polymères), ΔT, calcul de ΔL
4. **Export PDF** — Note de calcul normée (Go/No-Go, tableau maillons, tracé, métadonnées)
5. **Persistance** — Sauvegarde/chargement projets (JSON local puis base de données)
6. **Authentification & multi-utilisateurs** — Pour version SaaS

---

## 📄 Licence

Projet en cours de définition — à déterminer (MIT / Apache 2.0 / Propriétaire selon stratégie).

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Merci d'ouvrir une issue ou une PR pour discuter des changements.

```bash
# Workflow suggéré
git checkout -b feature/ma-fonctionnalite
# ... modifications + tests ...
pytest -v
git commit -m "feat: description claire"
git push origin feature/ma-fonctionnalite
# Ouvrir une Pull Request
```

---

## 📬 Contact

- **Email** : contact@cotastack.app
- **GitHub** : [github.com/cotastack](https://github.com/cotastack)
- **Landing page** : `landing/index.html` (à déployer sur GitHub Pages / Netlify / Vercel)

---

## 📄 Licence

Ce projet est distribué sous la licence [**CotaStack Source-Available & Non-Commercial Code License**](LICENSE).

- **Utilisation interne autorisée** : Toute personne ou entreprise (y compris commerciale, bureaux d'études, industriels) peut utiliser librement l'application dans le cadre de ses activités professionnelles internes et exploiter/diffuser les rapports techniques et résultats de calcul produits.
- **Restrictions commerciales sur le code** : La revente, la sous-licence, l'hébergement en service commercial payant (SaaS) ou l'incorporation directe du code source dans des produits commerciaux tiers est strictement interdite sans autorisation écrite préalable.
- **Clause de non-responsabilité technique** : Le logiciel est fourni « tel quel » sans garantie d'exactitude absolue. Tout calcul ou tolérancement doit être validé par un ingénieur qualifié avant mise en fabrication. Les auteurs déclinent toute responsabilité en cas de rebut, d'interférence d'assemblage ou de dommages directs ou indirects.
