
# a50_qdrant （helper/config 連携・Named Vectors・UI付き）

## セットアップ
```bash
pip install qdrant-client openai pandas pyyaml streamlit python-dotenv
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
export OPENAI_API_KEY=sk-...
```

## インジェスト（4データ統合、domain付き）
```bash
python a50_qdrant.py --recreate               # 初期化して投入
# answerも埋め込みに含める場合
python a50_qdrant.py --recreate --include-answer
```

## 検索（CLI）
```bash
python a50_qdrant.py --search "副作用はありますか？" --domain medical --using primary --topk 5
```

## UI
```bash
streamlit run a50_qdrant_ui.py
```

## config.yml（例）
```yaml
rag:
  collection: qa_corpus
  include_answer_in_embedding: false   # trueで question\nanswer を使用
  use_named_vectors: true              # 複数定義がある場合は自動でNamed Vectors

embeddings:
  primary:
    provider: openai
    model: text-embedding-3-small
    dims: 1536
  # 2つ目を追加すると Named Vectors で同居可能（例）
  # bge:
  #   provider: openai
  #   model: text-embedding-3-large
  #   dims: 3072

paths:
  customer: /mnt/data/customer_support_faq.csv
  medical:  /mnt/data/medical_qa.csv
  legal:    /mnt/data/legal_qa.csv
  sciq:     /mnt/data/sciq_qa.csv

qdrant:
  url: http://localhost:6333
```

## 備考
- helper_api.py に `get_openai_client()` があれば自動で利用します。
- helper_rag.py に `embed_texts(texts, model, batch_size)` があれば自動で利用します。
- YAMLに複数の `embeddings` があれば自動的に Named Vectors としてコレクションを作成します。
```
