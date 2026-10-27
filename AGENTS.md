# CotaStack — Agent Instructions

## Project Overview
Streamlit web app for 1D mechanical tolerance chain analysis (Worst-Case & RSS). Pure Python backend + Streamlit frontend.

## Structure
```
CotaStack/
├── backend/          # Core logic (models, calculator, ISO standards)
│   ├── models.py     # Item, ChainResult dataclasses
│   ├── calculator.py # ChainCalculator: WC & RSS
│   └── iso_standards.py # ISO 286, ISO 2768-1 lookup tables
├── app.py            # Streamlit entry point (multipage)
├── pages/            # Streamlit pages (to be created)
├── tests/            # pytest suite
├── landing/          # Static marketing page
└── .streamlit/config.toml # Theme & server config
```

## Commands
| Action | Command |
|--------|---------|
| Install deps | `uv pip install -r requirements.txt` (or `pip install -r requirements.txt`) |
| Run app | `streamlit run app.py` (or `uv run streamlit run app.py`) |
| Run tests | `pytest -v` |
| Tests + coverage | `pytest --cov=backend --cov-report=term-missing` |

## Key Conventions
- **Python ≥ 3.11**, `uv` recommended for venv management
- Virtual env at `.venv/` (already exists)
- Backend is importable as `from backend.models import Item`
- Item validation: `tolerance_minus <= 0`, `tolerance_plus >= 0`, `nominal >= 0`
- Direction field exists on Item but not yet used in calculations
- ISO standards module uses simplified lookup tables (µm for ISO 286, mm for ISO 2768-1)

## Testing
- Tests in `tests/test_calculator.py` cover models, calculator, edge cases
- Uses `approx_equal` helper for float comparisons (rel_tol=1e-9)
- Run single test: `pytest tests/test_calculator.py::TestChainCalculator::test_calculate_worst_case -v`

## Development Notes
- Pages directory doesn't exist yet — create when adding Streamlit multipage routes
- Streamlit config: headless=true, custom theme (primaryColor=#0284c7)
- No lint/typecheck configured yet (add ruff/mypy if needed)
- No CI/CD pipeline configured

## Language
- All conversations must be in French