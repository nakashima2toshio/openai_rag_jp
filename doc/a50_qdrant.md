# a50_qdrant - Qdrant RAGシステム

## 概要

Qdrantベクトルデータベースを使用したRAG（Retrieval-Augmented Generation）システム。4つのドメイン（customer、medical、legal、sciq）のQAデータを統合管理し、多言語での意味的検索とStreamlit WebUIを提供する。

### システム構成

本システムは2つの主要コンポーネントで構成されています：

1. **a50_qdrant_registration.py**: データ登録・インデックス構築スクリプト
2. **a50_qdrant_search.py**: Streamlit検索Webアプリケーション

## 処理手順（セットアップから運用まで）

### 1. 環境準備

```bash
# Qdrantサーバー起動
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

# 環境変数設定
export OPENAI_API_KEY=sk-...
```

### 2. データ登録（初期セットアップ）

```bash
# コレクション作成とデータ一括登録
python a50_qdrant_registration.py --recreate

# 登録確認（検索テスト）
python a50_qdrant_registration.py --search "副作用はありますか？" --domain medical
```

### 3. Web UI起動（日常運用）

```bash
# StreamlitアプリでUI提供
streamlit run a50_qdrant_search.py --server.port=8504

# ブラウザでアクセス
# http://localhost:8504
```

### 4. 運用フロー

```
データ準備 → Qdrant登録 → Web UI検索 → 結果活用
     ↓              ↓           ↓          ↓
 CSVファイル → ベクトル化 → 意味検索 → RAG応答
```

## 主な機能

### データ登録機能（a50_qdrant_registration.py）

- **多ドメイン統合**: 4つのドメインを単一コレクションで管理
- **Named Vectors対応**: 複数の埋め込みモデルを同時使用
- **フィルタ検索**: ドメイン別の絞り込み検索
- **Answer含有切替**: 質問のみ/質問+回答での埋め込み生成選択
- **バッチ処理**: 大量データの効率的処理

### 検索UI機能（a50_qdrant_search.py）

- **直感的WebUI**: Streamlitベースのブラウザインターフェース
- **ドメイン絞り込み**: customer/medical/legal/sciq別検索
- **質問例表示**: 各ドメインの典型的質問を提示
- **多言語対応**: 日本語質問で英語データ検索可能
- **スコア表示**: 類似度スコア付きの検索結果

## 設定ファイル（config.yml）

```yaml
rag:
  collection: "qa_corpus"
  include_answer_in_embedding: false
  
embeddings:
  primary:
    provider: "openai"
    model: "text-embedding-3-small"
    dims: 1536
  # Named Vectors例（複数モデル使用時）
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

## データ処理フロー詳細

### 登録フロー（a50_qdrant_registration.py）

1. **設定読み込み**: config.yml + デフォルト設定のマージ
2. **CSVロード**: 各ドメインCSVの読み込み・列名正規化
3. **埋め込み生成**: OpenAI APIでテキストベクトル化
4. **コレクション作成**: Named Vectors対応のQdrantコレクション構築
5. **メタデータ付与**: domain、timestamp等の構造化情報追加
6. **バッチ登録**: 効率的なバッチ処理でQdrantに登録

### 検索フロー（a50_qdrant_search.py）

1. **クエリ入力**: WebUIでユーザー質問を受付
2. **ベクトル化**: 質問文を同じ埋め込みモデルでベクトル変換
3. **フィルタ検索**: ドメイン絞り込み + ベクトル類似度検索
4. **結果表示**: スコア順ソート + 構造化表示
5. **詳細表示**: 最高スコア結果の強調表示

## 多言語埋め込み機能

OpenAIの埋め込みモデルの多言語対応により実現：

- 日本語質問 ↔ 英語データの意味的マッチング
- 翻訳処理なしでの直接ベクトル比較
- 例：「返金は可能ですか？」⟷「Can I get a refund?」（類似度0.4957）

## ペイロード構造

Qdrantに格納される各ポイントの構造：

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

## コマンドラインオプション

### a50_qdrant_registration.py

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

### a50_qdrant_search.py

Streamlit UIでの設定項目：
- **Collection**: 使用するQdrantコレクション名
- **Using vector**: 使用するNamed Vector（埋め込みモデル）
- **Domain**: 検索対象ドメイン（ALL/customer/medical/legal/sciq）
- **TopK**: 上位検索結果数（1-20）
- **Qdrant URL**: QdrantサーバーのURL

## ドメイン別サンプル質問

### Customer Support
- "返金は可能ですか？"
- "配送にはどのくらい時間がかかりますか？"
- "アカウントを作成するにはどうすればよいですか？"

### Medical
- "副作用はありますか？"
- "心房細動の症状について教えてください"
- "糖尿病の管理方法は何ですか？"

### Legal
- "Googleは私が作成したコンテンツに基づいて新しいコンテンツを作成することが許可されていますか？"
- "ユーザー生成コンテンツの修正からなる派生作品を作成することはGoogleの法的権利内ですか？"

### SciQ
- "チーズやヨーグルトなどの食品の調製に一般的に使用される生物のタイプは何ですか？"
- "放射性崩壊の最も危険性の低いタイプは何ですか？"
- "物質が酸素と迅速に反応するときに起こる反応の種類は何ですか？"

## 技術仕様

### 依存ライブラリ
- **qdrant-client**: Qdrantベクトルデータベースクライアント
- **openai**: OpenAI APIクライアント（埋め込み生成）
- **streamlit**: Web UIフレームワーク
- **pandas**: データフレーム処理
- **PyYAML**: 設定ファイル読み込み

### パフォーマンス考慮
- バッチ処理による効率的な埋め込み生成・登録
- Qdrant接続タイムアウト設定（300秒）
- 開発時のデータ制限オプション（--limit）
- 適切なバッチサイズ設定（既定32/128）

### エラーハンドリング
- CSVファイル不存在時の警告・スキップ処理
- 必要列不足時の明確なエラーメッセージ
- Qdrant接続エラーの適切な例外処理
- 設定ファイル読み込みエラー時のデフォルト値使用

### Named Vectors対応

- **単一ベクトル**: 1つの埋め込みモデルでの標準使用
- **Named Vectors**: 複数埋め込みモデルの同時活用
- 検索時の柔軟なモデル選択（--using オプション）

## カスタマイズポイント

- 新しいドメインデータの追加
- 埋め込みモデルの変更・追加
- 質問例の拡充
- UI レイアウトのカスタマイズ  
- 検索結果表示項目の追加
- 多言語UI対応の拡張

## 運用上の注意点

1. **データ更新**: 新しいデータ追加時は`--recreate`での再構築を推奨
2. **メモリ使用量**: 大量データ処理時は`--batch-size`調整が必要
3. **API制限**: OpenAI API使用量に注意（埋め込み生成時）
4. **Qdrantメンテナンス**: 定期的なバックアップ・モニタリング推奨