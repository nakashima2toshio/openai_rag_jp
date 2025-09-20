#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
a50_rag_search_local_qdrant.py — Streamlit UI（ドメイン絞り・横断・TopK・score表示、Named Vectors切替）
------------------------------------------------------------------------------
5種類のデータセットタイプの統合処理:
  - カスタマーサポート・FAQ (customer)
  - 医療QAデータ (medical)
  - 科学・技術QA (sciq)
  - 法律・判例QA (legal)
  - TriviaQA（トリビアQA） (trivia)

起動: streamlit run a50_rag_search_local_qdrant.py --server.port=8504
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

# 設定ロード（a30_qdrant_registration.py と同等の最小版）
DEFAULTS = {
    "rag": {"collection": "product_embeddings"},  # Changed default to product_embeddings
    "embeddings": {
        "primary": {"provider": "openai", "model": "text-embedding-3-small", "dims": 1536},
        "ada-002": {"provider": "openai", "model": "text-embedding-ada-002", "dims": 1536},
        "3-small": {"provider": "openai", "model": "text-embedding-3-small", "dims": 1536},
    },
    "qdrant": {"url": "http://localhost:6333"},
}

# Collection-specific embedding configurations
COLLECTION_EMBEDDINGS = {
    "product_embeddings": {"model": "text-embedding-3-small", "dims": 384},  # 384 dims for product_embeddings
    "qa_corpus": {"model": "text-embedding-3-small", "dims": 1536},
    # Add other collections as needed
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

def embed_query(text: str, model: str, dims: Optional[int] = None) -> List[float]:
    client = OpenAI()
    # Use dimensions parameter if model supports it (text-embedding-3-* models)
    if dims and "text-embedding-3" in model:
        return client.embeddings.create(model=model, input=[text], dimensions=dims).data[0].embedding
    else:
        return client.embeddings.create(model=model, input=[text]).data[0].embedding

st.set_page_config(page_title="Qdrant RAG UI", page_icon="🔎", layout="wide")
st.title("🔎 Qdrant RAG UI (domain filter / named vectors)")

cfg = load_config("config.yml")
default_collection = cfg.get("rag", {}).get("collection", "product_embeddings")
embeddings_cfg: Dict[str, Dict[str, Any]] = cfg.get("embeddings", {})
qdrant_url = (cfg.get("qdrant", {}) or {}).get("url", "http://localhost:6333")

# Fetch available collections from Qdrant
available_collections = []
try:
    temp_client = QdrantClient(url=qdrant_url)
    collections_response = temp_client.get_collections()
    available_collections = [col.name for col in collections_response.collections]
    # Sort collections with default_collection first
    if default_collection in available_collections:
        available_collections.remove(default_collection)
        available_collections.insert(0, default_collection)
except Exception:
    available_collections = [default_collection]  # Fallback to default if can't connect

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
    ],
    "trivia": [
        "日本で一番高い山は何ですか？",
        "アメリカの初代大統領は誰ですか？",
        "太陽系で最も大きな惑星は何ですか？",
        "東京オリンピックは何年に開催されましたか？",
        "世界で最も長い川は何ですか？"
    ]
}

with st.sidebar:
    st.header("Settings")
    
    # Collection selector
    if available_collections:
        # Default collection is already at index 0 due to sorting
        collection = st.selectbox("Collection", options=available_collections, index=0)
    else:
        collection = st.text_input("Collection", value=default_collection)
    
    # Show collection info
    if collection in COLLECTION_EMBEDDINGS:
        col_info = COLLECTION_EMBEDDINGS[collection]
        st.info(f"📊 Collection '{collection}' uses {col_info['model']} with {col_info['dims']} dimensions")
    
    vec_name = st.selectbox("Using vector (named)", options=list(embeddings_cfg.keys()))
    model_for_using = embeddings_cfg[vec_name]["model"]
    
    # Check if collection supports domain filtering
    supports_domain = collection in ["qa_corpus"]  # Add collections that support domain filtering
    
    # Show domain selector based on collection support
    if supports_domain:
        domain = st.selectbox("Domain", options=["ALL", "customer", "medical", "legal", "sciq", "trivia"])
    else:
        # For collections without domain field, force ALL
        st.info(f"ℹ️ Collection '{collection}' doesn't support domain filtering. Using ALL.")
        domain = "ALL"
    
    topk = st.slider("TopK", min_value=1, max_value=20, value=5, step=1)
    qdrant_url_input = st.text_input("Qdrant URL", value=qdrant_url)
    debug_mode = st.checkbox("🐛 Debug Mode", value=False)
    
    # Sample questions section
    st.markdown("---")
    st.subheader("💡 質問例")
    if domain != "ALL":
        st.write(f"**{domain.upper()}ドメインの質問例:**")
        for i, question in enumerate(SAMPLE_QUESTIONS.get(domain, []), 1):
            if st.button(f"{i}. {question[:30]}...", key=f"sample_{domain}_{i}"):
                st.session_state['selected_query'] = question
    else:
        # Show two examples for each domain when ALL is selected
        st.write("**ALLドメインの質問例（各ドメイン2件）**")
        for dom in ["customer", "medical", "legal", "sciq", "trivia"]:
            st.caption(f"{dom.upper()} ドメイン")
            examples = SAMPLE_QUESTIONS.get(dom, [])[:2]
            for i, q in enumerate(examples, 1):
                if st.button(f"{dom} {i}. {q[:30]}...", key=f"sample_all_{dom}_{i}"):
                    st.session_state['selected_query'] = q

        # Additionally show product_embeddings samples if that collection is selected
        if collection == "product_embeddings":
            st.markdown("---")
            st.write("**Product Embeddings サンプル検索:**")
            sample_queries = [
                "製品の特徴",
                "価格について",
                "使い方を教えて",
                "サポート情報"
            ]
            for i, q in enumerate(sample_queries, 1):
                if st.button(f"{i}. {q}", key=f"sample_product_{i}"):
                    st.session_state['selected_query'] = q

# Initialize session state for query
if 'selected_query' not in st.session_state:
    st.session_state['selected_query'] = "返金は可能ですか？"

st.code("""
  - collection「qa_corpus」は5種類のデータセット（customer, medical, legal, sciq, trivia）に対応
  - ここでドメインを選択するとそのドメインに特化した情報が取り出せます。
  - collection「qa_corpus」のDomain=ALLは5つのデータセットの統合版です。
  - OpenAIのembeddingモデルが多言語対応のため、日本語質問と英語データが同じベクトル空間で比較可能
  - 例ば、日本語「返金は可能ですか？」と英語「Can I get a refund?」の類似度が0.4957と高い値を示している
  - この多言語embedding機能により、翻訳なしで日英間の意味的検索が実現されている。
  - 左ペインで、個別domainを選択すると質問・候補が表示されます。
""")
query = st.text_input("Enter your query", value=st.session_state['selected_query'])
do_search = st.button("Search")

if do_search and query.strip():
    try:
        # Use the updated URL from input if provided
        current_qdrant_url = qdrant_url_input if 'qdrant_url_input' in locals() else qdrant_url
        client = QdrantClient(url=current_qdrant_url)
        # Test connection
        try:
            client.get_collections()
        except Exception as conn_err:
            st.error(f"❌ Qdrantサーバーに接続できません: {current_qdrant_url}")
            st.error("以下を確認してください:")
            st.error("1. Qdrantサーバーが起動しているか確認: `docker ps` または `qdrant` コマンド")
            st.error("2. URLが正しいか確認 (デフォルト: http://localhost:6333)")
            st.error(f"エラー詳細: {str(conn_err)}")
            st.stop()
        
        # Get the correct embedding configuration for the selected collection
        collection_config = COLLECTION_EMBEDDINGS.get(collection, {"model": model_for_using, "dims": None})
        embedding_model = collection_config["model"]
        embedding_dims = collection_config.get("dims")
        
        # Debug: Show embedding configuration
        if debug_mode:
            st.info(f"🔍 Using model: {embedding_model} with dims: {embedding_dims}")
        
        # Generate embeddings with the correct dimensions
        try:
            qvec = embed_query(query, embedding_model, embedding_dims)
            if debug_mode:
                st.success(f"✅ Generated embedding with {len(qvec)} dimensions")
        except Exception as embed_err:
            st.error(f"❌ Embedding generation failed: {str(embed_err)}")
            st.error(f"Model: {embedding_model}, Requested dims: {embedding_dims}")
            st.stop()
        
        qfilter = None
        if domain != "ALL":
            qfilter = models.Filter(must=[models.FieldCondition(key="domain", match=models.MatchValue(value=domain))])
        
        # Use search method (it works despite deprecation warning)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            hits = client.search(
                collection_name=collection,
                query_vector=qvec,
                limit=topk,
                query_filter=qfilter
            )
        rows = []
        for h in hits:
            # Debug: Show the actual payload structure
            if debug_mode:
                st.write(f"Debug - Payload keys: {h.payload.keys() if h.payload else 'No payload'}")
                st.write(f"Debug - Full payload: {h.payload}")
            
            # Try different field names that might be used
            row_data = {
                "score": h.score,
                "domain": h.payload.get("domain") if h.payload else None,
                "question": h.payload.get("question") or h.payload.get("text") or h.payload.get("content") if h.payload else None,
                "answer": h.payload.get("answer") or h.payload.get("response") or h.payload.get("metadata") if h.payload else None,
                "source": h.payload.get("source") or h.payload.get("file") if h.payload else None,
            }
            
            # If still no question/answer, try to extract from any text field
            if not row_data["question"] and h.payload:
                # Look for any text-like field
                for key in h.payload.keys():
                    if isinstance(h.payload[key], str) and len(h.payload[key]) > 10:
                        row_data["question"] = h.payload[key][:200]  # Limit to 200 chars
                        break
            
            rows.append(row_data)
        
        st.subheader("Results")
        st.dataframe(pd.DataFrame(rows))
        
        # Display the highest score result
        if rows:
            best_result = max(rows, key=lambda x: x["score"])
            st.subheader("🏆 Highest Score Result")
            st.write(f"**Score:** {best_result['score']:.4f}")
            st.write(f"**Question:** {best_result['question']}")
            st.write(f"**Answer:** {best_result['answer']}")

            # Ask OpenAI again using the result + original query (Japanese output)
            st.subheader("🧠 OpenAI 応答（日本語）")
            try:
                br_q = best_result.get("question") or ""
                br_a = best_result.get("answer") or ""
                br_score = best_result.get("score") or 0.0

                qa_prompt_jp = (
                    "以下の検索結果（スコア・質問・回答）とユーザーの元の質問を踏まえて、" \
                    "日本語で簡潔かつ正確に回答してください。必要に応じて箇条書きを用いてください。\n\n"
                    f"ユーザーの元の質問（query）:\n{query}\n\n"
                    f"検索結果のスコア: {br_score:.4f}\n"
                    f"検索結果の質問: {br_q}\n"
                    f"検索結果の回答: {br_a}\n"
                )

                st.markdown("**質問（プロンプト）**")
                st.code(qa_prompt_jp)

                with st.spinner("OpenAIに問い合わせ中..."):
                    oai_client = OpenAI()
                    oai_resp = oai_client.responses.create(
                        model="gpt-4o-mini",
                        input=qa_prompt_jp
                    )
                    generated_answer = getattr(oai_resp, "output_text", None) or ""

                st.markdown("**回答（日本語）**")
                if generated_answer.strip():
                    st.write(generated_answer)
                else:
                    st.info("応答テキストを取得できませんでした。")
            except Exception as gen_err:
                st.error(f"OpenAI応答生成に失敗しました: {str(gen_err)}")
    except ConnectionRefusedError:
        st.error(f"❌ Qdrantサーバーへの接続が拒否されました: {qdrant_url}")
        st.error("Qdrantサーバーが起動していることを確認してください:")
        st.code("cd docker-compose && docker-compose up -d", language="bash")
    except Exception as e:
        if "Connection refused" in str(e):
            st.error(f"❌ Qdrantサーバーに接続できません: {current_qdrant_url}")
            st.error("Qdrantサーバーが起動していることを確認してください:")
            st.code("cd docker-compose && docker-compose up -d", language="bash")
        elif "collection" in str(e).lower() and "not found" in str(e).lower():
            st.error(f"❌ コレクション '{collection}' が見つかりません")
            st.error("先に a30_qdrant_registration.py を実行してデータを登録してください:")
            st.code("python a30_qdrant_registration.py", language="bash")
        else:
            st.error(f"❌ エラーが発生しました: {str(e)}")
            st.error("エラーの詳細:")
            st.exception(e)
