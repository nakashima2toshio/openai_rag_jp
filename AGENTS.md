# Repository Guidelines

## Project Structure & Module Organization
- Root scripts: `a01_load_set_rag_data.py`, `a02_set_vector_store_vsid.py`, `a03_rag_search_cloud_vs.py`, `a50_rag_search_local_qdrant.py`, `server.py`.
- Helpers: `helper_api.py`, `helper_rag.py`, `helper_st.py` (put core logic here; keep scripts thin).
- Data: `datasets/` (raw) → `OUTPUT/` (processed).
- Docker: `docker-compose/` for local Qdrant.
- Docs: `doc/`, `README*.md`. Config: `.env`, `config.yml`.
- Naming: tasks `aNN_*`, helpers `helper_*.py`, docs `doc/<topic>.md`.

## Build, Test, and Development Commands
- Create env & install: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Lint/format: `ruff check . --fix` and `ruff format .`.
- Run API/server: `python server.py`.
- Streamlit UIs: `streamlit run a01_load_set_rag_data.py`, `streamlit run a03_rag_search_cloud_vs.py`, `streamlit run a50_rag_search_local_qdrant.py`.
- Local Qdrant (Docker): `cd docker-compose && docker-compose up -d`.

## Coding Style & Naming Conventions
- Python 3.12+, 4‑space indent, UTF‑8, Unix newlines.
- Use type hints; keep functions small and purposeful.
- Prefer pure helpers in `helper_*.py`; scripts orchestrate I/O and UI.
- Docstrings: purpose, inputs, outputs, side effects.
- Keep config in `.env`/`config.yml`; avoid hard‑coding.

## Testing Guidelines
- Framework: `pytest`. Place tests under `tests/` named `test_*.py`.
- Mock network/DB calls (OpenAI, Qdrant); focus on helper logic.
- Run: `pytest -q`. Also do manual checks via Streamlit apps and `server.py` with representative configs.

## Commit & Pull Request Guidelines
- Commits: include date tag and short scope, e.g., `2025-0907-1 a50: improve Qdrant recreation`.
- PRs: provide summary, rationale, affected modules/scripts, manual test steps; include screenshots/GIFs for Streamlit UI changes.
- Link related issues; note changes to `config.yml`/`.env` and any data migrations (ports, collections).

## Security & Configuration Tips
- Never commit secrets; load via `.env` (e.g., `OPENAI_API_KEY`) using `python-dotenv`.
- Review `config.yml` changes carefully (models, Qdrant URL/collection, limits).
- Prefer `docker-compose/` for local vector DB; document ports/collections in PRs.

