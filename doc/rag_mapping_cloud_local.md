# RAG 工程マップ（Cloud / Local 対応表）

本書は、リポジトリ内の各プログラムが **RAG 工程（1〜7）** の **どこを、どう担当しているか** にフォーカスして整理したものです。  
まず工程の凡例、つづいて **(1) Cloud 版（Vector Store）**、**(2) Local 版（Qdrant）**、最後に **共通モジュール** を記載します。

## 工程の凡例

| 番号 | 工程名 | 主な内容 |
|---|---|---|
| 1 | 前処理 | 文字コード/改行/空白/重複の整形、ノイズ除去（ナビ/フッター等）、メタデータ抽出（タイトル/URL/セクション/更新日） |
| 2 | チャンク分割 | 固定長 or 意味単位。オーバーラップ（10–20%）。日本語は文字数基準（800–1,200字＋100–200重なり）推奨。コード/表は独立チャンク |
| 3 | ベクトル化 | 各チャンクを埋め込み。必要に応じ **L2 正規化**（Cosine 類似度時） |
| 4 | インデックス化 | ベクタDBへ格納（近似最近傍）。本文・メタ・chunk_id を保存。属性フィルタ用のフィールド化 |
| 5 | 検索（クエリ側） | クエリも同じモデルで埋め込み。ベクトル検索＋（任意で）BM25、MMR、フィルタ、時間減衰、再ランキング |
| 6 | 生成 | 選抜チャンクを結合（重複/同一出典の統合）。出典メタデータ付与 |
| 7 | モニタリング/評価 | ヒット率・正確性の評価、チャンク長/オーバーラップ/モデル/閾値のチューニング |

---

# (1) Cloud 版（OpenAI Vector Store を使う）

## ファイル別マッピング（Cloud）

| プログラム | RAG 工程（どこ） | どう対応しているか | 入力 → 出力 | 備考 |
|---|---|---|---|---|
| `a01_load_set_rag_data.py` | **1 前処理**＋**2 チャンク分割** | 正規化／ノイズ除去／メタ抽出 → 文字数基準＋オーバーラップで分割 | 原文, `config_yml.yml` → `OUTPUT/processed/*.jsonl`（`{text, meta, chunk_id}`） | Cloud/Local 共用の前段 |
| `a02_set_vector_store_vsid.py` | **3 ベクトル化**＋**4 インデックス化（Cloud）** | Vector Store 作成/取得（VSID）→ a01 出力を投入。VS 側で埋め込み生成＆索引化。本文・メタ・chunk_id を格納 | `OUTPUT/processed/*.jsonl` → Vector Store（VSID/ファイルID） | L2 正規化は VS の類似度設定に従う（必要に応じクライアント側で実施） |
| `a20_rag_search_cloud_vs.py` | **5 検索**＋**6 生成** | クエリ埋め込み → VS 類似検索 →（任意）MMR/フィルタ/時間減衰 → コンテキスト結合 → 出典付与して応答 | `query`, VSID → 回答テキスト＋出典 | Top-k/テンプレート/モデルは `config_yml.yml` で制御 |
| `server.py` | **5 検索**＋**6 生成**（エンドポイント） | `a20` の処理を API/サーバとして公開（問い合わせ→検索→組立→応答） | HTTP/CLI → JSON/テキスト応答 | 運用時のエントリーポイント |
| `setup.py` | 0 環境土台 | 依存導入・CLI エントリ。RAG ロジックは持たない | - | - |
| `docker-compose/docker-compose.yml` | （Cloud では通常未使用） | Qdrant を使わないため不要 | - | Local で使用 |

> Cloud 版では、`a10_show_qdrant_data.py` / `a50_qdrant_registration.py` / `a50_rag_search_local_qdrant.py` は対象外です（Qdrant 用）。

---

# (2) Local 版（Qdrant を使う）

## ファイル別マッピング（Local）

| プログラム | RAG 工程（どこ） | どう対応しているか | 入力 → 出力 | 備考 |
|---|---|---|---|---|
| `docker-compose/docker-compose.yml` | **4/5 の「器」** | Qdrant の起動・永続化・ポートを定義（HNSW 実体は Qdrant 内） | compose 設定 → Qdrant ランタイム | `docker compose up -d` |
| `a01_load_set_rag_data.py` | **1 前処理**＋**2 チャンク分割** | 正規化／メタ抽出 → 文字数基準＋オーバーラップ分割 | 原文, `config_yml.yml` → `OUTPUT/processed/*.jsonl` | Cloud と共通の前段 |
| `a50_qdrant_registration.py` | **3 ベクトル化**＋**4 インデックス化（Local）** | 各チャンクを埋め込み →（Cosine 運用なら **L2 正規化**）→ Qdrant コレクション作成（`m`, `ef_construct`）→ upsert（本文・メタ・`chunk_id` を payload） | `OUTPUT/processed/*.jsonl` → Qdrant コレクション | `distance=Cosine` を推奨（または L2 正規化を徹底） |
| `a10_show_qdrant_data.py` | **4 インデックス検証** | コレクション一覧/件数/スキーマ/任意ポイントの payload を可視化 | Qdrant → 表示/ログ | 登録品質の点検用 |
| `a50_rag_search_local_qdrant.py` | **5 検索**＋**6 生成** | クエリ埋め込み → Qdrant 検索（`top_k`,`ef`）＋メタフィルタ →（任意）MMR/再ランク → コンテキスト結合 → 出典付与 | `query`, Qdrant → 回答テキスト＋出典 | 検索パラメタは `config_yml.yml` |
| `server.py` | **5 検索**＋**6 生成**（エンドポイント） | `a50_rag_search_local_qdrant.py` の処理を API/サーバとして公開 | HTTP/CLI → JSON/テキスト応答 | 運用時のエントリーポイント |
| `setup.py` | 0 環境土台 | 依存導入・CLI エントリ。RAG ロジックは持たない | - | - |

> Local 版では、`a02_set_vector_store_vsid.py` / `a20_rag_search_cloud_vs.py` は対象外です（Cloud 専用）。

---

# 共通モジュール（Cloud / Local 両対応）

## 共通テーブル

| モジュール | 関与工程 | どう支えるか | 主なキー/関数の例 |
|---|---|---|---|
| `config_yml.yml` | **1〜6** | 前処理/分割/埋め込み/検索/生成の一元設定 | `preprocess.*`, `chunk.size/overlap`, **Cloud**: `cloud.vector_store.*`, `cloud.embedding.model`, `cloud.search.*`, `cloud.generation.*` / **Local**: `qdrant.*`, `embedding.model`, `hnsw.*`, `search.top_k/ef`, `prompt.template` |
| `helper_api.py` | **3〜6 周辺** | OpenAI/Anthropic/Qdrant クライアント、レート制御、リトライ、ログ | `get_openai_client()`, `get_qdrant_client()`, `retry_request()` |
| `helper_rag.py` | **1〜6 コア** | 前処理・分割・メタ生成・埋め込み・MMR・L2 正規化・コンテキスト整形・出典整形 | `clean_text()`, `chunk_text()`, `build_metadata()`, `embed_texts()`, `l2_normalize()`, `mmr()`, `build_context()` |
| `helper_st.py` | **5〜6 可視化** | 検索結果・スコア・出典の UI、設定パネル、デバッグビュー | `render_search_results()`, `render_config_panel()` |

---

## 最短実行フロー（参考）

### Cloud（Vector Store）
1. `a01_load_set_rag_data.py`：**1 前処理＋2 分割**  
2. `a02_set_vector_store_vsid.py`：**3 ベクトル化＋4 インデックス化（Cloud）**  
3. `a20_rag_search_cloud_vs.py`（or `server.py`）：**5 検索＋6 生成**

### Local（Qdrant）
1. `a01_load_set_rag_data.py`：**1 前処理＋2 分割**  
2. `docker compose up -d`：**Qdrant 起動**  
3. `a50_qdrant_registration.py`：**3 ベクトル化＋4 インデックス化（Local）**  
4. `a50_rag_search_local_qdrant.py`（or `server.py`）：**5 検索＋6 生成**  
5. 必要に応じて `a10_show_qdrant_data.py`：**4 検証**

---

## ベストプラクティス（要点だけ）

- **日本語チャンク**：開始は **800–1,200 文字**＋**100–200 重なり**。  
- **正規化の一貫性**：前処理（本文）とクエリ側で同じ正規化ポリシー（全角/半角、句読点、空白）。  
- **Cosine 運用**：Qdrant は `distance=Cosine` または **L2 正規化**を一貫。  
- **メタデータ**：`source, title, section, lang, domain, timestamp` を保存（フィルタ/出典表示に活用）。  
- **MMR/再ランク**：Top-k の多様性・精度を上げる。必要に応じクロスエンコーダ導入。  
- **評価ログ（工程7）**：クエリ→命中チャンク→採点を `logs/` に残し、`chunk.size/overlap/top_k/MMR λ` をチューニング。

---

> 本書は「どのプログラムが RAG 工程の **どこ**を **どう**担当しているか」に特化しています。コマンド引数や UI 詳細は各 `.py` のヘルプ/README を参照してください。
