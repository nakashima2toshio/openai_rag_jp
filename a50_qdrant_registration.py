# python a50_qdrant_registration.py --recreate --include-answer

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
a50_qdrant_registration.py — helper群・config.yml連携版（単一コレクション＋domain、Named Vectors対応、answer同梱切替）
--------------------------------------------------------------------------------
- 4つのCSV（customer_support_faq.csv, medical_qa.csv, legal_qa.csv, sciq_qa.csv）を単一コレクションに統合
- payloadに domain を付与し、フィルタ検索が可能
- config.yml から埋め込みモデル/入出力設定を読み込み（fallbackあり）
- answer を埋め込みに含める切替フラグ（--include-answer / YAML設定）
- Named Vectors 対応（YAMLに複数ベクトル定義があれば自動有効）
- helper_api.py / helper_rag.py が存在すれば活用（無ければ内蔵実装を利用）

使い方：
  export OPENAI_API_KEY=sk-...
  docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
  python a50_qdrant_registration.py --recreate
  python a50_qdrant_registration.py --search "副作用はありますか？" --domain medical --using primary

主要引数：
  --recreate           : コレクション削除→新規作成
  --collection         : コレクション名（既定は YAML の rag.collection または 'qa_corpus'）
  --qdrant-url         : 既定は http://localhost:6333
  --batch-size         : Embeddings/Upsert バッチ（既定 128）
  --limit              : データ件数上限（開発用、0=無制限）
  --include-answer     : 埋め込み入力に answer も結合（question + "\n" + answer）
  --using              : Named Vectors のキー名（検索時にどのベクトルで検索するか）
  --search             : クエリ指定で検索のみ実行
  --domain             : 検索対象を絞る（customer/medical/legal/sciq）
  --topk               : 上位件数（既定5）
"""
import argparse
import os
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple, Optional, Any

import pandas as pd

try:
    import yaml  # PyYAML
except Exception:
    yaml = None

try:
    import helper_api as hapi
except Exception:
    hapi = None

try:
    import helper_rag as hrag
except Exception:
    hrag = None

from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI

# ------------------ デフォルト設定（YAMLが無い場合の後ろ盾） ------------------
DEFAULTS = {
    "rag": {
        "collection": "qa_corpus",
        "include_answer_in_embedding": False,
        "use_named_vectors": False,
    },
    "embeddings": {
        # named vectors: dict[name] = {model, dims}
        "primary": {"provider": "openai", "model": "text-embedding-3-small", "dims": 1536},
        # 2nd example for future expansion; commented by default
        # "bge": {"provider": "openai", "model": "text-embedding-3-large", "dims": 3072},
    },
    "paths": {
        "customer": "OUTPUT/preprocessed_customer_support_faq_89rows_20250721_092004.csv",
        "medical":  "OUTPUT/preprocessed_medical_qa_19704rows_20250721_092658.csv",
        "legal":    "OUTPUT/preprocessed_legal_qa_4rows_20250721_100302.csv",
        "sciq":     "OUTPUT/preprocessed_sciq_qa_11679rows_20250721_095451.csv",
    },
    "qdrant": {"url": "http://localhost:6333"},
}

# ------------------ 設定ロード ------------------
def load_config(path: str = "config.yml") -> Dict[str, Any]:
    cfg = {}
    if yaml and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    # マージ（浅いマージで十分。必要なら深いマージに差し替え）
    def merge(dst, src):
        for k, v in src.items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                merge(dst[k], v)
            else:
                dst.setdefault(k, v)
    full = {}
    merge(full, DEFAULTS)
    merge(full, cfg)
    return full

# ------------------ 小道具 ------------------
def batched(seq: Iterable, size: int):
    buf = []
    for x in seq:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

# ------------------ OpenAIクライアント ------------------
def get_openai_client():
    if hapi and hasattr(hapi, "get_openai_client"):
        return hapi.get_openai_client()
    return OpenAI()

# ------------------ 埋め込み実装（helper優先） ------------------
def embed_texts_openai(texts: List[str], model: str, client: Optional[OpenAI] = None) -> List[List[float]]:
    client = client or get_openai_client()
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]

def embed_texts(texts: List[str], model: str, batch_size: int = 128) -> List[List[float]]:
    if hrag and hasattr(hrag, "embed_texts"):
        return hrag.embed_texts(texts, model=model, batch_size=batch_size)
    vecs: List[List[float]] = []
    client = get_openai_client()
    for chunk in batched(texts, batch_size):
        vecs.extend(embed_texts_openai(chunk, model=model, client=client))
    return vecs

# ------------------ 入力テキスト構築 ------------------
def build_inputs(df: pd.DataFrame, include_answer: bool) -> List[str]:
    if include_answer:
        return (df["question"].astype(str) + "\n" + df["answer"].astype(str)).tolist()
    return df["question"].astype(str).tolist()

# ------------------ CSVロード ------------------
def load_csv(path: str, required=("question", "answer"), limit: int = 0) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(path)
    # 列名マッピングが必要ならここで調整（例: 'Question'->'question'）
    column_mappings = {
        'Question': 'question',
        'Response': 'answer',
        'Answer': 'answer',
        'correct_answer': 'answer'
    }
    df = df.rename(columns=column_mappings)
    for col in required:
        if col not in df.columns:
            raise ValueError(f"{path} には '{col}' 列が必要です（列: {list(df.columns)}）")
    df = df.fillna("").drop_duplicates(subset=list(required)).reset_index(drop=True)
    if limit and limit > 0:
        df = df.head(limit).copy()
    return df

# ------------------ Qdrant: コレクション作成（Named Vectors対応） ------------------
def create_or_recreate_collection(client: QdrantClient, name: str, recreate: bool,
                                  embeddings_cfg: Dict[str, Dict[str, Any]]):
    # embeddings_cfg: dict[name] = {"model": "...", "dims": int}
    # Named Vectors：複数キーなら dict を、単一なら VectorParams を使う
    if len(embeddings_cfg) == 1:
        dims = list(embeddings_cfg.values())[0]["dims"]
        vectors_config = models.VectorParams(size=dims, distance=models.Distance.COSINE)
    else:
        # Named vectors
        vectors_config = {
            k: models.VectorParams(size=v["dims"], distance=models.Distance.COSINE)
            for k, v in embeddings_cfg.items()
        }
    if recreate:
        client.recreate_collection(collection_name=name, vectors_config=vectors_config)
    else:
        # 無ければ作成
        try:
            client.get_collection(name)
        except Exception:
            client.create_collection(collection_name=name, vectors_config=vectors_config)
    # よく使うpayloadの索引（任意）
    try:
        client.create_payload_index(name, field_name="domain", field_type="keyword")
    except Exception:
        pass

# ------------------ ポイント構築（Named Vectors対応） ------------------
def build_points(df: pd.DataFrame, vectors_by_name: Dict[str, List[List[float]]], domain: str, source_file: str
                 ) -> List[models.PointStruct]:
    # vectors_by_name: name -> list[vec]
    n = len(df)
    for name, vecs in vectors_by_name.items():
        if len(vecs) != n:
            raise ValueError(f"vectors length mismatch for '{name}': df={n}, vecs={len(vecs)}")
    now_iso = datetime.now(timezone.utc).isoformat()
    points: List[models.PointStruct] = []
    for i, row in enumerate(df.itertuples(index=False)):
        payload = {
            "domain": domain,
            "question": getattr(row, "question"),
            "answer": getattr(row, "answer"),
            "source": os.path.basename(source_file),
            "created_at": now_iso,
            "schema": "qa:v1",
        }
        # Qdrant requires point IDs to be UUID or unsigned integer
        pid = hash(f"{domain}-{i}") & 0x7FFFFFFF  # Convert to positive 32-bit integer
        if len(vectors_by_name) == 1:
            # 単一ベクトル
            vec = list(vectors_by_name.values())[0][i]
            points.append(models.PointStruct(id=pid, vector=vec, payload=payload))
        else:
            # Named Vectors（dict渡し）
            vecs_dict = {name: vecs[i] for name, vecs in vectors_by_name.items()}
            points.append(models.PointStruct(id=pid, vector=vecs_dict, payload=payload))
    return points

def upsert_points(client: QdrantClient, collection: str, points: List[models.PointStruct], batch_size: int = 128) -> int:
    count = 0
    for chunk in batched(points, batch_size):
        client.upsert(collection_name=collection, points=chunk)
        count += len(chunk)
    return count

# ------------------ 検索（Named Vectors対応） ------------------
def embed_one(text: str, model: str) -> List[float]:
    return embed_texts([text], model=model, batch_size=1)[0]

def search(client: QdrantClient, collection: str, query: str, using_vec: str, model_for_using: str,
           topk: int = 5, domain: Optional[str] = None):
    qvec = embed_one(query, model=model_for_using)
    qfilter = None
    if domain:
        qfilter = models.Filter(must=[models.FieldCondition(key="domain", match=models.MatchValue(value=domain))])
    # Named vectors のときは using="name" を指定可能（単一路のときはNoneでもOK）
    hits = client.search(collection_name=collection, query_vector=qvec, limit=topk,
                         query_filter=qfilter, using=using_vec if using_vec else None)
    return hits

# ------------------ メイン ------------------
def main():
    cfg = load_config("config.yml")
    rag_cfg = cfg.get("rag", {})
    embeddings_cfg: Dict[str, Dict[str, Any]] = cfg.get("embeddings", {})
    paths_cfg: Dict[str, str] = cfg.get("paths", {})
    qdrant_url = (cfg.get("qdrant", {}) or {}).get("url", "http://localhost:6333")

    ap = argparse.ArgumentParser(description="Ingest 4 QA datasets into single Qdrant collection (domain filter, Named Vectors).")
    ap.add_argument("--recreate", action="store_true", help="Drop & create collection before upsert.")
    ap.add_argument("--collection", default=rag_cfg.get("collection", "qa_corpus"))
    ap.add_argument("--qdrant-url", default=qdrant_url)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0, help="Row limit per CSV for development (0=all)")
    ap.add_argument("--include-answer", action="store_true",
                    default=rag_cfg.get("include_answer_in_embedding", False),
                    help="Use 'question\nanswer' as embedding input.")
    ap.add_argument("--search", default=None, help="Run search only.")
    ap.add_argument("--domain", default=None, choices=[None, "customer", "medical", "legal", "sciq"])
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--using", default=None, help="Named Vector name to use for search (e.g., 'primary').")
    args = ap.parse_args()

    # どのベクトル定義があるか判定（1つなら単一、2つ以上ならNamed Vectors）
    if not embeddings_cfg:
        embeddings_cfg = DEFAULTS["embeddings"]
    # using の既定値（単一路ならその名前、複数なら 'primary' 優先）
    using_default = list(embeddings_cfg.keys())[0]
    using_vec = args.using or using_default

    # Qdrant with timeout configuration
    client = QdrantClient(url=args.qdrant_url, timeout=300)
    create_or_recreate_collection(client, args.collection, recreate=args.recreate, embeddings_cfg=embeddings_cfg)

    # 検索のみ
    if args.search:
        # usingに対応する埋め込みモデルを取得
        if using_vec not in embeddings_cfg:
            raise ValueError(f"--using '{using_vec}' is not in embeddings config: {list(embeddings_cfg.keys())}")
        model_for_using = embeddings_cfg[using_vec]["model"]
        hits = search(client, args.collection, args.search, using_vec, model_for_using,
                      topk=args.topk, domain=args.domain)
        print(f"[Search] collection={args.collection} using={using_vec} domain={args.domain or 'ALL'} query={args.search!r}")
        for h in hits:
            print(f"score={h.score:.4f}  domain={h.payload.get('domain')}  Q: {h.payload.get('question')}  A: {h.payload.get('answer')[:80]}...")
        return

    # インジェスト
    total = 0
    for domain, path in {
        "customer": paths_cfg.get("customer", DEFAULTS["paths"]["customer"]),
        "medical":  paths_cfg.get("medical",  DEFAULTS["paths"]["medical"]),
        "legal":    paths_cfg.get("legal",    DEFAULTS["paths"]["legal"]),
        "sciq":     paths_cfg.get("sciq",     DEFAULTS["paths"]["sciq"]),
    }.items():
        if not os.path.exists(path):
            print(f"[WARN] Not found: {path} (skip domain={domain})")
            continue
        df = load_csv(path, limit=args.limit)
        texts = build_inputs(df, include_answer=args.include_answer)

        # 埋め込み（Named Vectors: 各ベクトル名ごとに生成）
        vectors_by_name: Dict[str, List[List[float]]] = {}
        for name, vcfg in embeddings_cfg.items():
            vectors_by_name[name] = embed_texts(texts, model=vcfg["model"], batch_size=args.batch_size)

        points = build_points(df, vectors_by_name, domain=domain, source_file=path)
        n = upsert_points(client, args.collection, points, batch_size=args.batch_size)
        print(f"[{domain}] upserted {n} points")
        total += n

    print(f"Done. Total upserted: {total}")

    # 動作確認のミニ検索
    try:
        sample = [("返金は可能ですか？", "customer"), ("副作用はありますか？", "medical")]
        model_for_using = embeddings_cfg[using_vec]["model"]
        for q, d in sample:
            hits = search(client, args.collection, q, using_vec, model_for_using, topk=3, domain=d)
            print(f"\n[Search] using={using_vec} domain={d} query={q}")
            for h in hits:
                print(f"  score={h.score:.4f}  Q: {h.payload.get('question')}")
    except Exception as e:
        print(f"[WARN] search test skipped: {e}")

if __name__ == "__main__":
    main()
