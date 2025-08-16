#### 5-4 embeddings -----------------------------------------------
- pip install --upgrade torch
- pip install --upgrade tsne-torch

5-4-1 Embedding 取得・基本動作確認
5-4-2 文章検索 (Similarity Search)
5-4-3 コード検索
5-4-4 レコメンデーションシステム
5-4-5 Embedding の次元削減・正規化
5-4-6 質問応答 (QA) システムへの Embeddings 活用
5-4-7 可視化 (t-SNEなど) とクラスタリング
5-4-8 機械学習モデルでの回帰・分類タスク
5-4-9 ゼロショット分類

5-4-1 [Embedding](https://platform.openai.com/docs/guides/embeddings) 取得・基本動作確認
・Embedding API を呼び出して「埋め込みベクトル」を取得する方法を学習
・応答形式・ベクトルの長さ(1536 や 3072 次元)や dimensions パラメータなどの確認
・Embeddingの取得と表示の検証。
[内容]
・テキストを1つ指定して text-embedding-3-small もしくは text-embedding-3-large から埋め込みを取得
・レスポンスから埋め込みベクトルを抽出して表示
・dimensions パラメータを指定した場合のベクトルの挙動確認（短縮後の次元数と性能への影響）
```python
from openai import OpenAI

client = OpenAI()

def basic_embedding_example(text: str, model: str = "text-embedding-3-small"):
    response = client.embeddings.create(
        input=text,
        model=model,
        dimensions=256  # 短縮した例。指定しなければ既定長
    )
    embedding = response.data[0].embedding
    return embedding

if __name__ == "__main__":
    text = "Hello, world!"
    emb = basic_embedding_example(text)
    print(f"Embedding length: {len(emb)}")
    print(f"Sample of embedding: {emb[:10]}...")
```

5-4-2 文章検索 (Similarity Search)
・文書コーパスに対して埋め込みを取得し、検索クエリとの類似度を用いたレコメンド／検索システムの基本を学ぶ
　取得したEmbeddingを使用して、テキスト間の類似度を計算するコードを作成します。
　ユーザーが入力したテキストとデータセット内のテキストの類似度を計算し、類似したテキストを表示する機能を実装します。
類似度計算の検証。
[目的]・文書コーパスに対して埋め込みを取得し、検索クエリとの類似度を用いたレコメンド／検索システムの基本を学ぶ
[内容]
・サンプル文書を複数用意（レビュー文や短文記事など）
・各文書の埋め込みを取得してリストまたはデータフレームに保存
・ユーザのクエリを埋め込み化
・コサイン類似度を用いて上位 N 件の文書を返す
```python
import pandas as pd
from openai import OpenAI
import numpy as np

client = OpenAI()

def get_embedding(text: str, model="text-embedding-3-small"):
    response = client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def similarity_search(df, query, n=3):
    query_emb = get_embedding(query)
    # 各文書とクエリの類似度を計算
    df["similarity"] = df["embedding"].apply(lambda x: cosine_similarity(query_emb, x))
    return df.sort_values("similarity", ascending=False).head(n)

if __name__ == "__main__":
    data = [
        {"text": "おいしいコーヒーのお店です。", "embedding": None},
        {"text": "格安で犬の餌を買えるサイト。", "embedding": None},
        {"text": "最新のAI技術を解説する記事です。", "embedding": None},
    ]
    df = pd.DataFrame(data)
    # 埋め込みを取得してDataFrameに格納
    df["embedding"] = df["text"].apply(lambda x: get_embedding(x))

    query = "AI技術に関する情報を探しています"
    results = similarity_search(df, query)
    print(results)
```
5-4-3 コード検索 ----------------------------------------------------------------
・Embeddingを使用してコードの類似度を計算するコードを作成します。
・ユーザーが入力したコードとデータセット内のコードの類似度を計算し、類似したコードを表示する機能を実装します。
・コードの類似度計算の検証。
[目的]
・コード断片（関数やクラスなど）を対象に埋め込みを活用し、自然言語のクエリからコード検索を実装する例
[内容]
・Pythonファイルから関数やクラス定義を抽出
・抽出したコード断片の埋め込みを取得
・ユーザが自然言語で検索クエリを入力（例：「API呼び出し処理をする関数」）
・コサイン類似度が高いコード断片を上位 N 件表示
```python
import re
from openai import OpenAI
import pandas as pd

client = OpenAI()

def extract_functions_from_file(file_path):
    # 簡易的な正規表現で関数定義のみ抽出
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
    pattern = r"def\s+[\w_]+\s*\(.*?\):([\s\S]*?)(?=\ndef\s|$)"
    matches = re.findall(pattern, code, re.MULTILINE)
    return matches

def create_code_embedding_df(file_paths):
    data = []
    for path in file_paths:
        functions = extract_functions_from_file(path)
        for func in functions:
            data.append({"code": func.strip(), "embedding": None})
    return pd.DataFrame(data)

def get_code_embedding(code):
    response = client.embeddings.create(input=[code], model="text-embedding-3-small")
    return response.data[0].embedding

def search_code(df, query, n=3):
    query_emb = get_code_embedding(query)
    df["similarity"] = df["embedding"].apply(
        lambda x: np.dot(query_emb, x) / (np.linalg.norm(query_emb)*np.linalg.norm(x))
    )
    return df.sort_values("similarity", ascending=False).head(n)

if __name__ == "__main__":
    files = ["sample1.py", "sample2.py"]  # 対象となるPythonファイル
    df_code = create_code_embedding_df(files)
    # 各関数に対しEmbeddingを付与
    df_code["embedding"] = df_code["code"].apply(get_code_embedding)

    result = search_code(df_code, "ファイルを読み込んでAPIを呼び出す関数", n=3)
    print(result[["code", "similarity"]])
```
# ---
"""
5-4-4 レコメンデーションシステム ----------------------------------------------------------------
[目的]
・類似度を用いてユーザに対する商品や記事などのレコメンドを行う仕組みを学ぶ
[内容]
・レコメンド対象のアイテム（商品名や説明文）を埋め込み
・ユーザが興味を示した既存アイテムの埋め込みを平均するなどしてユーザプロファイルを作成
・類似度計算で最も近いアイテム上位 N 件を返す
"""

```python
def create_user_profile(user_items, embeddings_map):
    # ユーザが気に入ったアイテムの埋め込みを平均してユーザプロファイルとする
    emb_list = [embeddings_map[item] for item in user_items if item in embeddings_map]
    return np.mean(emb_list, axis=0) if len(emb_list) > 0 else None

def recommend_items(user_profile, all_items, embeddings_map, n=5):
    results = []
    for item in all_items:
        sim = cosine_similarity(user_profile, embeddings_map[item])
        results.append((item, sim))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:n]
```

"""
5-4-5 Embedding の次元削減・正規化 -------------------------------------------------------------
・埋め込み次元のダイナミック変更と正規化
[目的]
・dimensions パラメータを用いた次元削減と、後処理としてのL2正規化の基本を学ぶ
[内容]
・text-embedding-3-large などの大きな埋め込みで取得
・dimensions パラメータで小さい次元数を指定して埋め込みを再取得
・または取得後にベクトルをスライスして L2 正規化
・類似度に与える影響などを確認
"""

```python
import numpy as np

client = OpenAI()

def normalize_l2(x):
    x = np.array(x)
    norm = np.linalg.norm(x)
    return x / norm if norm != 0 else x

if __name__ == "__main__":
    text = "Testing dimension cut"
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    large_emb = response.data[0].embedding

    # 例：最初の256次元だけを使用し、L2正規化
    cut_emb = large_emb[:256]
    norm_emb = normalize_l2(cut_emb)
    print(len(norm_emb), norm_emb[:10])
```

5-4-6 質問応答 (QA) システムへの Embeddings 活用　 -----------------------------------------------
[サンプル]回答生成(Question Answering)における Embeddings 検索活用
[目的]
・埋め込みを用いて大規模コンテンツ(例えばドキュメントやFAQ等)から関連部分を検索し、Chatモデルのコンテキストに組み込む
・コンテキストウィンドウの節約や、最新情報をChatモデルに与える際のパターンを学ぶ
[内容]
・大量のドキュメント（例：企業内部マニュアルや製品リファレンス）を小分割して埋め込みを取得
・ユーザの質問に対してクエリベクトルを作成し、上位数文書を取り出す
・それらを Chat API や Completion API のプロンプトとして与えた上で回答を生成
```python
def retrieve_relevant_docs(df_docs, query, top_k=3):
    query_emb = get_embedding(query)
    df_docs["similarity"] = df_docs["embedding"].apply(lambda x: cosine_similarity(query_emb, x))
    return df_docs.sort_values("similarity", ascending=False).head(top_k)

def answer_question(query, df_docs):
    top_docs = retrieve_relevant_docs(df_docs, query, top_k=3)
    context = "\n".join(top_docs["text"].to_list())
    prompt = f"""以下の文書を参考に、質問に答えてください。文書に情報がない場合は「わかりません」と答えてください。

文書:
{context}

質問: {query}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message["content"]
```
5-4-7 可視化 (t-SNEなど) とクラスタリング --------------------------------------------------------
[目的]
・高次元の埋め込みを2次元や3次元に次元削減して可視化し、文書の類似度構造を把握する
・自然なクラスターや特徴的な塊を視覚的に理解
[内容]
・文書（例：商品レビュー）を埋め込み
・t-SNE や UMAP などで2次元に次元削減
・レビューのスコアごとに色分けしてプロットし、クラスター傾向を観察
```python
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

# dfに "embedding" (list[float]) と "score" などがあると仮定
def visualize_embeddings_tsne(df):
    X = np.vstack(df["embedding"].values)
    tsne = TSNE(n_components=2, perplexity=15, random_state=42)
    X_2d = tsne.fit_transform(X)

    plt.figure(figsize=(10,8))
    for score in sorted(df["score"].unique()):
        subset = df[df["score"] == score]
        indices = subset.index
        plt.scatter(X_2d[indices,0], X_2d[indices,1], label=str(score), alpha=0.5)
    plt.legend()
    plt.title("t-SNE visualization of embeddings")
    plt.show()
```
##### Pytorch利用の場合：
```python
import torch
from tsne_torch import TorchTSNE

# サンプルデータを用いたテスト
data = torch.randn(100, 50)
tsne = TorchTSNE(n_components=2, perplexity=30)
embedding = tsne.fit_transform(data)

print(embedding.shape)
```

5-4-8 機械学習モデルでの回帰・分類タスク--------------------------------------------------------
[目的]
・埋め込みベクトルを機械学習モデルの特徴量として使用する方法を学ぶ
・レビュースコア(連続値)を回帰、またはスコアのカテゴリ(1~5)を分類として予測
[内容]
・データセット(例：Amazonレビュー)の各サンプルに対し combined_text を埋め込み
・埋め込みを学習データ (X) 、スコアをターゲット (y) として回帰・分類に適用
・評価指標(MAE, Accuracyなど)を確認
```python
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, accuracy_score

# df["embedding"], df["score"] として準備
X = np.vstack(df["embedding"].values)
y = df["score"].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 回帰
rfr = RandomForestRegressor(n_estimators=100)
rfr.fit(X_train, y_train)
preds_reg = rfr.predict(X_test)
print("Regression MAE:", mean_absolute_error(y_test, preds_reg))

# 分類
clf = RandomForestClassifier(n_estimators=100)
clf.fit(X_train, y_train)
preds_cls = clf.predict(X_test)
print("Classification Accuracy:", accuracy_score(y_test, preds_cls))
```
5-4-9 ゼロショット分類--------------------------------------------------------
[目的]
・ラベルに対応する短いテキストやキーワードの埋め込みと、対象テキストの埋め込みを比較するだけで分類を行う手法
・トレーニング不要・すぐにクラス分けが可能
[内容]
・ラベル（例：「ポジティブ」「ネガティブ」など）の埋め込みを事前に取得
・新規テキストに対し埋め込みを取得
・各ラベルとのコサイン類似度を計算
・最も類似度が高いラベルを予測結果とする
```python
labels = ["ポジティブ", "ネガティブ"]
label_embs = [get_embedding(label) for label in labels]

def zero_shot_classify(text):
    text_emb = get_embedding(text)
    sims = [cosine_similarity(text_emb, label_emb) for label_emb in label_embs]
    max_idx = np.argmax(sims)
    return labels[max_idx]

```
