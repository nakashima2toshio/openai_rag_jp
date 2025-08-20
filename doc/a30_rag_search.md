# 📋 a30\_30\_rag\_search.py 設計書（改修版）

## 📝 目次

1. [📖 概要書](#📖-概要書)
2. [🔧 システム構成](#🔧-システム構成)
3. [📋 関数一覧](#📋-関数一覧)
4. [📑 関数詳細設計](#📑-関数詳細設計)
5. [⚙️ 技術仕様](#⚙️-技術仕様)
6. [🚨 エラーハンドリング](#🚨-エラーハンドリング)

---

## 📖 概要書

### 🎯 処理の概要

**最新OpenAI Responses API + file\_search RAG検索システム（重複問題修正版）**

本アプリケーションは、OpenAIの最新Responses APIとfile\_searchツールを活用した次世代RAG（Retrieval-Augmented Generation）検索システムです。**重複Vector Store問題を解決**し、動的Vector Store管理機能を追加した改修版です。

#### 🌟 主要機能

| 機能                               | 説明                                    |
| ---------------------------------- | --------------------------------------- |
| 🤖**最新Responses API**            | OpenAI最新APIによる高品質回答生成       |
| 🔍**file\_search ツール**          | Vector Store統合検索機能                |
| 📚**動的Vector Store管理**         | 自動ID更新・重複問題解決                |
| 🔄**重複ID解決（最新優先）**       | 同名Vector Storeの作成日時優先選択      |
| 📁**設定ファイル連携**             | vector_stores.json での永続化           |
| 🔗**a30_020_make_vsid.py連携**     | 新規Vector Store自動認識                |
| 📋**ファイル引用表示**             | 検索結果の出典明示                      |
| 🌐**多言語対応**                   | 英語・日本語質問サポート                |
| 📊**検索オプション**               | カスタマイズ可能な検索設定              |
| 🕒**履歴管理**                     | 検索履歴の保存・再実行                  |
| 🔒**セキュア設計**                 | 環境変数でのAPIキー管理                 |

#### 🆕 改修のハイライト

```mermaid
graph LR
    A["改修前"] --> B["重複Vector Store問題"]
    B --> C["古いIDが選択される"]
    C --> D["検索精度低下"]

    E["改修後"] --> F["VectorStoreManager"]
    F --> G["作成日時ソート"]
    G --> H["最新ID優先選択"]
    H --> I["高精度検索"]
```

### 🔄 mainの処理の流れ（改修版）

```mermaid
flowchart TD
    Start(["App Start"]) --> Init["Initialize Session State"]
    Init --> VectorMgr["Initialize VectorStoreManager"]
    VectorMgr --> UI["Setup Streamlit UI"]
    UI --> RefreshCheck{"Auto Refresh?"}
    RefreshCheck -->|Yes| Fetch["Fetch Latest Vector Stores"]
    RefreshCheck -->|No| Cache["Use Cached Stores"]
    Fetch --> Dedupe["Deduplicate by Created Time"]
    Cache --> Dedupe
    Dedupe --> Header["Display Header & Status"]
    Header --> Sidebar["Setup Sidebar"]

    Sidebar --> Store["Vector Store Selection"]
    Store --> Lang["Language Selection"]
    Lang --> Options["Search Options"]
    Options --> Management["Vector Store Management UI"]
    Management --> MainContent["Main Content Area"]

    MainContent --> Input["Query Input Form"]
    Input --> Submit{"Query Submitted?"}
    Submit -->|No| Wait["Wait for Input"]
    Submit -->|Yes| GetStoreID["Get Selected Store ID"]
    GetStoreID --> Search["Execute RAG Search"]

    Search --> Response["Display Results"]
    Response --> History["Update Search History"]
    History --> Wait

    Wait --> Footer["Display Footer"]
    Footer --> End(["App Ready"])
```

---

## 🔧 システム構成

### 📦 主要コンポーネント（改修版）

```mermaid
classDiagram
    class VectorStoreManager {
        +CONFIG_FILE_PATH : Path
        +DEFAULT_VECTOR_STORES : dict
        +STORE_NAME_MAPPING : dict
        +DISPLAY_NAME_MAPPING : dict
        +openai_client : OpenAI
        +cache : dict
        +last_update : datetime
        +load_vector_stores() dict
        +save_vector_stores() bool
        +fetch_latest_vector_stores() dict
        +get_vector_stores() dict
        +refresh_and_save() dict
        +debug_vector_stores() dict
    }

    class ModernRAGManager {
        +agent_sessions : dict
        +search_with_responses_api() tuple
        +search_with_agent_sdk() tuple
        +search() tuple
        -extract_response_text() str
        -extract_citations() list
        -extract_tool_calls() list
    }

    class StreamlitUI {
        +display_search_history() void
        +display_test_questions() void
        +display_system_info() void
        +display_search_options() void
        +display_search_results() void
        +display_vector_store_management() void
    }

    class SessionState {
        +search_history : list
        +current_query : string
        +selected_store : string
        +selected_language : string
        +search_options : dict
        +auto_refresh_stores : bool
    }

    class OpenAIAPI {
        <<external>>
    }

    class ConfigFile {
        <<file>>
        +vector_stores.json
    }

    VectorStoreManager --> OpenAIAPI
    VectorStoreManager --> ConfigFile
    ModernRAGManager --> VectorStoreManager
    StreamlitUI --> SessionState
    StreamlitUI --> VectorStoreManager
    StreamlitUI --> ModernRAGManager
```

### 📋 データフロー（重複問題解決版）

```mermaid
graph TD
    A["User Query"] --> B["VectorStoreManager"]
    B --> C["Check Cache"]
    C --> D{"Cache Valid?"}
    D -->|No| E["Fetch from OpenAI API"]
    D -->|Yes| F["Use Cached Data"]
    E --> G["Sort by Created Time DESC"]
    G --> H["Group by Store Name"]
    H --> I["Select Latest ID per Name"]
    I --> J["Update Cache"]
    F --> K["Get Selected Store ID"]
    J --> K
    K --> L["ModernRAGManager"]
    L --> M["OpenAI Responses API"]
    M --> N["file_search Tool"]
    N --> O["Vector Store Search"]
    O --> P["Knowledge Retrieval"]
    P --> Q["Response Generation"]
    Q --> R["Citation Extraction"]
    R --> S["Result Processing"]
    S --> T["Streamlit Display"]
    T --> U["Session History Update"]
```

---

## 📋 関数一覧

### 🆕 VectorStoreManager関連

| 関数名                              | 分類          | 処理概要                        | 重要度 |
| ----------------------------------- | ------------- | ------------------------------- | ------ |
| `VectorStoreManager.__init__()`     | 🏗️ 初期化   | Vector Store管理初期化          | ⭐⭐⭐ |
| `load_vector_stores()`              | 📁 設定      | 設定ファイル読み込み            | ⭐⭐⭐ |
| `save_vector_stores()`              | 💾 設定      | 設定ファイル保存                | ⭐⭐⭐ |
| `fetch_latest_vector_stores()`      | 🔄 API       | 最新Vector Store取得・重複解決  | ⭐⭐⭐ |
| `get_vector_stores()`               | 🎯 統合      | キャッシュ付きVector Store取得  | ⭐⭐⭐ |
| `refresh_and_save()`                | 🔄 更新      | 強制更新・保存実行              | ⭐⭐⭐ |
| `debug_vector_stores()`             | 🐛 デバッグ  | デバッグ情報取得                | ⭐⭐   |

### 🏗️ 初期化・設定関数

| 関数名                       | 分類          | 処理概要                        | 重要度 |
| ---------------------------- | ------------- | ------------------------------- | ------ |
| `initialize_session_state()` | 🔧 初期化     | Streamlitセッション状態初期化   | ⭐⭐⭐ |
| `get_vector_store_manager()` | 🏭 ファクトリ | Vector Store Managerシングルトン | ⭐⭐⭐ |
| `get_rag_manager()`          | 🏭 ファクトリ | RAGマネージャーシングルトン取得 | ⭐⭐⭐ |
| `get_current_vector_stores()` | 🔍 検索       | 現在のVector Store設定取得      | ⭐⭐⭐ |

### 🤖 RAG処理関数

| 関数名                        | 分類        | 処理概要              | 重要度 |
| ----------------------------- | ----------- | --------------------- | ------ |
| `ModernRAGManager.__init__()` | 🏗️ 初期化 | RAGマネージャー初期化 | ⭐⭐⭐ |
| `search_with_responses_api()` | 🔍 検索     | Responses API検索実行 | ⭐⭐⭐ |
| `search_with_agent_sdk()`     | 🤖 Agent    | Agent SDK検索実行     | ⭐⭐   |
| `search()`                    | 🎯 統合     | 統合検索メソッド      | ⭐⭐⭐ |

### 🔧 データ抽出関数

| 関数名                     | 分類    | 処理概要               | 重要度 |
| -------------------------- | ------- | ---------------------- | ------ |
| `_extract_response_text()` | 📝 抽出 | レスポンステキスト抽出 | ⭐⭐⭐ |
| `_extract_citations()`     | 📚 抽出 | ファイル引用情報抽出   | ⭐⭐⭐ |
| `_extract_tool_calls()`    | 🔧 抽出 | ツール呼び出し情報抽出 | ⭐⭐   |

### 🎨 UI表示関数

| 関数名                           | 分類        | 処理概要                   | 重要度 |
| -------------------------------- | ----------- | -------------------------- | ------ |
| `display_search_history()`       | 📊 履歴     | 検索履歴表示               | ⭐⭐   |
| `display_test_questions()`       | 💡 質問     | テスト質問表示             | ⭐⭐   |
| `display_system_info()`          | ℹ️ 情報    | システム情報表示           | ⭐     |
| `display_search_options()`       | ⚙️ 設定   | 検索オプション表示         | ⭐⭐   |
| `display_search_results()`       | 📈 結果     | 検索結果表示               | ⭐⭐⭐ |
| `display_vector_store_management()` | 🗄️ 管理 | Vector Store管理UI表示     | ⭐⭐⭐ |

### 🎯 メイン制御関数

| 関数名   | 分類    | 処理概要                   | 重要度 |
| -------- | ------- | -------------------------- | ------ |
| `main()` | 🎯 制御 | アプリケーションメイン制御 | ⭐⭐⭐ |

---

## 📑 関数詳細設計

### 🆕 VectorStoreManager.\_\_init\_\_()

#### 🎯 処理概要

Vector Store管理システムの初期化。OpenAIクライアントとキャッシュシステムの準備。

#### 📊 処理の流れ

```mermaid
graph TD
    A["Function Start"] --> B["Set OpenAI Client"]
    B --> C["Initialize Cache Dict"]
    C --> D["Set Last Update to None"]
    D --> E["Ready for Vector Store Management"]
```

#### 📋 IPO設計

| 項目        | 内容                                           |
| ----------- | ---------------------------------------------- |
| **INPUT**   | `openai_client: OpenAI = None`                 |
| **PROCESS** | クライアント設定 → キャッシュ初期化            |
| **OUTPUT**  | なし（副作用：インスタンス状態設定）           |

---

### 🔄 VectorStoreManager.fetch\_latest\_vector\_stores()

#### 🎯 処理概要

OpenAI APIから最新のVector Store一覧を取得し、重複問題を解決する中核機能。

#### 📊 処理の流れ（重複問題修正版）

```mermaid
graph TD
    A["Function Start"] --> B["Fetch Vector Stores from API"]
    B --> C["Sort by Created Time DESC"]
    C --> D["Initialize Store Candidates Dict"]
    D --> E["Iterate Each Store"]
    E --> F["Match with Known Patterns"]
    F --> G{"Exact Match?"}
    G -->|Yes| H["Set Display Name"]
    G -->|No| I["Check Partial Match"]
    I --> J{"Partial Match?"}
    J -->|Yes| H
    J -->|No| K["Use Store Name as Display"]
    H --> L{"Already in Candidates?"}
    K --> L
    L -->|No| M["Add as New Candidate"]
    L -->|Yes| N["Compare Created Time"]
    N --> O{"Newer than Existing?"}
    O -->|Yes| P["Replace with Newer"]
    O -->|No| Q["Keep Existing"]
    M --> R["Continue Loop"]
    P --> R
    Q --> R
    R --> S{"More Stores?"}
    S -->|Yes| E
    S -->|No| T["Build Final API Stores"]
    T --> U["Return Deduplicated Stores"]
```

#### 📋 IPO設計

| 項目        | 内容                                                   |
| ----------- | ------------------------------------------------------ |
| **INPUT**   | なし（OpenAI API呼び出し）                             |
| **PROCESS** | API取得 → 日時ソート → 重複解決 → 最新優先選択      |
| **OUTPUT**  | `Dict[str, str]` - (表示名: Vector Store ID)          |

#### 🔧 重複解決ロジック

```python
# 重複解決の具体例
candidates = {
    "Medical Q&A": {
        'id': 'vs_new123',
        'name': 'Medical Q&A Knowledge Base',
        'created_at': 1705567890  # 新しい
    }
    # 古いID 'vs_old456' は除外される
}
```

#### 📊 マッピング例

```python
STORE_NAME_MAPPING = {
    "customer_support_faq": "Customer Support FAQ Knowledge Base",
    "medical_qa": "Medical Q&A Knowledge Base",
    "sciq_qa": "Science & Technology Q&A Knowledge Base",
    "legal_qa": "Legal Q&A Knowledge Base"
}

DISPLAY_NAME_MAPPING = {
    "Customer Support FAQ Knowledge Base": "Customer Support FAQ",
    "Medical Q&A Knowledge Base": "Medical Q&A",
    "Science & Technology Q&A Knowledge Base": "Science & Technology Q&A",
    "Legal Q&A Knowledge Base": "Legal Q&A"
}
```

---

### 🎯 VectorStoreManager.get\_vector\_stores()

#### 🎯 処理概要

キャッシュ機能付きVector Store取得。5分間のキャッシュ有効期限管理。

#### 📊 処理の流れ

```mermaid
graph TD
    A["Function Start"] --> B{"Force Refresh?"}
    B -->|Yes| C["Clear Cache"]
    B -->|No| D{"Cache Exists?"}
    C --> E["Fetch Latest Stores"]
    D -->|No| E
    D -->|Yes| F["Check Cache Age"]
    F --> G{"Cache Valid (< 5min)?"}
    G -->|Yes| H["Return Cached Data"]
    G -->|No| E
    E --> I{"Auto Refresh Enabled?"}
    I -->|Yes| J["Call API Fetch"]
    I -->|No| K["Load from Config File"]
    J --> L["Update Cache"]
    K --> L
    L --> M["Return Vector Stores"]
    H --> M
```

#### 📋 IPO設計

| 項目        | 内容                                                   |
| ----------- | ------------------------------------------------------ |
| **INPUT**   | `force_refresh: bool = False`                          |
| **PROCESS** | キャッシュ確認 → 有効期限チェック → データ取得・更新 |
| **OUTPUT**  | `Dict[str, str]` - (表示名: Vector Store ID)          |

---

### 🔄 VectorStoreManager.refresh\_and\_save()

#### 🎯 処理概要

最新のVector Store情報を強制取得し、設定ファイルに保存する管理機能。

#### 📊 処理の流れ

```mermaid
graph TD
    A["Function Start"] --> B{"OpenAI Client Available?"}
    B -->|No| C["Display Error & Return"]
    B -->|Yes| D["Clear Cache"]
    D --> E["Force Refresh Vector Stores"]
    E --> F["Save to Config File"]
    F --> G{"Save Successful?"}
    G -->|Yes| H["Display Success Message"]
    G -->|No| I["Display Error Message"]
    H --> J["Show Updated Store List"]
    J --> K["Return Updated Stores"]
    I --> L["Return Fallback Stores"]
```

#### 📋 IPO設計

| 項目        | 内容                                                     |
| ----------- | -------------------------------------------------------- |
| **INPUT**   | なし                                                     |
| **PROCESS** | 強制更新 → 設定保存 → UI通知 → 結果表示              |
| **OUTPUT**  | `Dict[str, str]` - 更新されたVector Store設定           |

---

### 🐛 VectorStoreManager.debug\_vector\_stores()

#### 🎯 処理概要

Vector Store管理の詳細な内部状態をデバッグ用に出力。

#### 📊 処理の流れ

```mermaid
graph TD
    A["Function Start"] --> B["Check Config File Exists"]
    B --> C["Get Cached Stores"]
    C --> D["Get Last Update Time"]
    D --> E{"OpenAI Client Available?"}
    E -->|Yes| F["Fetch API Stores Details"]
    E -->|No| G["Set API Error"]
    F --> H["Extract Store Metadata"]
    G --> I["Build Debug Info Dict"]
    H --> I
    I --> J["Return Debug Info"]
```

#### 📋 IPO設計

| 項目        | 内容                                               |
| ----------- | -------------------------------------------------- |
| **INPUT**   | なし                                               |
| **PROCESS** | 内部状態収集 → API詳細取得 → デバッグ情報構築   |
| **OUTPUT**  | `Dict[str, Any]` - 包括的なデバッグ情報           |

#### 📊 デバッグ情報例

```json
{
    "config_file_exists": true,
    "cached_stores": {
        "Medical Q&A": "vs_687a060f9ed881918b213bfdeab8241b"
    },
    "last_update": "2025-01-17T10:30:45",
    "api_stores": {
        "Medical Q&A Knowledge Base": {
            "id": "vs_687a060f9ed881918b213bfde",
            "created_at": 1705567890,
            "file_counts": {"completed": 5, "total": 5},
            "usage_bytes": 1024000
        }
    }
}
```

---

### 🗄️ display\_vector\_store\_management()

#### 🎯 処理概要

Vector Store管理用のStreamlit UI。更新、デバッグ、設定表示機能。

#### 📊 処理の流れ

```mermaid
graph TD
    A["Function Start"] --> B["Display Header"]
    B --> C["Get Vector Store Manager"]
    C --> D["Show Config File Status"]
    D --> E["Display Operation Buttons"]
    E --> F{"Refresh Button Clicked?"}
    F -->|Yes| G["Execute Refresh & Save"]
    F -->|No| H{"Debug Button Clicked?"}
    G --> I["Clear Cache & Rerun"]
    H -->|Yes| J["Show Debug Info"]
    H -->|No| K{"Config Button Clicked?"}
    J --> L["Display JSON Debug Data"]
    K -->|Yes| M["Show Config File Content"]
    K -->|No| N["Wait for User Action"]
    M --> O["Display File Content as Code"]
    L --> N
    O --> N
    I --> N
```

#### 📋 IPO設計

| 項目        | 内容                                           |
| ----------- | ---------------------------------------------- |
| **INPUT**   | なし（Streamlit session state）               |
| **PROCESS** | UI構築 → ボタン処理 → 管理機能実行           |
| **OUTPUT**  | なし（副作用：UI表示・状態更新）               |

---

### 🎯 get\_current\_vector\_stores()

#### 🎯 処理概要

現在のVector Store設定を取得し、UI用のリスト形式も提供する統合関数。

#### 📊 処理の流れ

```mermaid
graph TD
    A["Function Start"] --> B["Get Vector Store Manager"]
    B --> C["Call get_vector_stores()"]
    C --> D["Extract Store Names List"]
    D --> E["Return Stores Dict & List"]
```

#### 📋 IPO設計

| 項目        | 内容                                                                 |
| ----------- | -------------------------------------------------------------------- |
| **INPUT**   | `force_refresh: bool = False`                                        |
| **PROCESS** | Manager取得 → Vector Store取得 → リスト変換                        |
| **OUTPUT**  | `Tuple[Dict[str, str], List[str]]` - (Stores辞書, Store名リスト)    |

---

### 🔧 get\_test\_questions\_by\_store()

#### 🎯 処理概要

選択されたVector Storeと言語に応じて、動的にテスト質問を取得する改修版関数。

#### 📊 処理の流れ

```mermaid
graph TD
    A["Function Start"] --> B["Build Question Mapping Key"]
    B --> C{"Exact Match Found?"}
    C -->|Yes| D["Return Matched Questions"]
    C -->|No| E["Try Partial Match"]
    E --> F{"Partial Match Found?"}
    F -->|Yes| G["Return Partial Match Questions"]
    F -->|No| H["Return Default Questions"]
    D --> I["Return Question List"]
    G --> I
    H --> I
```

#### 📋 IPO設計

| 項目        | 内容                                                     |
| ----------- | -------------------------------------------------------- |
| **INPUT**   | `store_name: str`, `language: str`                       |
| **PROCESS** | 動的マッピング → 部分一致 → デフォルト処理             |
| **OUTPUT**  | `List[str]` - 対応するテスト質問リスト                   |

#### 🌐 動的マッピング例

```python
store_question_mapping = {
    ("Customer Support FAQ", "English"): test_questions_en,
    ("Medical Q&A", "English"): test_questions_3_en,
    ("Science & Technology Q&A", "English"): test_questions_2_en,
    ("Legal Q&A", "English"): test_questions_4_en,
    # 日本語版
    ("Customer Support FAQ", "日本語"): test_questions_ja,
    ("Medical Q&A", "日本語"): test_questions_3_ja,
}

# 部分一致の例
# "Medical Q&A Knowledge Base" → "Medical Q&A"
```

---

## ⚙️ 技術仕様

### 📦 依存ライブラリ（改修版）

| ライブラリ      | バージョン | 用途                         | 重要度 |
| --------------- | ---------- | ---------------------------- | ------ |
| `streamlit`     | 最新       | 🎨 Web UIフレームワーク      | ⭐⭐⭐ |
| `openai`        | 1.x+       | ☁️ OpenAI API クライアント | ⭐⭐⭐ |
| `openai-agents` | 最新       | 🤖 Agent SDK（オプション）   | ⭐⭐   |
| `logging`       | 標準       | 📝 ログ管理                  | ⭐⭐   |
| `typing`        | 標準       | 🔤 型ヒント                  | ⭐⭐   |
| `datetime`      | 標準       | ⏰ 時刻処理                  | ⭐⭐   |
| `json`          | 標準       | 📄 JSON処理                  | ⭐⭐   |
| `pathlib`       | 標準       | 📁 パス操作                  | ⭐     |

### 🗄️ Vector Store動的管理システム

#### 📊 設定ファイル構造（vector_stores.json）

```json
{
    "vector_stores": {
        "Customer Support FAQ": "vs_687a0604f1508191aaf416d88e266ab7",
        "Medical Q&A": "vs_687a060f9ed881918b213bfdeab8241b",
        "Science & Technology Q&A": "vs_687a061acc908191af7d5d9ba623470b",
        "Legal Q&A": "vs_687a062418ec8191872efdbf8f554836"
    },
    "last_updated": "2025-01-17T10:30:45.123456",
    "source": "a30_30_rag_search.py",
    "version": "1.1"
}
```

#### 🔄 重複解決アルゴリズム

```mermaid
graph LR
    A["API Response"] --> B["Sort by created_at DESC"]
    B --> C["Group by Display Name"]
    C --> D["Select First (Latest) from Each Group"]
    D --> E["Build Final Mapping"]

    F["Before: vs_old123 (2024-01-01)"] --> G["After: vs_new456 (2025-01-17)"]
    F --> H["Same Display Name 'Medical Q&A'"]
    G --> H
    H --> I["Latest ID Selected: vs_new456"]
```

#### 🏭 VectorStoreManagerの設定

```python
# デフォルトVector Store（フォールバック用）
DEFAULT_VECTOR_STORES = {
    "Customer Support FAQ": "vs_687a0604f1508191aaf416d88e266ab7",
    "Science & Technology Q&A": "vs_687a061acc908191af7d5d9ba623470b",
    "Medical Q&A": "vs_687a060f9ed881918b213bfdeab8241b",
    "Legal Q&A": "vs_687a062418ec8191872efdbf8f554836"
}

# a30_020_make_vsid.py との連携マッピング
STORE_NAME_MAPPING = {
    "customer_support_faq": "Customer Support FAQ Knowledge Base",
    "medical_qa": "Medical Q&A Knowledge Base",
    "sciq_qa": "Science & Technology Q&A Knowledge Base",
    "legal_qa": "Legal Q&A Knowledge Base"
}

# UI表示用の逆マッピング
DISPLAY_NAME_MAPPING = {
    "Customer Support FAQ Knowledge Base": "Customer Support FAQ",
    "Medical Q&A Knowledge Base": "Medical Q&A",
    "Science & Technology Q&A Knowledge Base": "Science & Technology Q&A",
    "Legal Q&A Knowledge Base": "Legal Q&A"
}
```

### 🔧 API設定パラメータ（改修版）

#### 🤖 Responses API設定

```python
responses_api_config = {
    "model": "gpt-4o-mini",
    "tools": [{
        "type": "file_search",
        "vector_store_ids": ["vs_xxx..."],  # 動的に取得
        "max_num_results": 20,              # カスタマイズ可能
        "filters": None                     # オプション
    }],
    "include": ["file_search_call.results"],
    "timeout": 30,
    "max_retries": 3
}
```

### 📊 検索オプション（改修版）

| オプション              | デフォルト値 | 説明                           |
| ----------------------- | ------------ | ------------------------------ |
| **max\_results**        | 20           | Vector Store検索最大結果数     |
| **include\_results**    | True         | file\_search\_call.results含有 |
| **show\_citations**     | True         | ファイル引用表示               |
| **use\_agent\_sdk**     | False        | Agent SDK使用フラグ            |
| **auto\_refresh\_stores** | True         | 起動時Vector Store自動更新     |

### 🔄 セッション管理（改修版）

#### 💾 セッション状態構造

```python
session_structure = {
    "search_history": [...],  # 従来通り
    "current_query": "...",
    "selected_store": "Medical Q&A",  # 動的に管理
    "selected_language": "English",
    "search_options": {
        "max_results": 20,
        "include_results": True,
        "show_citations": True
    },
    # 新規追加
    "auto_refresh_stores": True,
    "vector_stores_updated": "2025-01-17T10:30:45",
    "force_initial_refresh": False
}
```

---

## 🚨 エラーハンドリング

### 🆕 Vector Store管理関連エラー

| エラー種別                   | 原因                     | 対処法                         | 影響度 |
| ---------------------------- | ------------------------ | ------------------------------ | ------ |
| **重複Vector Store問題**     | 🔄 同名Store複数存在     | 最新作成日時優先選択・自動解決 | 🟡 中  |
| **設定ファイル破損**         | 📁 JSON形式不正          | デフォルト値にフォールバック   | 🟡 中  |
| **API取得失敗**              | 🌐 OpenAI API障害        | 設定ファイルから読み込み       | 🟡 中  |
| **Vector Store ID不整合**    | 🚫 古いID・無効ID        | 最新情報に自動更新             | 🔴 高  |

### 🔑 API関連エラー（継続）

| エラー種別           | 原因                     | 対処法                         | 影響度 |
| -------------------- | ------------------------ | ------------------------------ | ------ |
| **APIキー未設定**    | 🚫 環境変数未設定        | 設定手順表示・アプリ停止       | 🔴 高  |
| **API認証エラー**    | 🔑 不正なAPIキー         | キー確認指示・再設定案内       | 🔴 高  |
| **API呼び出し失敗**  | 🌐 ネットワーク・API障害 | エラーメッセージ・リトライ提案 | 🟡 中  |
| **レート制限エラー** | ⏱️ 使用量上限到達      | 待機指示・使用量確認案内       | 🟡 中  |

### 🔄 重複問題解決フロー

```mermaid
graph TD
    A["Duplicate Vector Stores Detected"] --> B["Extract Created Time"]
    B --> C["Sort Descending by created_at"]
    C --> D["Group by Display Name"]
    D --> E["Select Latest from Each Group"]
    E --> F["Update Configuration"]
    F --> G{"Update Successful?"}
    G -->|Yes| H["Display Success Message"]
    G -->|No| I["Fallback to Default"]
    H --> J["Log Selected IDs"]
    I --> K["Log Fallback Action"]
    J --> L["Continue Operation"]
    K --> L
```

### 🛠️ エラー処理フロー（改修版）

```mermaid
graph TD
    A["Error Occurred"] --> B{"Error Category"}
    B -->|Vector Store| C["Vector Store Error Handler"]
    B -->|API| D["API Error Handler"]
    B -->|UI| E["UI Error Handler"]
    B -->|Agent SDK| F["Agent SDK Error Handler"]

    C --> G["Check for Duplicates"]
    G --> H["Apply Latest ID Selection"]
    H --> I["Update Cache & Config"]

    D --> J["Display Error Message"]
    E --> K["Reset State & Continue"]
    F --> L["Fallback to Responses API"]

    I --> M["Log Resolution Details"]
    J --> M
    K --> M
    L --> M

    M --> N{"Recovery Possible?"}
    N -->|Yes| O["Continue Operation"]
    N -->|No| P["Graceful Degradation"]
```

### ✅ エラーメッセージ設計（改修版）

#### 🎯 Vector Store管理エラー通知

```python
# 重複解決成功
st.success("✅ Vector Store設定を更新しました（重複問題解決）")
st.info("🔄 同名Vector Storeが検出されましたが、最新作成日時を優先して自動解決しました")

# 設定ファイル問題
st.warning("⚠️ 設定ファイル形式が不正です。デフォルト値を使用します")
st.info("💡 「最新情報に更新」ボタンで正常な設定ファイルを再生成できます")

# API取得失敗
st.error("❌ 最新情報の取得に失敗しました。設定ファイルから読み込みます")
st.info("🔄 しばらく時間をおいて「最新情報に更新」をお試しください")
```

#### 🔍 デバッグ支援機能

```python
# 重複解決ログ例
logger.info("🔄 更新: 'Medical Q&A' -> 'Medical Q&A Knowledge Base' (vs_new456) [新: 1705567890 > 旧: 1705480000]")
logger.info("✅ 新規候補: 'Legal Q&A' -> 'Legal Q&A Knowledge Base' (vs_abc123)")
logger.info("⏭️ スキップ: 'Customer Support FAQ' -> 'Customer Support FAQ v1' (vs_old789) [新: 1705400000 <= 既存: 1705567890]")
```

---

## 🎉 まとめ（改修版）

この設計書は、**重複Vector Store問題を解決**した **a30\_30\_rag\_search.py** の完全な技術仕様と実装詳細を網羅した包括的ドキュメントです。

### 🌟 改修のハイライト

* **🔄 重複Vector Store問題解決**: 同名Vector Storeの最新作成日時優先選択
* **🗄️ VectorStoreManagerクラス**: 動的Vector Store管理の中核システム
* **📁 設定ファイル連携**: vector_stores.json による永続化・キャッシュ機能
* **🔗 a30_020_make_vsid.py連携**: 新規作成Vector Storeの自動認識
* **🐛 デバッグ機能強化**: 詳細な内部状態確認・ログ出力
* **⚙️ 自動更新システム**: 起動時・手動での最新情報取得

### 📈 技術的特徴（改修版）

* **🔧 重複解決アルゴリズム**: 作成日時ベースの自動選択
* **💾 キャッシュシステム**: 5分間有効期限でのパフォーマンス最適化
* **🔒 フォールバック機能**: API障害時の設定ファイル読み込み
* **📊 UI管理機能**: サイドバーでの包括的Vector Store管理
* **🎯 動的マッピング**: 柔軟な名前解決・部分一致対応

### 🚀 今後の拡張可能性

* 🌍 多重Vector Store環境での高度な重複管理
* 📊 Vector Store使用統計・パフォーマンス分析
* 🤖 AI による最適Vector Store推奨機能
* 🔄 バージョン管理・ロールバック機能
* 📈 A/Bテスト対応Vector Store切り替え機能
* 🔐 Vector Store アクセス権限管理

### 🎯 運用上の利点

* **⚡ 高信頼性**: 重複問題の完全解決により安定した検索品質
* **🔧 メンテナンス性**: 直感的な管理UIによる運用負荷軽減
* **📈 スケーラビリティ**: 新規Vector Store の自動認識・統合
* **🐛 トラブルシューティング**: 詳細なデバッグ情報による迅速な問題解決
* **🔄 継続性**: キャッシュ・フォールバック機能による高可用性
