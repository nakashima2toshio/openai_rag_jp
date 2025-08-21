
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
a50_qdrant_search.py — Streamlit UI（ドメイン絞り・横断・TopK・score表示、Named Vectors切替）
------------------------------------------------------------------------------
起動: streamlit run a50_qdrant_search.py --server.port=8504
"""
import os
from typing import Dict, Any, List, Optional

import pandas as pd
import streamlit as st

try:
    import yaml
except Exception:
    yaml = None

from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI

# 設定ロード（a50_qdrant_registration.py と同等の最小版）
DEFAULTS = {
    "rag": {"collection": "qa_corpus"},
    "embeddings": {"primary": {"provider": "openai", "model": "text-embedding-3-small", "dims": 1536}},
    "qdrant": {"url": "http://localhost:6333"},
}

def load_config(path="config.yml") -> Dict[str, Any]:
    cfg = {}
    if yaml and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    full = DEFAULTS.copy()
    # 浅いマージ
    for k, v in (cfg or {}).items():
        if isinstance(v, dict) and isinstance(full.get(k), dict):
            full[k].update(v)
        else:
            full[k] = v
    return full

def embed_query(text: str, model: str) -> List[float]:
    client = OpenAI()
    return client.embeddings.create(model=model, input=[text]).data[0].embedding

st.set_page_config(page_title="Qdrant RAG UI", page_icon="🔎", layout="wide")
st.title("🔎 Qdrant RAG UI (domain filter / named vectors)")

cfg = load_config("config.yml")
collection = cfg.get("rag", {}).get("collection", "qa_corpus")
embeddings_cfg: Dict[str, Dict[str, Any]] = cfg.get("embeddings", {})
qdrant_url = (cfg.get("qdrant", {}) or {}).get("url", "http://localhost:6333")

# Sample questions for each domain
SAMPLE_QUESTIONS = {
    "customer": [
        "返金は可能ですか？",
        "配送にはどのくらい時間がかかりますか？",
        "アカウントを作成するにはどうすればよいですか？"
    ],
    "medical": [
        "副作用はありますか？",
        "心房細動の症状について教えてください",
        "糖尿病の管理方法は何ですか？"
    ],
    "legal": [
        "Googleは私が作成したコンテンツに基づいて新しいコンテンツを作成することが許可されていますか？",
        "ユーザー生成コンテンツの修正からなる派生作品を作成することはGoogleの法的権利内ですか？",
        "Googleは常に私のコンテンツをGoogleアカウントから転送することを許可しますか？"
    ],
    "sciq": [
        "チーズやヨーグルトなどの食品の調製に一般的に使用される生物のタイプは何ですか？",
        "放射性崩壊の最も危険性の低いタイプは何ですか？",
        "物質が酸素と迅速に反応するときに起こる反応の種類は何ですか？"
    ]
}

with st.sidebar:
    st.header("Settings")
    st.write(f"Collection: `{collection}`")
    vec_name = st.selectbox("Using vector (named)", options=list(embeddings_cfg.keys()))
    model_for_using = embeddings_cfg[vec_name]["model"]
    domain = st.selectbox("Domain", options=["ALL", "customer", "medical", "legal", "sciq"])
    topk = st.slider("TopK", min_value=1, max_value=20, value=5, step=1)
    qdrant_url = st.text_input("Qdrant URL", value=qdrant_url)
    
    # Sample questions section
    st.markdown("---")
    st.subheader("💡 質問例")
    if domain != "ALL":
        st.write(f"**{domain.upper()}ドメインの質問例:**")
        for i, question in enumerate(SAMPLE_QUESTIONS.get(domain, []), 1):
            if st.button(f"{i}. {question[:30]}...", key=f"sample_{domain}_{i}"):
                st.session_state['selected_query'] = question
    else:
        st.write("ドメインを選択すると質問例が表示されます")

# Initialize session state for query
if 'selected_query' not in st.session_state:
    st.session_state['selected_query'] = "返金は可能ですか？"

st.code("""
  - OpenAIのembeddingモデルが多言語対応のため、日本語質問と英語データが同じベクトル空間で比較可能
  - 例ば、日本語「返金は可能ですか？」と英語「Can I get a refund?」の類似度が0.4957と高い値を示している
  - この多言語embedding機能により、翻訳なしで日英間の意味的検索が実現されている。
  - 左ペインで、個別domainを選択すると質問・候補が表示されます。
""")
query = st.text_input("Enter your query", value=st.session_state['selected_query'])
do_search = st.button("Search")

if do_search and query.strip():
    client = QdrantClient(url=qdrant_url)
    qvec = embed_query(query, model_for_using)
    qfilter = None
    if domain != "ALL":
        qfilter = models.Filter(must=[models.FieldCondition(key="domain", match=models.MatchValue(value=domain))])
    # Since collection uses single vector configuration (not named vectors), 
    # use qvec directly without vector name
    hits = client.search(collection_name=collection, query_vector=qvec, limit=topk,
                         query_filter=qfilter)
    rows = []
    for h in hits:
        rows.append({
            "score": h.score,
            "domain": h.payload.get("domain"),
            "question": h.payload.get("question"),
            "answer": h.payload.get("answer"),
            "source": h.payload.get("source"),
        })
    st.subheader("Results")
    st.dataframe(pd.DataFrame(rows))
    
    # Display the highest score result
    if rows:
        best_result = max(rows, key=lambda x: x["score"])
        st.subheader("🏆 Highest Score Result")
        st.write(f"**Score:** {best_result['score']:.4f}")
        st.write(f"**Question:** {best_result['question']}")
        st.write(f"**Answer:** {best_result['answer']}")
