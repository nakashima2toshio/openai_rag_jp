# Repository Guidelines

## プロジェクト構成とモジュール配置
- ルート実行スクリプト: `a01_load_set_rag_data.py`, `a02_set_vector_store_vsid.py`, `a03_rag_search_cloud_vs.py`, `a50_rag_search_local_qdrant.py`, `server.py`
- ヘルパー: `helper_api.py`, `helper_rag.py`, `helper_st.py`
- データ: `datasets/`（生データ）, `OUTPUT/`（処理済み）
- Docker: `docker-compose/`
- ドキュメント: `doc/`, `README*.md`
- 設定: `.env`, `config.yml`

命名パターン
- タスク系: `aNN_*`（例: `a01_...`, `a50_...`）
- ヘルパー: `helper_*.py`
- ドキュメント: `doc/<topic>.md`

## ビルド・テスト・開発コマンド
- 仮想環境: `python -m venv .venv && source .venv/bin/activate`
- 依存導入: `pip install -r requirements.txt`
- Lint/Format: `ruff check . --fix` / `ruff format .`
- API/サーバー: `python server.py`
- データ準備UI: `streamlit run a01_load_set_rag_data.py`
- クラウド検索UI: `streamlit run a03_rag_search_cloud_vs.py`
- Qdrant 起動: `cd docker-compose && docker-compose up -d`
- ローカル検索UI: `streamlit run a50_rag_search_local_qdrant.py`

## コーディング規約・命名規則
- Python 3.12+、インデント4スペース、UTF-8、LF改行。
- 新規/変更関数は型ヒント必須。関数は単一責務で短く。
- 共通ロジックは `helper_*.py` に集約し、実行スクリプトは薄く。
- 公開関数/スクリプトには目的・入出力・副作用のDocstring。

## テストガイドライン
- 公式スイート未整備。追加する場合は `pytest` を使用し、`tests/` に `test_*.py` で配置。
- ネットワーク/DB（OpenAI, Qdrant）はモック化。`helper_*.py` のロジックを重点的に単体テスト。
- 手動確認: 上記Streamlit UIと `server.py` を代表設定で動作確認。

## コミット／プルリクエスト
- コミットは日付タグ（例: `2025-0907-1`）＋短い現在形スコープ（例: `a50: improve qdrant recreation`）。
- PR には概要、背景、影響箇所、手動テスト手順、Streamlit変更のスクショ/GIF。
- `config.yml` や `.env` キー変更は明記し、移行手順を添付。

## セキュリティ／設定の注意
- 秘密情報はコミット禁止。`.env` に保存し `python-dotenv` でロード。
- `config.yml` のモデル/Qdrant URL/コレクション/制限値の差分を慎重にレビュー。
- ローカルDBは `docker-compose/` の設定を優先。ポート/コレクションをPRで明記。

