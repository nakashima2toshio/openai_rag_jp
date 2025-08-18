# claude_jp.md

このファイルは、このリポジトリでコード作業を行う際のClaude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクト概要

これは、HuggingFaceからデータセットをダウンロードし、RAGアプリケーション用に処理し、OpenAIのAPIを使用してベクター検索を実行する完全なパイプラインを実装した日本語OpenAI RAG（Retrieval-Augmented Generation）デモンストレーションプロジェクトです。

## 開発コマンド

### インストール
```bash
pip install -r requirements.txt
```

### アプリケーションの実行
プロジェクトでは順次実行パイプライン方式を使用します：

1. **HuggingFaceからデータセットをダウンロード：**
   ```bash
   python a30_00_dl_dataset_from_huggingface.py
   ```

2. **RAG用に個別データセットを処理：**
   ```bash
   python a30_011_make_rag_data_customer.py    # カスタマーサポートFAQ
   python a30_013_make_rag_data_medical.py     # 医療Q&A
   python a30_014_make_rag_data_sciq.py        # 科学・技術Q&A
   python a30_015_make_rag_data_legal.py       # 法律Q&A
   ```

3. **OpenAIベクターストアを作成：**
   ```bash
   python a30_020_make_vsid.py
   ```

4. **RAG検索を実行：**
   ```bash
   python a30_30_rag_search.py
   ```

### Streamlitアプリケーション
一部のスクリプトにはStreamlit UIが含まれています。以下で実行：
```bash
streamlit run <スクリプト名>.py
```

## アーキテクチャ

### コアコンポーネント

- **helper_api.py**: OpenAI APIラッパーとコア機能（ConfigManager、ログ機能、APIクライアント管理を含む）
- **helper_rag.py**: RAGデータ前処理ユーティリティと共有設定（モデル定義と価格設定を含むAppConfigクラス）
- **helper_st.py**: Streamlit専用ヘルパー関数とUIコンポーネント

### データパイプライン

1. **データソース**: `datasets`ライブラリを使用してHuggingFaceからダウンロード
2. **処理スクリプト**: 異なるドメインデータセット用の個別プロセッサ（カスタマーサポート、医療、科学、法律）
3. **ベクターストレージ**: OpenAIのベクターストアAPIとの統合
4. **検索インターフェース**: RAGベースの検索実装

### 設定

- **config.yml**: 包括的なアプリケーション設定：
  - モデル設定（GPT-4o、o1、o3、o4シリーズをサポート）
  - タイムアウトと再試行設定を含むAPI設定
  - StreamlitアプリケーションのUI設定
  - 多言語サポート（日本語/英語）
  - トークンコスト計算用の価格情報

### データフロー

```
HuggingFaceデータセット → CSVファイル → 処理済みTXTファイル → OpenAIベクターストア → RAG検索
```

### ファイル構造

- `datasets/`: HuggingFaceからダウンロードした生のCSVファイル
- `OUTPUT/`: 処理済みファイルとメタデータ
- `doc/`: markdown形式のドキュメント
- 設定は`config.yml`と環境変数で管理

## 環境変数

- `OPENAI_API_KEY`: OpenAI APIアクセスに必須
- `OPENWEATHER_API_KEY`: 天気統合デモ用（オプション）

## 主要機能

- マルチドメインデータセットサポート（カスタマーサポート、医療、科学、法律）
- バイリンガルエラーメッセージを含む日本語フォーカス
- トークン使用量追跡とコスト計算
- 包括的なログ機能とエラーハンドリング
- インタラクティブデモンストレーション用Streamlit UIコンポーネント
- OpenAI APIを使用したベクターストア管理

## 開発メモ

- プロジェクトは順次実行用の番号付き命名規則（a30_*）に従っています
- 各処理スクリプトは処理済みデータとメタデータファイルの両方を生成します
- 設定は`config.yml`で一元化され、豊富なカスタマイズオプションを提供します
- ヘルパーモジュールはパイプライン全体で再利用可能な機能を提供します