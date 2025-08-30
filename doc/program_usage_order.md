# プログラム利用順番一覧表

## 利用順番とプログラム概要

| 順番 | プログラム名 | 概要 |
|------|-------------|------|
| 0 | setup.py | MCP環境セットアップスクリプト。Python環境チェック、必要パッケージ自動インストール（streamlit、openai、qdrant-client等）、環境構築の自動化 |
| 1 | helper_api.py | OpenAI API関連のコア機能。ConfigManager、APIクライアント管理、ログ設定、Responses API型定義、トークン計算、エラーハンドリング等の共通基盤機能 |
| 2 | helper_rag.py | RAGデータ前処理の共通機能モジュール。AppConfig（モデル設定・料金情報）、データ検証、データセット読み込み、前処理、統計表示、ファイル保存等の汎用機能 |
| 3 | helper_st.py | Streamlit関連のヘルパー機能モジュール。Streamlit UI部品の共通機能を提供 |
| 4 | a00_dl_dataset_from_huggingface.py | HuggingFaceからRAG用データセットを一括ダウンロード。カスタマーサポート、医療、科学技術、法律、トリビアの5つのデータセットをCSVファイルとして保存 |
| 5 | a011_make_rag_data_customer.py | カスタマーサポートFAQデータ専用のRAG前処理Streamlitアプリ。問題・解決・サポート関連用語の検証機能でデータを質問・回答形式に変換 |
| 6 | a013_make_rag_data_medical.py | 医療QAデータ専用のRAG前処理Streamlitアプリ。症状・診断・治療・薬等の医療関連用語検証機能で医療質問データをRAG用に最適化 |
| 7 | a014_make_rag_data_sciq.py | 科学・技術QAデータ専用のRAG前処理Streamlitアプリ。化学・物理・生物・数学等の科学技術関連用語検証機能でSciQデータセットをRAG検索用に変換 |
| 8 | a015_make_rag_data_legal.py | 法律・判例QAデータ専用のRAG前処理Streamlitアプリ。法律・条文・判例・裁判等の法律関連用語検証機能でリーガルベンチデータをRAG用に最適化 |
| 9A | a02_make_vsid.py | OpenAI Vector Store作成用Streamlitアプリ。前処理済みテキストからVector Storeを作成し、vector_stores.jsonに管理情報を保存。重複対応・最新優先選択機能 |
| 10A | a03_rag_search.py | OpenAI Responses API使用のRAG検索Streamlitアプリ。file_searchツールでVector Store検索を実行。動的Vector Store ID管理、重複対応、多言語質問対応 |
| 9B | a50_qdrant_registration.py | Qdrantベクトルデータベース一括データ登録スクリプト。4つのCSVファイルを単一コレクションに統合登録。domain別フィルタ検索対応、Named Vectors対応 |
| 10B | a50_qdrant_search.py | Qdrant検索用Streamlit UI。ドメイン絞り込み検索、横断検索、TopK設定、スコア表示、Named Vectors切替機能を提供 |
| 11B | mcp_qdrant_show.py | Qdrantデータ専用表示Streamlitアプリ。Qdrant接続状態チェック、コレクション一覧表示、データ概要取得等の管理・監視機能 |
| 12 | server.py | MCPサーバー起動スクリプト。PostgreSQL・Redis接続確認、データベース初期化、FastAPIアプリケーション起動、ポート設定、テストモード対応 |

## 実行パス

### パスA: OpenAI Cloud RAG（推奨）
```
setup.py → helper群 → データダウンロード → データ前処理 → Vector Store作成 → RAG検索
```
**具体的な流れ**:
1. `setup.py` - 環境セットアップ
2. `helper_api.py`, `helper_rag.py`, `helper_st.py` - 共通機能の準備
3. `a00_dl_dataset_from_huggingface.py` - データダウンロード
4. `a011_make_rag_data_customer.py` など - 各分野のデータ前処理
5. `a02_make_vsid.py` - OpenAI Vector Store作成
6. `a03_rag_search.py` - RAG検索実行

### パスB: Qdrant RAG（オンプレミス）
```
setup.py → helper群 → データダウンロード → データ前処理 → Qdrant登録 → Qdrant検索 → 管理
```
**具体的な流れ**:
1. `setup.py` - 環境セットアップ
2. `helper_api.py`, `helper_rag.py`, `helper_st.py` - 共通機能の準備
3. `a00_dl_dataset_from_huggingface.py` - データダウンロード
4. `a011_make_rag_data_customer.py` など - 各分野のデータ前処理
5. `a50_qdrant_registration.py` - Qdrantへのデータ登録
6. `a50_qdrant_search.py` - Qdrant検索実行
7. `mcp_qdrant_show.py` - Qdrant管理・監視

### パスC: MCPサーバー（API提供）
```
setup.py → helper群 → RAGシステム → MCPサーバー起動
```
**具体的な流れ**:
1. `setup.py` - 環境セットアップ
2. RAGシステム構築（パスAまたはB）
3. `server.py` - MCPサーバー起動でAPI提供

## 注意事項

- **9A/10A** と **9B/10B** は選択式（どちらか一方を使用）
- **パスA**: クラウドベースRAG（OpenAI Vector Store使用）
- **パスB**: オンプレミスRAG（Qdrant使用）
- **helper群**（1-3番）は全パスで共通して必要
- **前処理スクリプト**（5-8番）は必要な分野のみ実行可能