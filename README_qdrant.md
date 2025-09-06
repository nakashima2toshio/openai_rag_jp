# Qdrant ローカルRAGサーチ セットアップガイド

## 概要
このガイドは、QdrantをローカルのRAGサーチシステムとして設定し、データ投入から検索UIの起動までを説明します。

## クイックスタート

### 1. 環境セットアップ
```bash
# 依存パッケージのインストールとQdrantの自動起動
python setup.py
```

### 2. Qdrantサーバーとサービスの起動
```bash
# Qdrantサーバー、APIサーバー、検索UIを一括起動
python server.py
```

### 3. データの投入
```bash
# 簡易版データ投入（制限付きサンプルデータ）
python qdrant_data_loader.py --recreate --limit 100

# または、フルデータ投入
python a50_qdrant_registration.py --recreate
```

## 各コンポーネントの説明

### setup.py（改修済み）
- Pythonバージョンチェック
- 必要パッケージの自動インストール
- **Qdrantサーバーの自動起動（Docker使用）**
- 環境変数テンプレート作成
- オプションでサンプルデータの自動投入

### server.py（改修済み）
- **Qdrantサーバーの起動と接続確認**
- PostgreSQL、Redis接続確認（オプション）
- APIサーバー起動（mcp_api_server.pyが存在する場合）
- **Streamlit検索UIの自動起動**
- 統合管理とログ出力

### qdrant_data_loader.py（新規作成）
簡略版のデータローダースクリプト：
- config.ymlからの設定読み込み
- 複数ドメインのCSVデータ処理
  - customer: カスタマーサポートFAQ
  - medical: 医療Q&A
  - legal: 法律Q&A
  - sciq: 科学/技術Q&A
- OpenAI埋め込みモデル使用
- バッチ処理による効率的なデータ投入
- プログレス表示と統計情報

### a50_qdrant_registration.py（既存）
高度な機能を持つデータ登録スクリプト：
- Named Vectors対応
- 複数埋め込みモデルサポート
- answer含有オプション
- ドメインフィルタ機能

### a50_qdrant_search.py（既存）
Streamlit検索UI：
- ドメイン別検索
- TopK調整
- スコア表示
- サンプル質問集
- 多言語対応（日本語/英語）

## データ投入フロー

```mermaid
graph LR
    A[CSVファイル] --> B[データローダー]
    B --> C[OpenAI Embeddings]
    C --> D[Qdrant Vector DB]
    D --> E[検索UI]
```

## 必要な環境変数

`.env`ファイルに以下を設定：
```bash
# 必須
OPENAI_API_KEY=sk-...

# オプション
QDRANT_URL=http://localhost:6333
```

## Dockerを使用した手動起動

### Qdrantのみ起動
```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

### docker-compose使用
```bash
docker-compose -f docker-compose/docker-compose.yml up -d qdrant
```

## トラブルシューティング

### Qdrantに接続できない
```bash
# Qdrantコンテナの状態確認
docker ps | grep qdrant

# ログ確認
docker logs qdrant
```

### データが見つからない
```bash
# データファイルの存在確認
ls OUTPUT/preprocessed_*.csv

# データ準備スクリプトの実行
python a30_011_make_rag_data_customer.py
```

### 検索結果が返ってこない
- コレクションが作成されているか確認
- データが正しく投入されているか確認
- OpenAI APIキーが設定されているか確認

## 使用ポート
- 6333: Qdrant HTTP API
- 6334: Qdrant gRPC（未使用）
- 8000: MCPAPIサーバー（オプション）
- 8504: Streamlit検索UI

## 推奨実行順序

1. **初回セットアップ**
   ```bash
   python setup.py
   ```

2. **サーバー起動**
   ```bash
   python server.py
   ```

3. **データ投入（別ターミナルで）**
   ```bash
   python qdrant_data_loader.py --recreate --limit 100
   ```

4. **検索テスト**
   - ブラウザで http://localhost:8504 にアクセス
   - サンプル質問を選択または入力して検索

## 停止方法
- `Ctrl+C`でサーバーを停止
- Dockerコンテナの停止：
  ```bash
  docker stop qdrant
  ```