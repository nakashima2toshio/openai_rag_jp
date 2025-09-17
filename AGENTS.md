# Repository Guidelines

## Project Structure & Module Organization
- Root scripts: `a01_load_set_rag_data.py`, `a02_set_vector_store_vsid.py`, `a03_rag_search_cloud_vs.py`, `a50_rag_search_local_qdrant.py`, `server.py`
- Helpers: `helper_api.py`, `helper_rag.py`, `helper_st.py`
- Data: `datasets/` (raw), `OUTPUT/` (processed)
- Docker: `docker-compose/`
- Docs: `doc/` and `README*.md`
- Config: `.env`, `config.yml`

Naming patterns
- Task scripts: `aNN_*` (e.g., `a01_...`, `a50_...`)
- Helpers: `helper_*.py`
- Docs: `doc/<topic>.md`

## Build, Test, and Development Commands
- Setup env: `python -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Lint/format: `ruff check . --fix` and `ruff format .`
- Run API/server: `python server.py`
- Data prep UI: `streamlit run a01_load_set_rag_data.py`
- Cloud RAG UI: `streamlit run a03_rag_search_cloud_vs.py`
- Local Qdrant (Docker): `cd docker-compose && docker-compose up -d`
- Local RAG UI: `streamlit run a50_rag_search_local_qdrant.py`

## Coding Style & Naming Conventions
- Python 3.12+; 4‑space indentation; UTF-8; Unix newlines.
- Use type hints in new/modified functions; keep functions focused.
- Prefer pure helpers in `helper_*.py`; keep scripts thin.
- Docstrings: describe purpose, inputs, outputs, and side effects.

## Testing Guidelines
- No formal suite yet. If adding tests, use `pytest` and place files under `tests/` named `test_*.py`.
- Mock network/DB (OpenAI, Qdrant) in unit tests; focus on `helper_*.py` logic.
- Manual checks: run the Streamlit apps and `server.py` with representative configs.

## Commit & Pull Request Guidelines
- Commit messages commonly include date tags (e.g., `2025-0907-1`). Keep this style and add a short, present‑tense scope: `a50: improve Qdrant recreation`.
- PRs must include: summary, rationale, affected modules/scripts, manual test steps, and screenshots/GIFs for Streamlit UI changes.
- Link related issues. Note config changes (`config.yml`, `.env` keys) and any data migrations.

## Security & Configuration Tips
- Do not commit secrets. Store keys in `.env` (e.g., `OPENAI_API_KEY`) and load via `python-dotenv`.
- Review `config.yml` changes carefully (models, Qdrant URL/collection, limits).
- For local vector DB, prefer `docker-compose/` and document ports/collections in PRs.

