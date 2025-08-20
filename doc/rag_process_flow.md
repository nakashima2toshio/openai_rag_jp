# 📋 本プロジェクトの処理フロー設計書

## 📝 概要

本プロジェクトは、HuggingFaceからデータセットをダウンロードし、OpenAI RAG（Retrieval-Augmented Generation）システムを構築する4段階の処理パイプラインです。

## 🔄 処理フロー

```mermaid
graph TD
    %% Step 1: Download datasets
    A["🔽 Step 1: HuggingFace Dataset Download"] --> B1["customer_support_faq.csv"]
    A --> B2["trivia_qa.csv"] 
    A --> B3["medical_qa.csv"]
    A --> B4["sciq_qa.csv"]
    A --> B5["legal_qa.csv"]
    
    %% Step 2: Process to RAG data
    B1 --> C1["📝 Process Customer Support Data<br/>a011_make_rag_data_customer.py"]
    B2 --> C2["📝 Process Trivia QA Data<br/>(planned)"]
    B3 --> C3["📝 Process Medical Data<br/>a013_make_rag_data_medical.py"] 
    B4 --> C4["📝 Process Science/Tech Data<br/>a014_make_rag_data_sciq.py"]
    B5 --> C5["📝 Process Legal Data<br/>a015_make_rag_data_legal.py"]
    
    %% Step 2 outputs
    C1 --> D1["customer_rag_data.txt"]
    C2 --> D2["trivia_rag_data.txt"]
    C3 --> D3["medical_rag_data.txt"]
    C4 --> D4["sciq_rag_data.txt"] 
    C5 --> D5["legal_rag_data.txt"]
    
    %% Step 3: Create vector store
    D1 --> E["🗃️ Step 3: OpenAI Vector Store Creation<br/>a020_make_vsid.py"]
    D2 --> E
    D3 --> E
    D4 --> E
    D5 --> E
    
    %% Step 4: RAG Search
    E --> F["🔍 Step 4: RAG Search<br/>a30_rag_search.py"]
    
    %% Helper functions
    G1["🛠️ helper_api.py<br/>OpenAI API wrapper"] --> C1
    G1 --> C3
    G1 --> C4
    G1 --> C5
    G1 --> E
    G1 --> F
    
    G2["🛠️ helper_rag.py<br/>RAG utilities"] --> C1
    G2 --> C3
    G2 --> C4
    G2 --> C5
    G2 --> E
    G2 --> F
    
    G3["🛠️ helper_st.py<br/>Streamlit helpers"] --> F

    %% Styling
    classDef stepBox fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#01579b
    classDef dataBox fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#4a148c
    classDef processBox fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px,color:#1b5e20
    classDef helperBox fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#e65100
    
    class A,E,F stepBox
    class B1,B2,B3,B4,B5,D1,D2,D3,D4,D5 dataBox
    class C1,C2,C3,C4,C5 processBox
    class G1,G2,G3 helperBox
```

## 📋 詳細処理手順

### 🔽 Step 1: HuggingFace Dataset Download
**実行スクリプト**: `a30_00_dl_dataset_from_huggingface.py`

| No. | データセット | ファイル名 | 内容 |
|-----|-------------|-----------|------|
| ① | Customer Support FAQ | `customer_support_faq.csv` | カスタマーサポート・FAQデータセット |
| ② | Trivia QA | `trivia_qa.csv` | 一般知識・トリビアQAデータセット |
| ③ | Medical QA | `medical_qa.csv` | 医療質問回答データセット |
| ④ | Science/Tech QA | `sciq_qa.csv` | 科学・技術QAデータセット |
| ⑤ | Legal QA | `legal_qa.csv` | 法律・判例QAデータセット |

### 📝 Step 2: RAG Data Processing
各CSVファイルを RAG用のTXTファイルに加工

| データセット | 処理スクリプト | 出力ファイル |
|-------------|---------------|-------------|
| Customer Support | `a011_make_rag_data_customer.py` | `customer_rag_data.txt` |
| Medical QA | `a013_make_rag_data_medical.py` | `medical_rag_data.txt` |
| Science/Tech QA | `a014_make_rag_data_sciq.py` | `sciq_rag_data.txt` |
| Legal QA | `a015_make_rag_data_legal.py` | `legal_rag_data.txt` |

### 🗃️ Step 3: Vector Store Creation
**実行スクリプト**: `a020_make_vsid.py`

加工済みTXTファイルをOpenAIのVector Storeに登録し、検索可能な形式に変換

### 🔍 Step 4: RAG Search
**実行スクリプト**: `a30_rag_search.py`

Vector Storeに登録されたデータを利用して、質問に対する関連情報を検索・回答生成

## 🛠️ ヘルパー関数

| ファイル | 機能 | 利用箇所 |
|---------|------|---------|
| `helper_api.py` | OpenAI API wrapper、設定管理 | 全ステップ |
| `helper_rag.py` | RAG用データ前処理、設定 | データ加工・検索 |
| `helper_st.py` | Streamlit UI関数 | 検索インターフェース |

## 🔄 データフロー概要

```
HuggingFace → CSV → RAG用TXT → OpenAI Vector Store → RAG検索
```

各ステップは順次実行される設計で、前段階の出力が次段階の入力となる一方向のパイプライン構造です。