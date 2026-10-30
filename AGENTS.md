# CotaStack — Agent Instructions

## Project Overview
Streamlit web app for 1D mechanical tolerance chain analysis (Worst-Case & RSS). Pure Python backend + Streamlit frontend.

## Structure
```
CotaStack/
├── backend/               # Core logic (models, calculator, ISO standards)
│   ├── models.py          # Item, ChainResult dataclasses
│   ├── calculator.py      # ChainCalculator: WC, RSS, Pareto, Compliance
│   └── iso_standards.py   # ISO 286-1/2, ISO 2768-1 lookup & fit calculations
├── app.py                 # Streamlit entry point (multipage)
├── pages/                 # Streamlit pages
│   ├── 01_Calculateur.py  # 1D tolerance chain calculator & visualizations
│   ├── 02_Standards_ISO.py# ISO 286 fits and ISO 2768 tolerances explorer
│   └── 03_Rapports.py     # Reports, lightweight exports (CSV, MD) & PDF
├── tests/                 # pytest suite
│   ├── test_calculator.py # Item and ChainCalculator tests
│   └── test_iso_standards.py # ISO 286 and 2768-1 tests
├── landing/               # Static marketing page
└── .streamlit/config.toml # Theme & server config
```

## Commands
| Action | Command |
|--------|---------|
| Install deps | `uv pip install -r requirements.txt` (or `.venv/bin/pip install -r requirements.txt`) |
| Run app | `uv run streamlit run app.py` (or `.venv/bin/streamlit run app.py`) |
| Run tests | `.venv/bin/pytest -v` |
| Tests + coverage | `.venv/bin/pytest --cov=backend --cov-report=term-missing` |

## Key Conventions
- **Python ≥ 3.11**, `uv` recommended for venv management
- Virtual env at `.venv/`
- Backend is importable as `from backend.models import Item`
- Item validation: `es >= ei`, `nominal >= 0`, `orientation in (1, -1)`
- Dimensions and tolerances in millimeters (mm) in models and calculator; ISO tables convert µm -> mm
- ISO standards module covers ISO 286 (fits H7/g6, etc.) and ISO 2768-1 (general linear and chamfer tolerances)

## Testing
- Tests in `tests/test_calculator.py` and `tests/test_iso_standards.py`
- Uses `approx_equal` helper for float comparisons (rel_tol=1e-9)
- Target: 100% test coverage on backend modules

## Development Notes
- Streamlit config: headless=true, custom theme (primaryColor=#0284c7)
- Pages use `st.set_page_config` with wide layout

## Language
- All conversations must be in French
