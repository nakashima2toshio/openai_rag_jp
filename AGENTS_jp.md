# Repository Guidelines（日本語版）

この文書は `AGENTS.md` の日本語版です。内容差異が生じた場合は `AGENTS.md` を正とし、速やかに同期してください。

## プロジェクト構成とモジュール
- ルートスクリプト: `a01_load_set_rag_data.py`, `a02_set_vector_store_vsid.py`, `a03_rag_search_cloud_vs.py`, `a50_rag_search_local_qdrant.py`, `server.py`。
- ヘルパー: `helper_api.py`, `helper_rag.py`, `helper_st.py`（コア処理はここに集約。スクリプトは薄く）。
- データ: `datasets/`（生データ）→ `OUTPUT/`（前処理後）。
- Docker: ローカル Qdrant 用 `docker-compose/`。
- ドキュメント: `doc/`, `README*.md`。設定: `.env`, `config.yml`。
- 命名: タスク `aNN_*`、ヘルパー `helper_*.py`、ドキュメント `doc/<topic>.md`。

## ビルド・テスト・開発コマンド
- 仮想環境＋依存関係: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`。
- Lint/整形: `ruff check . --fix` と `ruff format .`。
- API/サーバー起動: `python server.py`。
- Streamlit UI: `streamlit run a01_load_set_rag_data.py`、`streamlit run a03_rag_search_cloud_vs.py`、`streamlit run a50_rag_search_local_qdrant.py`。
- ローカル Qdrant (Docker): `cd docker-compose && docker-compose up -d`。

## コーディング規約と命名
- Python 3.12+、4スペースインデント、UTF‑8、LF 改行。
- 型ヒントを使用し、小さく目的指向の関数に分割。
- ピュア処理は `helper_*.py` に置き、スクリプトはI/OやUIの指揮に限定。
- Docstring: 目的・入力・出力・副作用を明記。
- 設定は `.env`/`config.yml` に集約し、ハードコードしない。

## テスト方針
- フレームワーク: `pytest`。`tests/` 配下に `test_*.py` を配置。
- ネットワーク/DB（OpenAI, Qdrant）はモック。ヘルパーのロジック中心に検証。
- 実行: `pytest -q`。`server.py` と各 Streamlit アプリで代表的な設定を用いた手動確認も行う。

## コミットとプルリクエスト
- コミット: 日付タグ＋短いスコープ。例: `2025-0907-1 a50: improve Qdrant recreation`。
- PR: 概要、背景/目的、影響範囲（対象モジュール/スクリプト）、手動テスト手順。Streamlit のUI変更はスクリーンショット/GIFを添付。
- 関連Issueをリンク。`config.yml`/`.env` のキー変更やデータ移行（ポート/コレクション）も明記。

## セキュリティと設定のヒント
- 秘密情報はコミットしない。`python-dotenv` で `.env` から読み込む（例: `OPENAI_API_KEY`）。
- `config.yml` の変更は要レビュー（モデル、Qdrant URL/コレクション、リミット）。
- ローカルのベクタDBは `docker-compose/` を推奨。ポート/コレクションはPRで明記。

