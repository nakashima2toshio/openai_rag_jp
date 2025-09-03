# README_2.md - 利用手順と目的別サンプルプログラムの使い方

## 概要
このプロジェクトは、日本語対応のRAG（Retrieval-Augmented Generation）デモンストレーションシステムです。HuggingFaceからデータセットをダウンロードし、OpenAIのベクトルストアを使用して高度な検索を実現します。

## 基本的な利用手順

### ステップ1: データセットのダウンロード
HuggingFaceから必要なデータセットをダウンロードします。

```bash
python a30_00_dl_dataset_from_huggingface.py
```

**実行結果:**
- `datasets/`ディレクトリにCSVファイルが保存されます
- 複数のドメイン（顧客サポート、医療、科学、法律）のデータセットが利用可能

### ステップ2: RAGデータの作成
ダウンロードしたデータセットを処理し、RAG用のデータを作成します。

```bash
# すべてのデータセットを処理する場合
python a30_011_make_rag_data_customer.py    # カスタマーサポートFAQ
python a30_013_make_rag_data_medical.py     # 医療Q&A
python a30_014_make_rag_data_sciq.py        # 科学・技術Q&A
python a30_015_make_rag_data_legal.py       # 法律Q&A
```

**実行結果:**
- `OUTPUT/`ディレクトリに処理済みテキストファイルが生成されます
- 各ファイルにはメタデータが付与されます

### ステップ3: ベクトルストアの作成
OpenAI APIを使用してベクトルストアを構築します。

```bash
python a30_020_make_vsid.py
```

**実行結果:**
- OpenAIのベクトルストアIDが生成されます
- このIDは後の検索で使用されます

### ステップ4: RAG検索の実行
作成したベクトルストアを使用して検索を実行します。

```bash
python a30_30_rag_search.py
```

## 目的別サンプルプログラム

### 1. カスタマーサポートFAQシステム

**目的:** 顧客からの問い合わせに自動応答するシステムの構築

**使用方法:**
```bash
# データ準備
python a30_011_make_rag_data_customer.py

# Streamlit UIで実行（対話型インターフェース）
streamlit run a30_011_make_rag_data_customer.py
```

**ユースケース:**
- 製品に関する質問への自動回答
- トラブルシューティングガイドの提供
- よくある質問への即座の応答

### 2. 医療情報検索システム

**目的:** 医療関連の質問に対する情報検索

**使用方法:**
```bash
# データ準備
python a30_013_make_rag_data_medical.py

# 検索実行
python a30_30_rag_search.py --domain medical
```

**ユースケース:**
- 症状に基づく一般的な医療情報の提供
- 医療用語の説明
- ※注意: 実際の診断には使用しないでください

### 3. 科学・技術Q&Aシステム

**目的:** 科学技術に関する質問への回答

**使用方法:**
```bash
# データ準備
python a30_014_make_rag_data_sciq.py

# インタラクティブモードで実行
python -i a30_014_make_rag_data_sciq.py
```

**ユースケース:**
- 科学的概念の説明
- 技術的な問題解決のサポート
- 教育目的での利用

### 4. 法律相談支援システム

**目的:** 法律関連の質問に対する基本情報の提供

**使用方法:**
```bash
# データ準備
python a30_015_make_rag_data_legal.py

# 検索実行
python a30_30_rag_search.py --domain legal
```

**ユースケース:**
- 法律用語の説明
- 一般的な法律相談への初期対応
- ※注意: 法的助言の代替にはなりません

## 高度な使用方法

### Streamlit UIの活用

多くのスクリプトはStreamlit UIを提供しています：

```bash
# 一般的な起動方法
streamlit run <スクリプト名>.py

# ポート指定
streamlit run <スクリプト名>.py --server.port 8080

# ブラウザを自動で開かない
streamlit run <スクリプト名>.py --server.headless true
```

### バッチ処理

複数のクエリを一度に処理する場合：

```python
# batch_search.py の例
from helper_api import ConfigManager
from helper_rag import process_batch_queries

queries = [
    "製品の返品方法は？",
    "配送料金について",
    "保証期間は？"
]

results = process_batch_queries(queries)
for query, result in zip(queries, results):
    print(f"Q: {query}")
    print(f"A: {result}\n")
```

### カスタムデータセットの追加

独自のデータセットを追加する方法：

1. CSVファイルを`datasets/`に配置
2. 処理スクリプトを作成：

```python
# a30_01X_make_rag_data_custom.py
from helper_rag import AppConfig, process_dataset

config = AppConfig()
process_dataset(
    input_file="datasets/custom_data.csv",
    output_dir="OUTPUT/custom",
    metadata={"domain": "custom", "language": "ja"}
)
```

### API使用量とコストの管理

トークン使用量とコストを監視：

```python
from helper_api import ConfigManager

cm = ConfigManager()
# API呼び出し後
usage = cm.get_token_usage()
cost = cm.calculate_cost(usage)
print(f"トークン使用量: {usage}")
print(f"推定コスト: ${cost:.4f}")
```

## 設定のカスタマイズ

### config.ymlの主要設定

```yaml
# モデル選択
model:
  default: "gpt-4o-mini"
  available:
    - "gpt-4o"
    - "gpt-4o-mini"
    - "o1-preview"
    - "o1-mini"

# APIタイムアウト
api:
  timeout: 60
  max_retries: 3

# 言語設定
language:
  default: "ja"
  supported: ["ja", "en"]
```

### 環境変数による上書き

```bash
# モデルを変更
export OPENAI_MODEL="gpt-4o"

# タイムアウトを延長
export API_TIMEOUT="120"
```

## トラブルシューティング

### よくある問題と解決方法

**1. API制限エラー**
```python
# config.ymlでレート制限を調整
api:
  rate_limit_delay: 1.0  # リクエスト間の遅延（秒）
```

**2. メモリ不足**
```python
# バッチサイズを減らす
config.batch_size = 10  # デフォルト: 100
```

**3. 検索精度が低い**
```python
# ベクトル検索のパラメータを調整
search_params = {
    "top_k": 10,  # 検索結果数を増やす
    "threshold": 0.7  # 類似度閾値を調整
}
```

## パフォーマンス最適化

### 1. 並列処理の活用
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(process_query, queries)
```

### 2. キャッシュの利用
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query):
    return perform_search(query)
```

### 3. バッチ処理の最適化
```python
# 大量のデータを処理する場合
for chunk in chunks(data, size=50):
    process_chunk(chunk)
    time.sleep(0.5)  # API制限を考慮
```

## ログとデバッグ

### ログレベルの設定
```python
import logging

# デバッグモード
logging.basicConfig(level=logging.DEBUG)

# 本番モード
logging.basicConfig(level=logging.INFO)
```

### ログファイルの確認
```bash
# 最新のログを表示
tail -f logs/app.log

# エラーのみ表示
grep ERROR logs/app.log
```

## 次のステップ

1. **プロダクション環境への展開**
   - Docker化の検討
   - CI/CDパイプラインの構築
   - 監視システムの導入

2. **機能拡張**
   - 新しいデータソースの追加
   - マルチモーダル対応（画像、音声）
   - リアルタイム更新機能

3. **パフォーマンス向上**
   - GPUの活用
   - 分散処理の実装
   - キャッシュ戦略の最適化

## サポート

問題が発生した場合は、以下を確認してください：

1. `logs/`ディレクトリのエラーログ
2. `CLAUDE.md`の開発ガイドライン
3. `config.yml`の設定値

詳細な技術情報については、`doc/`ディレクトリのドキュメントを参照してください。