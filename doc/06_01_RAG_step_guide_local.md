# RAG（Retrieval-Augmented Generation）実装手順

本ドキュメントでは、OpenAIのResponses APIおよびPineconeなどのベクターデータベースを用いたRAGの実装方法を解説します。

---

## 実装の概要

以下の手順で実装を進めます。

1. データセット準備・加工
2. ベクターDB（Pinecone）の設定
3. データの埋め込みとベクター登録
4. 質問をベクター検索で処理
5. Responses APIを用いて回答生成
6. 複数ツールの統合（マルチツール呼び出し）

---

## 詳細手順（プログラムコードを含む）

### ① データセット準備・加工

**目的**：質問回答ペアをベクターDBに投入する形式に加工。

**利用ライブラリ**:

```python
from datasets import load_dataset
import pandas as pd
```

**手順**:

* Hugging Faceなどから質問回答データセットを取得。
* 「質問」と「回答」を一つの文字列として統合する。

```python
ds = load_dataset("FreedomIntelligence/medical-o1-reasoning-SFT", "en", split='train[:100]')
ds_dataframe = pd.DataFrame(ds)

# 質問と回答を統合
ds_dataframe['merged'] = ds_dataframe.apply(
    lambda row: f"Question: {row['Question']} Answer: {row['Response']}", axis=1
)
```

---

### ② ベクターDB（Pinecone）の設定

**目的**：ベクターDBを初期化して、データ保持を可能にする。

**利用ライブラリ**:

```python
from pinecone import Pinecone, ServerlessSpec
```

**手順**:

* Pineconeへ接続してインデックスを作成。
* 埋め込み次元をOpenAI Embeddings APIを用いて取得。

```python
from openai import OpenAI
import os, random, string

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

sample_embedding_resp = client.embeddings.create(
    input=[ds_dataframe['merged'].iloc[0]],
    model="text-embedding-3-small"
)
embed_dim = len(sample_embedding_resp.data[0].embedding)

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
spec = ServerlessSpec(cloud="aws", region="us-east-1")

# ランダムなインデックス名を生成
index_name = 'pinecone-index-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

pc.create_index(
    index_name,
    dimension=embed_dim,
    metric='dotproduct',
    spec=spec
)

index = pc.Index(index_name)
```

---

### ③ データの埋め込みとベクター登録

**目的**：質問回答データをベクター化してメタデータ付きで登録。

```python
batch_size = 32
MODEL = "text-embedding-3-small"

for i in range(0, len(ds_dataframe['merged']), batch_size):
    lines_batch = ds_dataframe['merged'][i: i+batch_size]
    ids_batch = [str(n) for n in range(i, i+len(lines_batch))]

    res = client.embeddings.create(input=list(lines_batch), model=MODEL)
    embeds = [record.embedding for record in res.data]

    meta = [
        {"Question": rec['Question'], "Answer": rec['Response']}
        for rec in ds_dataframe.iloc[i:i+batch_size].to_dict('records')
    ]

    vectors = list(zip(ids_batch, embeds, meta))
    index.upsert(vectors=vectors)
```

---

### ④ 質問をベクター検索で処理

**目的**：ユーザーの質問に対し、関連する質問回答ペアを取得。

```python
def query_pinecone_index(client, index, model, query_text):
    query_embedding = client.embeddings.create(input=query_text, model=model).data[0].embedding
    res = index.query(vector=[query_embedding], top_k=5, include_metadata=True)
    return res
```

---

### ⑤ Responses APIを用いて回答生成

**目的**：検索結果のコンテキストを使い、最終回答を生成。

```python
matches = index.query(vector=[query_embedding], top_k=3, include_metadata=True)['matches']

context = "\n\n".join(
    f"Question: {m['metadata']['Question']}\nAnswer: {m['metadata']['Answer']}"
    for m in matches
)

response = client.responses.create(
    model="gpt-4o",
    input=f"Context: {context}\nQuestion: {query_text}"
)

print(response.output_text)
```

---

### ⑥ 複数ツールの統合（マルチツール呼び出し）

**目的**：ウェブ検索やPinecone検索を動的に選択し回答を生成。

```python
tools = [
    {"type": "web_search_preview"},
    {
        "type": "function",
        "name": "PineconeSearchDocuments",
        "parameters": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 3}
        }
    }
]

response = client.responses.create(
    model="gpt-4o",
    input=[{"role": "user", "content": query_text}],
    tools=tools,
    parallel_tool_calls=True
)
```

---

## 実行フロー（マルチツールオーケストレーション）

1. 質問を受け取る
2. 必要に応じて：

   * 一般知識はウェブ検索を実行
   * 専門知識はベクターDB検索を実行
3. 検索結果を基にResponses APIで最終的な回答生成
4. ユーザーに回答を返す

---

## 主な利用ライブラリ

* **OpenAI API**: Embeddings, Responses
* **Pinecone**: ベクターDB
* **Datasets, pandas**: データ処理

---

RAGアプローチにより、質問内容に応じて動的に適切なデータ源を選択し、精度の高い回答を提供できます。
