# CotaStack — Agent Instructions

## Project Overview
Streamlit web app for 1D mechanical tolerance chain analysis (Worst-Case & RSS, Thermal Expansion, Monte Carlo, ISO Standards, PDF Reports). Pure Python backend + Streamlit frontend.

## Structure
```
CotaStack/
├── backend/                  # Core engineering logic
│   ├── models.py             # Item, ChainResult dataclasses
│   ├── calculator.py         # ChainCalculator: WC, RSS, Pareto, Compliance
│   ├── iso_standards.py      # ISO 286-1/2, ISO 2768-1 lookup & fit calculations
│   ├── thermal.py            # Differential thermal expansion (alpha, delta_T, J(T))
│   ├── monte_carlo.py        # Stochastic simulation engine (100k runs, distributions, PPM)
│   ├── tolerance_synthesis.py# Inverse tolerance allocation (cost, proportional, ISO)
│   ├── project_io.py         # .cotastack JSON format save & load (privacy-first)
│   └── report_generator.py   # Vectorized A4 PDF calculation report (ReportLab)
├── app.py                    # Streamlit entry point (multipage)
├── pages/                    # Streamlit pages
│   ├── 01_Calculateur.py     # 1D tolerance chain calculator, thermal & Monte Carlo tabs
│   ├── 02_Standards_ISO.py   # ISO 286 fits and ISO 2768 tolerances explorer
│   └── 03_Rapports.py        # Official A4 PDF reports, CSV and Markdown exports
├── tests/                    # pytest suite (100% backend coverage target)
│   ├── test_calculator.py    # Item and ChainCalculator tests
│   ├── test_iso_standards.py # ISO 286 and 2768-1 tests
│   ├── test_thermal.py       # Thermal expansion tests
│   ├── test_monte_carlo.py   # Monte Carlo simulation tests
│   ├── test_tolerance_synthesis.py # Inverse allocation tests
│   └── test_reports_and_io.py# .cotastack IO & PDF generator tests
├── landing/                  # Static redirection & portal page
└── .streamlit/config.toml    # Theme & server config
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
- Thermal expansion: standard ISO 1 reference temperature is 20.0 °C
- Monte Carlo: vectorized with NumPy, standard run is 100,000 iterations

## Testing
- Tests in `tests/test_calculator.py`, `tests/test_iso_standards.py`, `tests/test_thermal.py`, `tests/test_monte_carlo.py`, `tests/test_reports_and_io.py`
- Uses `approx_equal` helper for float comparisons
- Target: 100% test coverage on backend modules

## Development Notes
- Streamlit config: headless=true, custom theme (primaryColor=#0284c7)
- Pages use `st.set_page_config` with wide layout

## Language
- All conversations must be in French
