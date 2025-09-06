# Qdrant RAG システム セットアップガイド

このガイドでは、ローカルQdrantを使用したRAG（Retrieval-Augmented Generation）システムの完全なセットアップ手順を説明します。

## 📋 前提条件

- Python 3.8以上
- Docker および Docker Compose
- OpenAI API キー

## 🏗️ システム構成

```
1. Qdrantベクトルデータベース (Docker)
   ↓
2. データ準備・投入
   ↓
3. 検索インターフェース (Streamlit)
```

## 📝 セットアップ手順

### ステップ 1: 環境準備

```bash
# リポジトリのクローン（既存の場合はスキップ）
git clone <repository_url>
cd openai_rag_jp

# 環境設定スクリプトの実行
python setup.py
```

このスクリプトは以下を実行します：
- 必要なPythonパッケージのインストール
- `.env`ファイルのテンプレート作成
- Qdrant接続の確認

### ステップ 2: 環境変数の設定

`.env`ファイルを編集し、OpenAI APIキーを設定：

```bash
# .env
OPENAI_API_KEY=sk-your-api-key-here
QDRANT_URL=http://localhost:6333
```

### ステップ 3: Qdrantサーバーの起動

Docker Composeを使用してQdrantを起動：

```bash
# Docker Composeで起動（推奨）
docker-compose -f docker-compose/docker-compose.yml up -d qdrant

# または、Dockerコマンドで直接起動
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v qdrant_data:/qdrant/storage \
  qdrant/qdrant
```

起動確認：
```bash
# コンテナの状態確認
docker ps | grep qdrant

# ヘルスチェック
curl http://localhost:6333/health
```

### ステップ 4: データの準備（初回のみ）

HuggingFaceからデータセットをダウンロードし、前処理を実行：

```bash
# データセットのダウンロード
python a30_00_dl_dataset_from_huggingface.py

# 各ドメインのデータを前処理
python a30_011_make_rag_data_customer.py  # カスタマーサポート
python a30_013_make_rag_data_medical.py   # 医療Q&A
python a30_014_make_rag_data_sciq.py      # 科学技術Q&A
python a30_015_make_rag_data_legal.py     # 法律Q&A
```

### ステップ 5: Qdrantへのデータ投入

2つのオプションから選択：

#### オプション A: シンプル版（テスト用）

```bash
python qdrant_data_loader.py --recreate --limit 100
```

特徴：
- 高速な初期セットアップ
- 各ドメインから100件ずつサンプリング
- 基本的な埋め込みのみ

#### オプション B: 詳細版（本番用）

```bash
python a50_qdrant_registration.py --recreate --include-answer
```

特徴：
- 全データの投入
- 複数の埋め込みモデル対応
- 回答も含めた埋め込み生成
- ドメインベースのフィルタリング

### ステップ 6: サーバーの起動（オプション）

統合サーバーを起動する場合：

```bash
python server.py
```

このスクリプトは以下を実行：
- Qdrant接続の確認
- APIサーバーの起動（存在する場合）
- Streamlit UIの自動起動

### ステップ 7: 検索UIの起動

Streamlitアプリケーションを起動：

```bash
streamlit run a50_qdrant_search.py --server.port 8504
```

ブラウザで `http://localhost:8504` にアクセス

## 🔍 使用方法

### 検索インターフェース

1. **ドメイン選択**: 検索対象のドメインを選択
   - ALL: 全ドメイン
   - customer: カスタマーサポート
   - medical: 医療関連
   - legal: 法律関連
   - sciq: 科学技術

2. **質問入力**: 日本語または英語で質問を入力

3. **結果表示数**: TopKで結果の表示数を調整（1-20）

### サンプル質問

各ドメインのサンプル質問が用意されています：
- カスタマー: "How can I reset my password?"
- 医療: "What are the symptoms of diabetes?"
- 法律: "What is intellectual property?"
- 科学: "How does photosynthesis work?"

## 📊 データ構造

### コレクション名
- `qa_corpus`: メインのQ&Aコレクション

### ベクトル次元
- OpenAI text-embedding-3-small: 1536次元

### ペイロード
```json
{
  "domain": "customer|medical|legal|sciq",
  "question": "質問テキスト",
  "answer": "回答テキスト",
  "metadata": "追加メタデータ"
}
```

## 🛠️ トラブルシューティング

### Qdrantに接続できない

```bash
# Qdrantの状態確認
docker ps -a | grep qdrant

# ログ確認
docker logs qdrant

# 再起動
docker restart qdrant
```

### データが見つからない

```bash
# コレクションの確認
curl http://localhost:6333/collections

# データの再投入
python qdrant_data_loader.py --recreate
```

### OpenAI APIエラー

```bash
# APIキーの確認
echo $OPENAI_API_KEY

# .envファイルの再読み込み
source .env
```

## 📁 ファイル構成

```
openai_rag_jp/
├── docker-compose/
│   └── docker-compose.yml      # Qdrant設定
├── OUTPUT/                      # 前処理済みデータ
│   ├── preprocessed_customer_support_faq.csv
│   ├── preprocessed_medical_qa.csv
│   ├── preprocessed_legal_qa.csv
│   └── preprocessed_sciq_qa.csv
├── setup.py                     # 環境セットアップ
├── server.py                    # 統合サーバー
├── qdrant_data_loader.py       # シンプルなデータローダー
├── a50_qdrant_registration.py  # 詳細なデータローダー
├── a50_qdrant_search.py        # 検索UI
└── .env                         # 環境変数
```

## 🔄 データ更新

データを更新する場合：

```bash
# 1. 新しいデータの前処理
python a30_0XX_make_rag_data_XXX.py

# 2. Qdrantコレクションの再作成
python qdrant_data_loader.py --recreate

# 3. UIの再起動
streamlit run a50_qdrant_search.py
```

## 🎯 ベストプラクティス

1. **初回セットアップ**: まず`--limit 100`でテスト
2. **本番環境**: `a50_qdrant_registration.py`で全データ投入
3. **定期バックアップ**: Dockerボリュームのバックアップ
4. **モニタリング**: Qdrantのメトリクス監視

## 📌 注意事項

- Qdrantはポート6333を使用します
- OpenAI APIの使用には課金が発生します
- 初回のデータ投入には時間がかかる場合があります
- Docker Desktopのメモリ設定を確認してください（推奨: 4GB以上）

## 🆘 サポート

問題が発生した場合：
1. ログファイルを確認
2. Docker コンテナの状態を確認
3. 環境変数が正しく設定されているか確認
4. ネットワーク接続を確認