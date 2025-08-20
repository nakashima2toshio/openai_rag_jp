
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
a50_qdrant_ui.py — Streamlit UI（ドメイン絞り・横断・TopK・score表示、Named Vectors切替）
------------------------------------------------------------------------------
起動: streamlit run a50_qdrant_ui.py
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

# 設定ロード（a50_qdrant.py と同等の最小版）
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

with st.sidebar:
    st.header("Settings")
    st.write(f"Collection: `{collection}`")
    vec_name = st.selectbox("Using vector (named)", options=list(embeddings_cfg.keys()))
    model_for_using = embeddings_cfg[vec_name]["model"]
    domain = st.selectbox("Domain", options=["ALL", "customer", "medical", "legal", "sciq"])
    topk = st.slider("TopK", min_value=1, max_value=20, value=5, step=1)
    qdrant_url = st.text_input("Qdrant URL", value=qdrant_url)

query = st.text_input("Enter your query", value="返金は可能ですか？")
do_search = st.button("Search")

if do_search and query.strip():
    client = QdrantClient(url=qdrant_url)
    qvec = embed_query(query, model_for_using)
    qfilter = None
    if domain != "ALL":
        qfilter = models.Filter(must=[models.FieldCondition(key="domain", match=models.MatchValue(value=domain))])
    hits = client.search(collection_name=collection, query_vector=qvec, limit=topk,
                         query_filter=qfilter, using=vec_name if vec_name else None)
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
