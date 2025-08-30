# a50_qdrant_registration.py

## 概要

QdrantにRAG用のベクトルデータベースを構築するPythonスクリプト。4つのドメイン（customer、medical、legal、sciq）のCSVファイルを単一のQdrantコレクションに登録し、ドメインフィルタや多元ベクトル（Named Vectors）に対応する。

## 主な機能

- **単一コレクション統合**: 複数ドメインのQA データを1つのコレクションに統合
- **ドメインフィルタ**: `domain` フィールドでフィルタ検索が可能
- **Named Vectors対応**: 複数の埋め込みモデルを同時使用可能
- **Answer含有切替**: 埋め込み生成時にanswerも含めるかを選択可能
- **config.yml連携**: 設定ファイルから埋め込みモデルやパスを読み込み

## 使用方法

### 基本的な使用方法

1. **Qdrant起動**:
   ```bash
   docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
   ```

2. **環境変数設定**:
   ```bash
   export OPENAI_API_KEY=sk-...
   ```

3. **初期データ登録**:
   ```bash
   python a50_qdrant_registration.py --recreate
   ```

4. **検索テスト**:
   ```bash
   python a50_qdrant_registration.py --search "副作用はありますか？" --domain medical
   ```

### 主要コマンドラインオプション

| オプション | デフォルト | 説明 |
|----------|----------|------|
| `--recreate` | False | コレクション削除→新規作成 |
| `--collection` | config.yml設定 | コレクション名 |
| `--qdrant-url` | http://localhost:6333 | QdrantサーバーURL |
| `--batch-size` | 32 | 埋め込み/Upsertバッチサイズ |
| `--limit` | 0 | データ件数上限（0=無制限）|
| `--include-answer` | config.yml設定 | 埋め込みにanswerも含める |
| `--search` | None | 検索クエリ（指定時は検索のみ実行）|
| `--domain` | None | 検索対象ドメイン絞り込み |
| `--using` | "primary" | Named Vectorsのキー名 |
| `--topk` | 5 | 上位検索結果数 |

## 設定ファイル連携

`config.yml`の設定例:

```yaml
rag:
  collection: "qa_corpus"
  include_answer_in_embedding: false
  
embeddings:
  primary:
    provider: "openai"
    model: "text-embedding-3-small"
    dims: 1536
  # 複数ベクトル例（Named Vectors使用時）
  # secondary:
  #   provider: "openai" 
  #   model: "text-embedding-3-large"
  #   dims: 3072

paths:
  customer: "OUTPUT/preprocessed_customer_support_faq_89rows_20250721_092004.csv"
  medical: "OUTPUT/preprocessed_medical_qa_19704rows_20250721_092658.csv"
  legal: "OUTPUT/preprocessed_legal_qa_4rows_20250721_100302.csv"
  sciq: "OUTPUT/preprocessed_sciq_qa_11679rows_20250721_095451.csv"
  
qdrant:
  url: "http://localhost:6333"
```

## データ処理フロー

1. **設定読み込み**: config.ymlとデフォルト設定をマージ
2. **CSVファイル読み込み**: 各ドメインのCSVを読み込み、列名正規化
3. **埋め込み生成**: OpenAI APIで質問（+回答）の埋め込みを生成
4. **Qdrantコレクション作成**: Named Vectors設定でコレクション作成
5. **ポイント構築**: 各レコードにdomain、timestamp等のメタデータ付与
6. **バッチ登録**: Qdrantにポイントをバッチ登録

## ペイロード構造

```json
{
  "domain": "medical",
  "question": "副作用はありますか？",
  "answer": "一般的な副作用として...",
  "source": "preprocessed_medical_qa_19704rows_20250721_092658.csv",
  "created_at": "2025-08-30T12:34:56.789Z",
  "schema": "qa:v1"
}
```

## Named Vectors対応

- **単一ベクトル**: 1つの埋め込みモデルのみ使用
- **Named Vectors**: 複数の埋め込みモデルを同時使用
- 検索時は`--using`で使用するベクトルを指定

## エラーハンドリング

- CSVファイルが存在しない場合は警告出力してスキップ
- 必要列（question、answer）が無い場合はエラー
- Qdrant接続エラーは例外として処理

## 依存モジュール

- **helper_api**: OpenAI APIクライアント管理（オプショナル）
- **helper_rag**: RAG処理ユーティリティ（オプショナル）
- 上記が無い場合は内蔵実装を使用

## パフォーマンス考慮

- 埋め込み生成とQdrant登録を適切なバッチサイズで処理
- 大規模データセット向けにlimit オプションで開発時制限可能
- Qdrant接続にタイムアウト設定（300秒）