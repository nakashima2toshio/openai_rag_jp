# README_2.md - 利用手順と目的別サンプルプログラムの使い方

## 概要
このプロジェクトは、日本語対応のRAG（Retrieval-Augmented Generation）システムの完全実装版です。HuggingFaceから直接データセットをダウンロードし、処理、ベクトル化、検索まで一貫したパイプラインを提供します。クラウド版（OpenAI Vector Store）とローカル版（Qdrant）の両方に対応しています。

## 🚀 クイックスタート（統合ツールを使用）

### 新しい統合RAGデータ処理ツール
最新版では、すべてのデータ処理を統合した強力なStreamlit UIツールを提供しています。

```bash
# 統合RAGデータ処理ツールを起動
streamlit run a01_load_set_rag_data.py --server.port=8501
```

このツールの特徴：
- 📥 **HuggingFaceから直接ダウンロード**: データセット名を入力するだけで自動取得
- 📊 **5種類のデータセットに対応**: カスタマーサポート、医療、科学技術、法律、雑学
- 🔄 **リアルタイム処理**: ダウンロードからRAGデータ作成まで一括処理
- 📈 **統計情報表示**: トークン使用量とコスト推定を自動計算
- 💾 **多形式出力**: CSV、TXT、JSONメタデータを同時生成
- 🎛️ **柔軟な設定**: チャンクサイズ、オーバーラップ、列マッピングをUI上で調整

## 📋 基本的な利用手順（詳細版）

### ステップ1: 統合ツールでデータ準備

```bash
# Streamlit UIを起動
streamlit run a01_load_set_rag_data.py
```

**UIでの操作手順：**
1. **データセット選択**: サイドバーから処理したいデータセットを選択
   - カスタマーサポートFAQ
   - 医療Q&A（推論過程付き）
   - 科学技術Q&A（選択肢付き）
   - 法律Q&A
   - 雑学QA（TriviaQA）

2. **データ取得方法を選択**:
   - **方法A**: CSVファイルをアップロード
   - **方法B**: HuggingFaceから直接ダウンロード
     ```
     例：
     データセット名: sciq
     Split: train
     サンプル数: 1000
     ```

3. **列マッピング設定**: 
   - 質問列と回答列を適切にマッピング
   - 必要に応じて追加の列も指定

4. **処理パラメータ設定**:
   - チャンクサイズ: 800-1200文字
   - オーバーラップ: 100-200文字
   - 出力形式: CSV/TXT/JSON

5. **処理実行**: 「処理を実行」ボタンをクリック

**出力結果:**
- `OUTPUT/`ディレクトリに処理済みファイル
- `datasets/`ディレクトリに元データ（HuggingFace使用時）
- メタデータファイル（処理履歴と設定）

### ステップ2: ベクトルストアへの登録

#### クラウド版（OpenAI Vector Store）

```bash
# OpenAI Vector Storeの作成と登録
python a02_set_vector_store_vsid.py
```

**実行結果:**
- OpenAI Vector Store IDが生成され、`vector_stores.json`に保存
- ファイルがアップロードされ、ベクトル化完了

#### ローカル版（Qdrant）

```bash
# Qdrantの起動（初回のみ）
cd docker-compose/
docker-compose -f docker-compose.yml up -d
cd ..

# データ登録
python a30_qdrant_registration.py --recreate --include-answer
```

**実行結果:**
- Qdrantコレクションが作成
- ベクトルデータがインデックス化

### ステップ3: RAG検索の実行

#### クラウド版検索

```bash
# Streamlit UIで検索（OpenAI Vector Store使用）
streamlit run a03_rag_search_cloud_vs.py
```

#### ローカル版検索

```bash
# Streamlit UIで検索（Qdrant使用）
streamlit run a50_rag_search_local_qdrant.py
```

## 🎯 目的別サンプルプログラム

### 1. カスタマーサポートFAQシステム

**目的:** 顧客からの問い合わせに自動応答するシステムの構築

**統合ツールを使用した構築方法:**
```bash
# 1. 統合ツールを起動
streamlit run a01_load_set_rag_data.py

# 2. UIで以下を実行:
#    - データセット: 「カスタマーサポートFAQ」を選択
#    - HuggingFaceから「databricks/databricks-dolly-15k」をダウンロード
#    - 質問と回答の列をマッピング
#    - 処理実行

# 3. ベクトルストア作成（クラウド版）
python a02_set_vector_store_vsid.py

# 4. 検索UIを起動
streamlit run a03_rag_search_cloud_vs.py
```

**ユースケース:**
- 製品に関する質問への自動回答
- トラブルシューティングガイドの提供
- よくある質問への即座の応答
- 24時間365日のカスタマーサポート

### 2. 医療情報検索システム

**目的:** 医療関連の質問に対する情報検索と推論過程の提供

**統合ツールを使用した構築方法:**
```bash
# 1. 統合ツールを起動
streamlit run a01_load_set_rag_data.py

# 2. UIで以下を実行:
#    - データセット: 「医療Q&A」を選択
#    - HuggingFaceから「lavita/ChatDoctor-HealthCareMagic-100k」をダウンロード
#    - Complex_CoT（推論過程）を含めて処理
#    - チャンクサイズを1200文字に設定（詳細な説明のため）

# 3. Qdrantにデータ登録（ローカル版）
python a30_qdrant_registration.py --domain medical --include-answer

# 4. 検索UIを起動
streamlit run a50_rag_search_local_qdrant.py
```

**ユースケース:**
- 症状に基づく一般的な医療情報の提供
- 医療用語の説明と解説
- 治療方法の概要提供
- ※注意: 実際の診断には使用しないでください

### 3. 科学・技術Q&Aシステム

**目的:** 科学技術に関する質問への詳細な回答（選択肢付き）

**統合ツールを使用した構築方法:**
```bash
# 1. 統合ツールを起動
streamlit run a01_load_set_rag_data.py

# 2. UIで以下を実行:
#    - データセット: 「科学技術Q&A」を選択
#    - HuggingFaceから「sciq」をダウンロード（trainセット）
#    - 選択肢（distractors）を含めて処理
#    - サポート文書も統合

# 3. ハイブリッド検索の設定
python a30_qdrant_registration.py --domain science --recreate

# 4. 検索実行
streamlit run a50_rag_search_local_qdrant.py
```

**ユースケース:**
- 科学的概念の詳細な説明
- 技術的な問題解決のサポート
- 教育目的での利用（選択肢形式の学習）
- STEM分野の学習支援

### 4. 法律相談支援システム

**目的:** 法律関連の質問に対する基本情報と参考資料の提供

**統合ツールを使用した構築方法:**
```bash
# 1. 統合ツールを起動
streamlit run a01_load_set_rag_data.py

# 2. UIで以下を実行:
#    - データセット: 「法律Q&A」を選択
#    - カスタムCSVまたはHuggingFaceデータセットをロード
#    - 法律用語と条文を含めて処理
#    - メタデータに分野タグを追加

# 3. クラウド版で高精度検索
python a02_set_vector_store_vsid.py

# 4. 検索UIを起動
streamlit run a03_rag_search_cloud_vs.py
```

**ユースケース:**
- 法律用語の定義と説明
- 一般的な法律相談への初期対応
- 関連条文の検索と提示
- ※注意: 法的助言の代替にはなりません

### 5. 雑学QAシステム（TriviaQA）

**目的:** 幅広いジャンルの雑学的な質問に対する正確な回答の提供

**統合ツールを使用した構築方法:**
```bash
# 1. 統合ツールを起動
streamlit run a01_load_set_rag_data.py

# 2. UIで以下を実行:
#    - データセット: 「雑学QA」を選択
#    - HuggingFaceから「trivia_qa」をダウンロード（rcコンフィグ）
#    - エンティティページとコンテキスト情報を含めて処理
#    - Wikipediaリンクなどの参照情報も統合

# 3. ベクトルストア作成
python a02_set_vector_store_vsid.py

# 4. 検索UIを起動
streamlit run a03_rag_search_cloud_vs.py
```

**ユースケース:**
- クイズアプリケーションの開発
- 教育・学習支援システム
- 一般知識の検索と確認
- エンターテイメントコンテンツの作成
- ファクトチェック支援

**特徴:**
- Wikipedia等のエンティティページ情報を含む
- 検索コンテキストによる回答の根拠提示
- 幅広いトピック（歴史、地理、科学、文化、スポーツ等）
- 多様な質問形式（Who/What/Where/When/Why/Which）に対応

## 🔧 高度な使用方法

### マルチドメイン統合検索

複数のドメインを統合した検索システムの構築：

```bash
# 1. すべてのドメインのデータを準備
streamlit run a01_load_set_rag_data.py
# UIで各ドメインを順番に処理

# 2. 統合コレクション作成
python a30_qdrant_registration.py --recreate --collection-name multi_domain

# 3. ドメインフィルタ付き検索
streamlit run a50_rag_search_local_qdrant.py
# UIで「ALL」ドメインを選択
```

### バッチ処理とAPI利用

```python
# batch_rag_processing.py
from helper_api import ConfigManager
from helper_rag import process_batch_queries
import pandas as pd

# 大量のクエリをバッチ処理
queries_df = pd.read_csv("queries.csv")
queries = queries_df["question"].tolist()

# バッチサイズを指定して処理
results = []
for i in range(0, len(queries), 50):
    batch = queries[i:i+50]
    batch_results = process_batch_queries(batch)
    results.extend(batch_results)
    
# 結果を保存
results_df = pd.DataFrame({
    "query": queries,
    "response": results
})
results_df.to_csv("rag_results.csv", index=False)
```

### カスタムデータセットの追加

独自のデータセットを統合ツールで処理：

```python
# custom_dataset_processor.py
import streamlit as st
from a01_load_set_rag_data import main

# カスタム設定でツールを起動
if __name__ == "__main__":
    # デフォルト値をカスタマイズ
    st.set_page_config(
        page_title="カスタムRAGデータ処理",
        page_icon="🔧",
        layout="wide"
    )
    
    # カスタムデータセット設定を追加
    custom_config = {
        "dataset_name": "my_custom_data",
        "chunk_size": 1000,
        "overlap": 150,
        "include_metadata": True
    }
    
    main(custom_config)
```

### パフォーマンス最適化

```yaml
# config.yml での最適化設定
api:
  timeout: 60
  max_retries: 3
  batch_size: 100  # バッチ処理サイズ
  rate_limit_delay: 0.5  # API制限対策

embedding:
  model: "text-embedding-3-small"  # 高速モデル
  batch_size: 50
  cache_enabled: true  # キャッシュ有効化

search:
  top_k: 10
  rerank_enabled: true  # 再ランキング有効化
  mmr_lambda: 0.5  # 多様性パラメータ
```

## 📊 API使用量とコスト管理

### トークン使用量の監視

```python
from helper_api import ConfigManager

cm = ConfigManager()

# 処理前後でトークン使用量を確認
initial_usage = cm.get_token_usage()
# ... RAG処理実行 ...
final_usage = cm.get_token_usage()

# 使用量とコストを計算
tokens_used = final_usage - initial_usage
estimated_cost = cm.calculate_cost(tokens_used)

print(f"トークン使用量: {tokens_used:,}")
print(f"推定コスト: ${estimated_cost:.4f}")
```

### コスト最適化のヒント

1. **モデル選択**: 用途に応じて適切なモデルを選択
   - 高速処理: `gpt-4o-mini`
   - 高精度: `gpt-4o`
   - コスト重視: `text-embedding-3-small`

2. **キャッシュ活用**: 同じクエリの再計算を防ぐ
3. **バッチ処理**: APIコールを最小化
4. **チャンクサイズ最適化**: 無駄なトークン使用を削減

## 🐳 Docker環境での実行

### 完全なDocker環境構築

```bash
# Docker Composeで全サービスを起動
docker-compose up -d

# または個別に起動
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

### コンテナ化されたRAGシステム

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "a01_load_set_rag_data.py"]
```

## 🛠️ トラブルシューティング

### よくある問題と解決方法

**1. HuggingFaceダウンロードエラー**
```python
# 解決策: データセット名とsplitを確認
from datasets import list_datasets
available = list_datasets()
print(f"利用可能なデータセット: {available[:10]}")
```

**2. メモリ不足エラー**
```python
# 解決策: バッチサイズを調整
config = AppConfig()
config.batch_size = 10  # デフォルト: 100
config.max_chunk_size = 500  # デフォルト: 1000
```

**3. Vector Store作成エラー**
```bash
# 解決策: OpenAI APIキーを確認
echo $OPENAI_API_KEY
# APIの利用制限を確認
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**4. Qdrant接続エラー**
```bash
# 解決策: Qdrantの状態を確認
docker ps | grep qdrant
docker logs qdrant
# 再起動
docker restart qdrant
```

## 📈 パフォーマンスメトリクス

### 検索精度の測定

```python
from helper_rag import evaluate_rag_performance

# 評価データセットを用意
test_queries = [
    {"query": "返品方法は？", "expected": "返品ポリシー"},
    {"query": "配送料金", "expected": "送料情報"}
]

# 精度を測定
metrics = evaluate_rag_performance(test_queries)
print(f"精度: {metrics['accuracy']:.2%}")
print(f"再現率: {metrics['recall']:.2%}")
print(f"F1スコア: {metrics['f1']:.2%}")
```

## 📚 参考資料とリンク

- [OpenAI APIドキュメント](https://platform.openai.com/docs)
- [HuggingFace Datasets](https://huggingface.co/datasets)
- [Qdrantドキュメント](https://qdrant.tech/documentation/)
- [Streamlitドキュメント](https://docs.streamlit.io/)

## 次のステップ

1. **本番環境への展開**
   - Kubernetes設定の追加
   - 自動スケーリングの実装
   - 監視とアラートの設定

2. **機能拡張**
   - マルチモーダル対応（画像、音声）
   - リアルタイムデータ更新
   - ファインチューニング機能

3. **セキュリティ強化**
   - API認証の実装
   - データ暗号化
   - アクセス制御

## サポート

問題が発生した場合：
1. `logs/`ディレクトリのエラーログを確認
2. `CLAUDE.md`の開発ガイドラインを参照
3. 各機能の詳細ドキュメント（`doc/`）を確認

詳細な技術情報は、プロジェクトルートの`README.md`および`doc/`ディレクトリを参照してください。